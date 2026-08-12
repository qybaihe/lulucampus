import Foundation
import UIKit

private struct PushInstallationState: Codable, Equatable {
    var token: String?
    var deactivationProof: String?
    var pendingDeactivation = false
    var queuedToken: String?
    var registerOperationKey: String?
    var deactivateOperationKey: String?
}

@MainActor
final class PushTokenRegistrar: ObservableObject {
    enum Status: Equatable {
        case idle
        case pending
        case registering
        case registered
        case deactivating
        case failed(String)
    }

    @Published private(set) var status: Status = .idle
    @Published private(set) var retryAttempt = 0

    private let api: APIClient
    private let auth: AuthManager
    private let keychain: KeychainStore
    private let stateAccount = "push-installation-v2"
    private var installation: PushInstallationState
    private var retryTask: Task<Void, Never>?
    private var suspendedForSignOut = false
    private var gateHeld = false
    private var gateWaiters: [CheckedContinuation<Void, Never>] = []

    init(
        api: APIClient,
        auth: AuthManager,
        keychain: KeychainStore = .init(service: "com.onemore.campus.push")
    ) {
        self.api = api
        self.auth = auth
        self.keychain = keychain
        if let raw = keychain.read(account: stateAccount),
           let data = raw.data(using: .utf8),
           let decoded = try? JSONDecoder().decode(PushInstallationState.self, from: data) {
            installation = decoded
            status = decoded.pendingDeactivation ? .pending : .idle
        } else {
            installation = .init()
        }
    }

    func receive(deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        Task { await accept(token: token) }
    }

    func resumeAfterAuthentication() async {
        suspendedForSignOut = false
        await flush()
    }

    func flush() async {
        await acquireGate()
        defer { releaseGate() }
        do {
            try await flushLocked()
        } catch {
            status = .failed(error.localizedDescription)
            scheduleRetry()
        }
    }

    /// Explicit sign-out is fail-closed. Auth state is retained until the
    /// server acknowledges deactivation of the atomic token/proof pair.
    func deactivateBeforeSignOut() async throws {
        await acquireGate()
        defer { releaseGate() }
        suspendedForSignOut = true
        retryTask?.cancel()
        guard installation.token != nil else { status = .idle; return }
        do {
            try await deactivateCurrentLocked(allowAuthenticatedFallback: true)
            UIApplication.shared.unregisterForRemoteNotifications()
        } catch {
            installation.pendingDeactivation = true
            persist()
            status = .failed("通知设备注销未完成：\(error.localizedDescription)")
            suspendedForSignOut = false
            throw error
        }
    }

    /// A 401 may make the bearer unusable; the installation-bound proof still
    /// deactivates the old account. The gate prevents a fast account-B login
    /// from registering until this account-A cleanup finishes.
    func deactivateAfterSessionExpiry() async {
        await acquireGate()
        defer { releaseGate() }
        suspendedForSignOut = true
        UIApplication.shared.unregisterForRemoteNotifications()
        guard installation.deactivationProof != nil else { return }
        do {
            try await deactivateCurrentLocked(allowAuthenticatedFallback: false)
        } catch {
            installation.pendingDeactivation = true
            persist()
            status = .failed("登录失效后通知注销待联网重试：\(error.localizedDescription)")
            scheduleRetry()
        }
    }

    private func accept(token: String) async {
        await acquireGate()
        defer { releaseGate() }
        suspendedForSignOut = false
        do {
            if let current = installation.token, current != token,
               installation.deactivationProof != nil {
                // Never overwrite a proof with a rotated token. Queue the new
                // token, revoke the old pair, then atomically promote it.
                installation.queuedToken = token
                installation.pendingDeactivation = true
                persist()
                try await deactivateCurrentLocked(allowAuthenticatedFallback: true)
            } else if installation.token != token {
                installation.token = token
                installation.deactivationProof = nil
                installation.pendingDeactivation = false
                persist()
            }
            try await flushLocked()
        } catch {
            status = .failed("通知令牌同步失败：\(error.localizedDescription)")
            scheduleRetry()
        }
    }

    private func flushLocked() async throws {
        if installation.pendingDeactivation {
            try await deactivateCurrentLocked(allowAuthenticatedFallback: false)
        }
        guard !suspendedForSignOut,
              await auth.state == .authenticated,
              let token = installation.token else {
            status = installation.pendingDeactivation ? .pending : .idle
            return
        }
        status = .registering
        if installation.registerOperationKey == nil {
            installation.registerOperationKey = "push-register-\(UUID().uuidString)"
            persist()
        }
        let response: PushDeviceRegistration = try await api.send(
            "/notifications/devices",
            method: .post,
            body: PushDeviceRegisterRequest(token: token),
            idempotencyKey: installation.registerOperationKey!
        )
        // token and proof are committed as one Keychain value.
        installation.deactivationProof = response.deactivationToken
        installation.pendingDeactivation = false
        installation.registerOperationKey = nil
        persist()
        retryAttempt = 0
        status = .registered
        retryTask?.cancel()
        retryTask = nil
    }

    private func deactivateCurrentLocked(allowAuthenticatedFallback: Bool) async throws {
        guard let token = installation.token else { return }
        status = .deactivating
        if installation.deactivateOperationKey == nil {
            installation.deactivateOperationKey = "push-deactivate-\(UUID().uuidString)"
            persist()
        }
        if let proof = installation.deactivationProof {
            let _: PushDeviceDeactivation = try await api.send(
                "/notifications/devices/installation",
                method: .delete,
                body: PushInstallationDeactivateRequest(token: token, deactivationToken: proof)
            )
        } else if allowAuthenticatedFallback, await auth.state == .authenticated {
            let _: PushDeviceDeactivation = try await api.send(
                "/notifications/devices",
                method: .delete,
                body: PushDeviceDeactivateRequest(token: token),
                idempotencyKey: installation.deactivateOperationKey!
            )
        }
        installation.deactivationProof = nil
        installation.pendingDeactivation = false
        installation.deactivateOperationKey = nil
        installation.registerOperationKey = nil
        if let queued = installation.queuedToken {
            installation.token = queued
            installation.queuedToken = nil
        }
        persist()
        retryAttempt = 0
        status = .idle
    }

    private func persist() {
        guard let data = try? JSONEncoder().encode(installation) else { return }
        keychain.write(String(decoding: data, as: UTF8.self), account: stateAccount)
    }

    private func scheduleRetry() {
        guard retryTask == nil else { return }
        retryAttempt += 1
        let delay = min(pow(2.0, Double(retryAttempt - 1)), 60)
        retryTask = Task { [weak self] in
            do { try await Task.sleep(for: .seconds(delay)) }
            catch { return }
            guard !Task.isCancelled, let self else { return }
            self.retryTask = nil
            await self.flush()
        }
    }

    private func acquireGate() async {
        if !gateHeld { gateHeld = true; return }
        await withCheckedContinuation { gateWaiters.append($0) }
    }

    private func releaseGate() {
        if gateWaiters.isEmpty { gateHeld = false }
        else { gateWaiters.removeFirst().resume() }
    }

    deinit { retryTask?.cancel() }
}
