import Foundation
import Security

actor AuthManager {
    enum State: Equatable, Sendable { case unauthenticated, authenticated, expired }
    private(set) var state: State
    private var bearerToken: String?
    private let keychain: KeychainStore
    private let expiredMarkerKey: String
    private let devUserOverride: String?
    private let forceSignedOut: Bool

    init(keychain: KeychainStore = .init(service: "com.onemore.campus.auth")) {
        self.keychain = keychain
        let markerKey = "\(keychain.service).session-expired"
        expiredMarkerKey = markerKey
        var initialToken = keychain.read(account: "access-token")
        var persistedExpired = keychain.read(account: "session-expired") == "true"
            || UserDefaults.standard.bool(forKey: markerKey)
        #if DEV_AUTH
        let arguments = ProcessInfo.processInfo.arguments
        let initialOverride = Self.argumentValue("-DevUserIDOverride", in: arguments)
        let initiallyForcedSignedOut = Self.argumentValue("-ForceSignedOut", in: arguments)?.uppercased() == "YES"
        if arguments.contains("-UI_TESTING"), initialOverride != nil {
            persistedExpired = false
            keychain.delete(account: "session-expired")
            UserDefaults.standard.removeObject(forKey: markerKey)
        }
        if persistedExpired { initialToken = nil }
        if initialOverride != nil || initiallyForcedSignedOut { initialToken = nil }
        if initiallyForcedSignedOut { keychain.delete(account: "access-token") }
        bearerToken = initialToken
        devUserOverride = initialOverride
        forceSignedOut = initiallyForcedSignedOut
        state = persistedExpired ? .expired : (initiallyForcedSignedOut ? .unauthenticated : .authenticated)
        #else
        if persistedExpired { initialToken = nil }
        bearerToken = initialToken
        devUserOverride = nil
        forceSignedOut = false
        state = persistedExpired ? .expired : (initialToken == nil ? .unauthenticated : .authenticated)
        #endif
    }

    func headers() -> [String: String] {
        guard state == .authenticated else { return [:] }
        if let bearerToken { return ["Authorization": "Bearer \(bearerToken)"] }
        #if DEV_AUTH
        guard state == .authenticated else { return [:] }
        if let user = devUserOverride ?? (Bundle.main.object(forInfoDictionaryKey: "DevUserID") as? String), !user.isEmpty {
            return ["X-User-ID": user]
        }
        #endif
        return [:]
    }

    func currentUserID() -> String? {
        if let bearerToken,
           let payload = bearerToken.split(separator: ".").dropFirst().first,
           let data = Data(base64URLEncoded: String(payload)),
           let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let subject = object["sub"] as? String {
            return subject
        }
        #if DEV_AUTH
        guard state == .authenticated else { return nil }
        return devUserOverride ?? (Bundle.main.object(forInfoDictionaryKey: "DevUserID") as? String)
        #else
        return nil
        #endif
    }

    func cacheScope() -> String { currentUserID().map { "user:\($0)" } ?? "anonymous" }

    func install(token: String) {
        bearerToken = token
        keychain.write(token, account: "access-token")
        keychain.delete(account: "session-expired")
        UserDefaults.standard.removeObject(forKey: expiredMarkerKey)
        state = .authenticated
    }
    func markExpired() {
        state = .expired
        keychain.write("true", account: "session-expired")
        UserDefaults.standard.set(true, forKey: expiredMarkerKey)
        keychain.delete(account: "access-token")
    }
    func clear() {
        bearerToken = nil
        keychain.delete(account: "access-token")
        keychain.delete(account: "session-expired")
        UserDefaults.standard.removeObject(forKey: expiredMarkerKey)
        state = .unauthenticated
    }

    private static func argumentValue(_ key: String, in arguments: [String]) -> String? {
        guard let index = arguments.firstIndex(of: key), arguments.indices.contains(index + 1) else { return nil }
        return arguments[index + 1]
    }
}

private extension Data {
    init?(base64URLEncoded value: String) {
        var normalized = value.replacingOccurrences(of: "-", with: "+").replacingOccurrences(of: "_", with: "/")
        normalized += String(repeating: "=", count: (4 - normalized.count % 4) % 4)
        self.init(base64Encoded: normalized)
    }
}

struct KeychainStore: Sendable {
    let service: String
    func write(_ value: String, account: String) {
        delete(account: account)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: Data(value.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        SecItemAdd(query as CFDictionary, nil)
    }
    func read(account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: AnyObject?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    func delete(account: String) {
        SecItemDelete([kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: account] as CFDictionary)
    }
}
