import Foundation
import SwiftUI
import Combine

@MainActor
final class AppEnvironment: ObservableObject {
    let auth: AuthManager
    let api: APIClient
    let webSocket: WebSocketClient
    let today: TodayRepository
    let campusEvents: CampusEventRepository
    let competitions: CompetitionRepository
    let intents: IntentRepository
    let identity: IdentityRepository
    let social: SocialRepository
    let gatherings: GatheringRepository
    let actions: ActionRepository
    let tasteImport: TasteImportRepository
    let organizer: OrganizerRepository
    let referenceData: StaticReferenceRepository
    let calendar: any CalendarServicing
    let calendarRegistry: CalendarEventRegistry
    let calendarReconciler: GatheringCalendarReconciler
    let calendarPreferenceStore: CalendarSyncPreferenceStore
    let diagnostics: NetworkDiagnostics
    let networkAvailability: NetworkAvailability
    let networkMonitor: NetworkMonitor
    let permissions = PermissionCoordinator()
    let speech = SpeechTranscriber()
    let motion = LuluMotionEngine()
    let pushTokens: PushTokenRegistrar
    let recovery: SessionRecoveryStore
    let session: AppSessionController
    @Published private(set) var referenceDataError: String?
    @Published private(set) var calendarReconciliationError: String?
    private var cancellables: Set<AnyCancellable> = []

    init(bundle: Bundle = .main) {
        auth = AuthManager()
        diagnostics = NetworkDiagnostics()
        let availability = NetworkAvailability()
        networkAvailability = availability
        let apiURLString = bundle.object(forInfoDictionaryKey: "APIBaseURL") as? String ?? ""
        let socketURLString = bundle.object(forInfoDictionaryKey: "WebSocketBaseURL") as? String ?? ""
        guard let apiURL = URL(string: apiURLString), let socketURL = URL(string: socketURLString) else { fatalError("APIBaseURL/WebSocketBaseURL missing") }
        api = APIClient(
            baseURL: apiURL,
            auth: auth,
            diagnostics: diagnostics,
            network: availability
        )
        let apiForReconnect = api
        networkMonitor = NetworkMonitor(availability: availability) {
            await apiForReconnect.resumePendingMutations()
        }
        pushTokens = PushTokenRegistrar(api: api, auth: auth)
        recovery = SessionRecoveryStore()
        webSocket = WebSocketClient(baseURL: socketURL, auth: auth)
        today = TodayRepository(api: api)
        campusEvents = CampusEventRepository(api: api)
        competitions = CompetitionRepository(api: api)
        intents = IntentRepository(api: api); identity = IdentityRepository(api: api); social = SocialRepository(api: api)
        gatherings = GatheringRepository(api: api); actions = ActionRepository(api: api)
        tasteImport = TasteImportRepository(api: api); organizer = OrganizerRepository(api: api)
        referenceData = StaticReferenceRepository(bundle: bundle)
        let eventCalendar = EventKitCalendarService()
        let eventRegistry = CalendarEventRegistry()
        calendar = eventCalendar
        calendarRegistry = eventRegistry
        calendarReconciler = GatheringCalendarReconciler(service: eventCalendar, registry: eventRegistry)
        calendarPreferenceStore = CalendarSyncPreferenceStore()
        let apiForReset = api
        let todayForReset = today
        let competitionsForReset = competitions
        let socketForReset = webSocket
        let pushForSession = pushTokens
        session = AppSessionController(
            auth: auth,
            resetSessionData: {
                await socketForReset.disconnect()
                await todayForReset.invalidate()
                await competitionsForReset.invalidate()
                await apiForReset.clearSessionData()
            },
            deactivateNotificationsBeforeSignOut: {
                try await pushForSession.deactivateBeforeSignOut()
            },
            deactivateNotificationsAfterExpiry: {
                await pushForSession.deactivateAfterSessionExpiry()
            },
            resumeNotificationsAfterAuthentication: {
                await pushForSession.resumeAfterAuthentication()
            }
        )
        // RootView observes AppEnvironment, while authentication is owned by
        // the nested session controller. Forward those changes so a completed
        // login immediately replaces A3 with the account-scoped A4 flow.
        session.objectWillChange
            .sink { [weak self] _ in self?.objectWillChange.send() }
            .store(in: &cancellables)
        networkMonitor.objectWillChange
            .sink { [weak self] _ in self?.objectWillChange.send() }
            .store(in: &cancellables)
        Task {
            do { try await referenceData.loadAndValidate() }
            catch { referenceDataError = error.localizedDescription }
        }
    }

    func reconcileCalendarPush(_ event: CalendarPushEvent) async {
        let scope = await auth.cacheScope()
        let pendingKey = "calendar.pending-push.\(scope)"
        do {
            switch event {
            case let .remove(gatheringID):
                _ = try await calendarReconciler.removeIfPresent(gatheringID: gatheringID, scope: scope)
            case let .sync(gatheringID), let .refresh(gatheringID):
                guard await calendarPreferenceStore.isEnabled(scope: scope) else {
                    _ = try await calendarReconciler.removeIfPresent(
                        gatheringID: gatheringID,
                        scope: scope
                    )
                    calendarReconciliationError = nil
                    UserDefaults.standard.removeObject(forKey: pendingKey)
                    return
                }
                let gathering = try await gatherings.detail(gatheringID)
                guard let start = gathering.startAt, let end = gathering.endAt else { return }
                let descriptor = CalendarEventDescriptor(
                        title: gathering.title,
                        start: start,
                        end: end,
                        location: gathering.location,
                        notes: "onemore://gathering/\(gathering.id)/space"
                )
                if case .sync(_) = event {
                    let exists = await calendarReconciler.hasEvent(
                        gatheringID: gatheringID,
                        scope: scope
                    )
                    _ = try await calendarReconciler.addOrUpdate(
                        gatheringID: gatheringID,
                        scope: scope,
                        descriptor: descriptor,
                        requestAccess: !exists
                    )
                } else {
                    _ = try await calendarReconciler.updateIfPresent(
                        gatheringID: gatheringID,
                        scope: scope,
                        descriptor: descriptor
                    )
                }
            }
            calendarReconciliationError = nil
            UserDefaults.standard.removeObject(forKey: pendingKey)
        } catch {
            calendarReconciliationError = error.localizedDescription
            let encoded: String
            switch event {
            case let .remove(id): encoded = "remove|\(id)"
            case let .sync(id): encoded = "sync|\(id)"
            case let .refresh(id): encoded = "refresh|\(id)"
            }
            UserDefaults.standard.set(encoded, forKey: pendingKey)
        }
    }

    func retryPendingCalendarPush() async {
        let scope = await auth.cacheScope()
        let pendingKey = "calendar.pending-push.\(scope)"
        guard let encoded = UserDefaults.standard.string(forKey: pendingKey) else { return }
        let parts = encoded.split(separator: "|", maxSplits: 1).map(String.init)
        guard parts.count == 2 else {
            UserDefaults.standard.removeObject(forKey: pendingKey)
            return
        }
        let event: CalendarPushEvent = switch parts[0] {
        case "remove": .remove(gatheringID: parts[1])
        case "sync": .sync(gatheringID: parts[1])
        default: .refresh(gatheringID: parts[1])
        }
        await reconcileCalendarPush(event)
    }

    func applyCalendarPreference(enabled: Bool) async {
        let scope = await auth.cacheScope()
        await calendarPreferenceStore.set(enabled, scope: scope)
        do {
            if !enabled {
                for gatheringID in await calendarRegistry.gatheringIDs(scope: scope) {
                    _ = try await calendarReconciler.removeIfPresent(
                        gatheringID: gatheringID,
                        scope: scope
                    )
                }
                calendarReconciliationError = nil
                UserDefaults.standard.removeObject(forKey: "calendar.pending-push.\(scope)")
                return
            }
            let items = try await gatherings.mine()
            var requestedAccess = false
            for gathering in items {
                guard [.executed, .active].contains(gathering.status),
                      let start = gathering.startAt,
                      let end = gathering.endAt else { continue }
                let exists = await calendarReconciler.hasEvent(
                    gatheringID: gathering.id,
                    scope: scope
                )
                _ = try await calendarReconciler.addOrUpdate(
                    gatheringID: gathering.id,
                    scope: scope,
                    descriptor: .init(
                        title: gathering.title,
                        start: start,
                        end: end,
                        location: gathering.location,
                        notes: "onemore://gathering/\(gathering.id)/space"
                    ),
                    requestAccess: !exists && !requestedAccess
                )
                requestedAccess = requestedAccess || !exists
            }
            calendarReconciliationError = nil
        } catch {
            calendarReconciliationError = error.localizedDescription
        }
    }

    func refreshCalendarPreference() async {
        guard session.isAuthenticated else { return }
        do {
            let preferences = try await social.notificationPreferences()
            await applyCalendarPreference(enabled: preferences.calendarSyncEnabled)
        } catch {
            calendarReconciliationError = error.localizedDescription
        }
    }

    func cacheCalendarPreference(_ enabled: Bool) async {
        let scope = await auth.cacheScope()
        await calendarPreferenceStore.set(enabled, scope: scope)
    }
}
