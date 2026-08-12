@preconcurrency import CoreLocation
import EventKit
import Foundation
import AVFAudio
import PhotosUI
import Speech
import SwiftUI
import UIKit
import UserNotifications

struct CalendarEventDescriptor: Equatable, Sendable {
    let title: String
    let start: Date
    let end: Date
    let location: String?
    let notes: String?
}

enum PersonalActionCalendarDescriptorFactory {
    static func make(
        actionID: String,
        actionName: String,
        params: [String: JSONValue]
    ) -> CalendarEventDescriptor? {
        guard actionName.hasPrefix("room.") || actionName.hasPrefix("gym."),
              let date = string("date", in: params),
              let startText = string("start", in: params),
              let endText = string("end", in: params),
              let start = parse(date: date, time: startText),
              let end = parse(date: date, time: endText),
              end > start else { return nil }
        let isRoom = actionName.hasPrefix("room.")
        let room = string("room", in: params)
        let venue = string("venue", in: params)
        let venueType = string("venue_type", in: params)
        let kind = string("kind", in: params)
        let location = isRoom
            ? [kind, room].compactMap { $0 }.joined(separator: " · ")
            : (venue ?? venueType)
        let customTitle = string("title", in: params)
        return .init(
            title: customTitle ?? (isRoom ? "研讨室预约" : "体育场馆预约"),
            start: start,
            end: end,
            location: location.flatMap { $0.isEmpty ? nil : $0 },
            notes: "onemore://action/\(actionID)"
        )
    }

    private static func string(
        _ key: String,
        in params: [String: JSONValue]
    ) -> String? {
        guard case let .string(value)? = params[key] else { return nil }
        return value
    }

    private static func parse(date: String, time: String) -> Date? {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = CampusDayCodec.timeZone
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter.date(from: "\(date) \(time)")
    }
}

protocol CalendarServicing: Sendable {
    func requestAccess() async throws -> Bool
    func create(_ descriptor: CalendarEventDescriptor) async throws -> String
    func update(_ descriptor: CalendarEventDescriptor, identifier: String) async throws -> Bool
    func delete(identifier: String) async throws
}

actor CalendarEventRegistry {
    private let defaults: UserDefaults
    private let prefix: String

    init(defaults: UserDefaults = .standard, prefix: String = "calendar.") {
        self.defaults = defaults
        self.prefix = prefix
    }

    func identifier(for gatheringID: String, scope: String) -> String? {
        defaults.string(forKey: prefix + scope + "." + gatheringID)
    }

    func set(_ identifier: String, for gatheringID: String, scope: String) {
        defaults.set(identifier, forKey: prefix + scope + "." + gatheringID)
    }

    func remove(gatheringID: String, scope: String) {
        defaults.removeObject(forKey: prefix + scope + "." + gatheringID)
    }

    func gatheringIDs(scope: String) -> [String] {
        let scopedPrefix = prefix + scope + "."
        return defaults.dictionaryRepresentation().keys.compactMap { key in
            guard key.hasPrefix(scopedPrefix) else { return nil }
            return String(key.dropFirst(scopedPrefix.count))
        }
    }
}

/// A per-account, local mirror of the server-owned calendar preference. Push
/// handling consults this mirror before touching EventKit, so an already
/// disabled device never recreates an event while a background fetch is late.
actor CalendarSyncPreferenceStore {
    private let defaults: UserDefaults
    private let prefix: String

    init(defaults: UserDefaults = .standard, prefix: String = "calendar.sync-enabled.") {
        self.defaults = defaults
        self.prefix = prefix
    }

    func isEnabled(scope: String) -> Bool {
        defaults.bool(forKey: prefix + scope)
    }

    func set(_ enabled: Bool, scope: String) {
        defaults.set(enabled, forKey: prefix + scope)
    }
}

enum CalendarReconciliationError: LocalizedError {
    case accessDenied
    case noExistingEvent

    var errorDescription: String? {
        switch self {
        case .accessDenied: "日历权限未开启，可稍后到系统设置恢复"
        case .noExistingEvent: "没有需要更新的本地日历事件"
        }
    }
}

/// Keeps the server-authoritative gathering and the one locally-created
/// EventKit event in sync. The registry is the sole source for identifiers,
/// which also lets push reconciliation and foreground UI share one chain.
actor GatheringCalendarReconciler {
    private let service: any CalendarServicing
    private let registry: CalendarEventRegistry

    init(service: any CalendarServicing, registry: CalendarEventRegistry) {
        self.service = service
        self.registry = registry
    }

    func hasEvent(gatheringID: String, scope: String) async -> Bool {
        await registry.identifier(for: gatheringID, scope: scope) != nil
    }

    @discardableResult
    func addOrUpdate(
        gatheringID: String,
        scope: String,
        descriptor: CalendarEventDescriptor,
        requestAccess: Bool
    ) async throws -> String {
        if requestAccess {
            let granted = try await service.requestAccess()
            if !granted { throw CalendarReconciliationError.accessDenied }
        }
        if let existing = await registry.identifier(for: gatheringID, scope: scope) {
            if try await service.update(descriptor, identifier: existing) { return existing }
            await registry.remove(gatheringID: gatheringID, scope: scope)
        }
        let identifier = try await service.create(descriptor)
        await registry.set(identifier, for: gatheringID, scope: scope)
        return identifier
    }

    /// Updates only an event the user previously opted into. A reschedule
    /// never creates a surprise calendar item or asks for permission again.
    @discardableResult
    func updateIfPresent(gatheringID: String, scope: String, descriptor: CalendarEventDescriptor) async throws -> Bool {
        guard let existing = await registry.identifier(for: gatheringID, scope: scope) else { return false }
        guard try await service.update(descriptor, identifier: existing) else {
            await registry.remove(gatheringID: gatheringID, scope: scope)
            return false
        }
        return true
    }

    @discardableResult
    func removeIfPresent(gatheringID: String, scope: String) async throws -> Bool {
        guard let identifier = await registry.identifier(for: gatheringID, scope: scope) else { return false }
        try await service.delete(identifier: identifier)
        await registry.remove(gatheringID: gatheringID, scope: scope)
        return true
    }
}

actor EventKitCalendarService: CalendarServicing {
    private let store = EKEventStore()
    func requestAccess() async throws -> Bool { try await store.requestFullAccessToEvents() }
    func create(_ descriptor: CalendarEventDescriptor) async throws -> String {
        let event = EKEvent(eventStore: store)
        event.calendar = store.defaultCalendarForNewEvents
        event.title = descriptor.title; event.startDate = descriptor.start; event.endDate = descriptor.end
        event.location = descriptor.location; event.notes = descriptor.notes
        try store.save(event, span: .thisEvent, commit: true)
        return event.eventIdentifier
    }
    func update(_ descriptor: CalendarEventDescriptor, identifier: String) async throws -> Bool {
        guard let event = store.event(withIdentifier: identifier) else { return false }
        event.title = descriptor.title; event.startDate = descriptor.start; event.endDate = descriptor.end
        event.location = descriptor.location; event.notes = descriptor.notes
        try store.save(event, span: .thisEvent, commit: true)
        return true
    }
    func delete(identifier: String) async throws {
        guard let event = store.event(withIdentifier: identifier) else { return }
        try store.remove(event, span: .thisEvent, commit: true)
    }
}

@MainActor
final class SpeechTranscriber: ObservableObject {
    @Published private(set) var transcript = ""
    @Published private(set) var isRecording = false
    @Published private(set) var errorMessage: String?
    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "zh-CN"))
    private let engine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    func start(seed: String = "") throws {
        guard !isRecording else { return }
        guard let recognizer, recognizer.isAvailable else {
            throw SpeechTranscriberError.recognizerUnavailable
        }
        transcript = seed
        errorMessage = nil
        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.record, mode: .measurement, options: [.duckOthers])
        try audioSession.setActive(true, options: .notifyOthersOnDeactivation)
        let recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        recognitionRequest.shouldReportPartialResults = true
        request = recognitionRequest
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1_024, format: format) { [weak recognitionRequest] buffer, _ in
            recognitionRequest?.append(buffer)
        }
        task = recognizer.recognitionTask(with: recognitionRequest) { [weak self] result, error in
            Task { @MainActor in
                guard let self else { return }
                if let result { self.transcript = result.bestTranscription.formattedString }
                if let error { self.errorMessage = error.localizedDescription; self.stop() }
                else if result?.isFinal == true { self.stop() }
            }
        }
        engine.prepare()
        try engine.start()
        isRecording = true
    }

    func stop() {
        if engine.isRunning { engine.stop() }
        engine.inputNode.removeTap(onBus: 0)
        request?.endAudio(); request = nil
        task?.cancel(); task = nil
        isRecording = false
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    deinit { task?.cancel(); if engine.isRunning { engine.stop() } }
}

enum SpeechTranscriberError: LocalizedError {
    case recognizerUnavailable
    var errorDescription: String? { "当前语音识别服务不可用，请稍后重试" }
}

@MainActor
final class PermissionCoordinator: NSObject, ObservableObject, @preconcurrency CLLocationManagerDelegate {
    enum Permission: String { case notifications, microphone, speech, photos, location, calendar }
    @Published private(set) var location: CLLocation?
    @Published private(set) var denied: Set<Permission> = []
    private let locationManager = CLLocationManager()
    override init() { super.init(); locationManager.delegate = self }

    /// Keeps the recovery notice aligned with the current system decision.
    /// It is intentionally internal so deterministic unit tests can model the
    /// Settings round-trip without presenting an operating-system prompt.
    func recordAuthorization(_ permission: Permission, granted: Bool) {
        if granted { denied.remove(permission) }
        else { denied.insert(permission) }
    }

    func requestNotificationsAndRegister() async -> Bool {
        do {
            let allowed = try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound])
            recordAuthorization(.notifications, granted: allowed)
            if allowed { UIApplication.shared.registerForRemoteNotifications() }
            return allowed
        } catch { recordAuthorization(.notifications, granted: false); return false }
    }
    func requestVoice() async -> Bool {
        let mic = await AVAudioApplication.requestRecordPermission()
        let speech = await withCheckedContinuation { continuation in SFSpeechRecognizer.requestAuthorization { continuation.resume(returning: $0 == .authorized) } }
        recordAuthorization(.microphone, granted: mic)
        recordAuthorization(.speech, granted: speech)
        return mic && speech
    }
    func requestPhotoSelection() async -> Bool {
        let status = await PHPhotoLibrary.requestAuthorization(for: .readWrite)
        let allowed = status == .authorized || status == .limited
        recordAuthorization(.photos, granted: allowed)
        return allowed
    }
    func requestOneShotLocation() {
        switch locationManager.authorizationStatus {
        case .notDetermined: locationManager.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorizedWhenInUse:
            recordAuthorization(.location, granted: true)
            locationManager.requestLocation()
        case .denied, .restricted:
            recordAuthorization(.location, granted: false)
        @unknown default:
            break
        }
    }
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        if manager.authorizationStatus == .authorizedAlways || manager.authorizationStatus == .authorizedWhenInUse {
            recordAuthorization(.location, granted: true)
            manager.requestLocation()
        } else if manager.authorizationStatus == .denied || manager.authorizationStatus == .restricted {
            recordAuthorization(.location, granted: false)
        }
    }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) { location = locations.last; manager.stopUpdatingLocation() }
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) { location = nil }

    /// Reconciles only settled decisions. `notDetermined` never creates a
    /// warning because the app asks just-in-time when the user taps a feature.
    func refreshDeniedPermissions() async {
        let notificationSettings = await UNUserNotificationCenter.current().notificationSettings()
        switch notificationSettings.authorizationStatus {
        case .authorized, .provisional, .ephemeral:
            recordAuthorization(.notifications, granted: true)
        case .denied:
            recordAuthorization(.notifications, granted: false)
        case .notDetermined:
            break
        @unknown default:
            break
        }

        switch AVAudioApplication.shared.recordPermission {
        case .granted: recordAuthorization(.microphone, granted: true)
        case .denied: recordAuthorization(.microphone, granted: false)
        case .undetermined: break
        @unknown default: break
        }

        switch SFSpeechRecognizer.authorizationStatus() {
        case .authorized: recordAuthorization(.speech, granted: true)
        case .denied, .restricted: recordAuthorization(.speech, granted: false)
        case .notDetermined: break
        @unknown default: break
        }

        switch PHPhotoLibrary.authorizationStatus(for: .readWrite) {
        case .authorized, .limited: recordAuthorization(.photos, granted: true)
        case .denied, .restricted: recordAuthorization(.photos, granted: false)
        case .notDetermined: break
        @unknown default: break
        }

        let locationStatus = locationManager.authorizationStatus
        if locationStatus == .authorizedAlways || locationStatus == .authorizedWhenInUse {
            recordAuthorization(.location, granted: true)
        } else if locationStatus == .denied || locationStatus == .restricted {
            recordAuthorization(.location, granted: false)
        }

        switch EKEventStore.authorizationStatus(for: .event) {
        case .fullAccess, .writeOnly:
            recordAuthorization(.calendar, granted: true)
        case .denied, .restricted:
            recordAuthorization(.calendar, granted: false)
        case .notDetermined:
            break
        @unknown default:
            break
        }
    }
    func openSystemSettings() { if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) } }
}

struct PhotoPicker: UIViewControllerRepresentable {
    let onImage: (Data) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(onImage: onImage) }
    func makeUIViewController(context: Context) -> PHPickerViewController {
        var configuration = PHPickerConfiguration(photoLibrary: .shared())
        configuration.filter = .images; configuration.selectionLimit = 1
        let picker = PHPickerViewController(configuration: configuration); picker.delegate = context.coordinator
        return picker
    }
    func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {}
    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let onImage: (Data) -> Void
        init(onImage: @escaping (Data) -> Void) { self.onImage = onImage }
        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            picker.dismiss(animated: true)
            guard let provider = results.first?.itemProvider, provider.canLoadObject(ofClass: UIImage.self) else { return }
            provider.loadObject(ofClass: UIImage.self) { [onImage] object, _ in if let image = object as? UIImage, let data = image.jpegData(compressionQuality: 0.82) { DispatchQueue.main.async { onImage(data) } } }
        }
    }
}
