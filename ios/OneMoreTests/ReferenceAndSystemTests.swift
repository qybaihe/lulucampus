import Foundation
import XCTest
@testable import ONE_MORE

final class ReferenceAndSystemTests: XCTestCase {
    @MainActor func testPermissionRecoveryStateClearsAfterSettingsGrant() {
        let coordinator = PermissionCoordinator()
        coordinator.recordAuthorization(.photos, granted: false)
        coordinator.recordAuthorization(.microphone, granted: false)
        coordinator.recordAuthorization(.speech, granted: false)
        coordinator.recordAuthorization(.location, granted: false)
        XCTAssertEqual(
            coordinator.denied,
            Set([.photos, .microphone, .speech, .location])
        )
        coordinator.recordAuthorization(.photos, granted: true)
        coordinator.recordAuthorization(.microphone, granted: true)
        coordinator.recordAuthorization(.speech, granted: true)
        coordinator.recordAuthorization(.location, granted: true)
        XCTAssertTrue(coordinator.denied.isEmpty)
    }

    func testPersonalCampusActionCalendarDescriptorAndSingleEventLifecycle() async throws {
        actor Fake: CalendarServicing {
            var accessRequests = 0
            var creates = 0
            var updates = 0
            var deletions: [String] = []
            func requestAccess() async throws -> Bool { accessRequests += 1; return true }
            func create(_ descriptor: CalendarEventDescriptor) async throws -> String {
                creates += 1; return "personal-event"
            }
            func update(_ descriptor: CalendarEventDescriptor, identifier: String) async throws -> Bool {
                updates += 1; return identifier == "personal-event"
            }
            func delete(identifier: String) async throws { deletions.append(identifier) }
        }
        let descriptor = try XCTUnwrap(PersonalActionCalendarDescriptorFactory.make(
            actionID: "action-57",
            actionName: "gym.book_preview",
            params: [
                "venue_type": .string("羽毛球"),
                "venue": .string("南校园体育馆"),
                "date": .string("2026-08-13"),
                "start": .string("05:30"),
                "end": .string("07:00")
            ]
        ))
        XCTAssertEqual(descriptor.title, "体育场馆预约")
        XCTAssertEqual(descriptor.location, "南校园体育馆")
        XCTAssertEqual(descriptor.notes, "onemore://action/action-57")
        XCTAssertEqual(CampusDayCodec.string(from: descriptor.start), "2026-08-13")

        let suite = "tests.calendar.personal-action.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let fake = Fake()
        let registry = CalendarEventRegistry(defaults: defaults, prefix: "test.personal.")
        let reconciler = GatheringCalendarReconciler(service: fake, registry: registry)
        let key = "action:action-57"
        _ = try await reconciler.addOrUpdate(
            gatheringID: key, scope: "user:owner", descriptor: descriptor,
            requestAccess: true
        )
        _ = try await reconciler.addOrUpdate(
            gatheringID: key, scope: "user:owner", descriptor: descriptor,
            requestAccess: true
        )
        let didRemove = try await reconciler.removeIfPresent(
            gatheringID: key,
            scope: "user:owner"
        )
        XCTAssertTrue(didRemove)
        let accessRequests = await fake.accessRequests
        let creates = await fake.creates
        let updates = await fake.updates
        let deletions = await fake.deletions
        XCTAssertEqual(accessRequests, 2)
        XCTAssertEqual(creates, 1)
        XCTAssertEqual(updates, 1)
        XCTAssertEqual(deletions, ["personal-event"])
    }

    func testVersionedReferenceBundleChecksumsAliasesSearchAndSections() async throws {
        let repository = StaticReferenceRepository(bundle: .main)
        try await repository.loadAndValidate()
        let bundleVersion = await repository.bundleVersion
        let searchResults = await repository.search("南门")
        let venues = await repository.venueDirectory(campusID: "guangzhou_south")
        let campuses = await repository.campusDirectory()
        let calendar = await repository.calendarSummary()
        let commute = await repository.commuteMinutes(from: "guangzhou_south", to: "guangzhou_east")
        let firstSectionStart = await repository.section(1)?.0
        XCTAssertEqual(bundleVersion, "sysu-campus-reference-v1.1-south-first")
        XCTAssertFalse(searchResults.isEmpty)
        XCTAssertFalse(venues.isEmpty)
        XCTAssertEqual(campuses.count, 5)
        XCTAssertEqual(campuses.first(where: { $0.id == "zhuhai" })?.city, "珠海")
        XCTAssertEqual(calendar?.academicYear, "2026-2027")
        XCTAssertEqual(calendar?.holidays.first?.name, "中秋节")
        XCTAssertEqual(commute, 30)
        XCTAssertEqual(firstSectionStart, "08:00")
    }

    func testUnsupportedReferenceBundleVersionFailsClosed() {
        XCTAssertThrowsError(
            try StaticReferenceRepository.validateMetadata(
                bundleVersion: "sysu-campus-reference-v9-tampered",
                schemaVersion: "1.1.0",
                unresolvedGapCount: 13
            )
        )
    }

    func testResponseCacheExpirationAndInvalidation() async {
        let root = FileManager.default.temporaryDirectory.appending(path: UUID().uuidString)
        let cache = ResponseCache(root: root)
        await cache.put(Data("cached".utf8), key: "/competitions")
        let fresh = await cache.get(key: "/competitions", maxAge: 60)
        let expired = await cache.get(key: "/competitions", maxAge: -1)
        XCTAssertEqual(fresh, Data("cached".utf8))
        XCTAssertNil(expired)
    }

    func testEventKitProtocolFakeOnlyWritesAfterExplicitCall() async throws {
        actor Fake: CalendarServicing {
            var writes = 0
            func requestAccess() async throws -> Bool { true }
            func create(_ descriptor: CalendarEventDescriptor) async throws -> String { writes += 1; return "event-1" }
            func update(_ descriptor: CalendarEventDescriptor, identifier: String) async throws -> Bool { true }
            func delete(identifier: String) async throws { writes -= 1 }
        }
        let fake = Fake()
        var writes = await fake.writes
        XCTAssertEqual(writes, 0)
        let id = try await fake.create(.init(title: "已执行局", start: .now, end: .now.addingTimeInterval(3600), location: nil, notes: nil))
        XCTAssertEqual(id, "event-1")
        writes = await fake.writes
        XCTAssertEqual(writes, 1)
        try await fake.delete(identifier: id)
        writes = await fake.writes
        XCTAssertEqual(writes, 0)
    }

    func testGatheringCalendarReconcilerWritesUpdatesAndDeletesSameEvent() async throws {
        actor Fake: CalendarServicing {
            var accessRequests = 0
            var saves: [(CalendarEventDescriptor, String?)] = []
            var deletions: [String] = []
            func requestAccess() async throws -> Bool { accessRequests += 1; return true }
            func create(_ descriptor: CalendarEventDescriptor) async throws -> String {
                saves.append((descriptor, nil)); return "event-one"
            }
            func update(_ descriptor: CalendarEventDescriptor, identifier: String) async throws -> Bool {
                saves.append((descriptor, identifier)); return true
            }
            func delete(identifier: String) async throws { deletions.append(identifier) }
        }
        let suite = "tests.calendar.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let fake = Fake()
        let registry = CalendarEventRegistry(defaults: defaults, prefix: "test.calendar.")
        let reconciler = GatheringCalendarReconciler(service: fake, registry: registry)
        let original = CalendarEventDescriptor(
            title: "羽毛球局", start: .now, end: .now.addingTimeInterval(3_600),
            location: "东校园", notes: "onemore://gathering/g1"
        )
        _ = try await reconciler.addOrUpdate(gatheringID: "g1", scope: "user:a", descriptor: original, requestAccess: true)
        let updated = CalendarEventDescriptor(
            title: original.title, start: original.start.addingTimeInterval(7_200),
            end: original.end.addingTimeInterval(7_200), location: original.location, notes: original.notes
        )
        let didUpdate = try await reconciler.updateIfPresent(gatheringID: "g1", scope: "user:a", descriptor: updated)
        let didRemove = try await reconciler.removeIfPresent(gatheringID: "g1", scope: "user:a")
        XCTAssertTrue(didUpdate)
        XCTAssertTrue(didRemove)
        let stillExists = await reconciler.hasEvent(gatheringID: "g1", scope: "user:a")
        XCTAssertFalse(stillExists)
        let accessRequests = await fake.accessRequests
        let saves = await fake.saves
        let deletions = await fake.deletions
        XCTAssertEqual(accessRequests, 1)
        XCTAssertEqual(saves.count, 2)
        XCTAssertNil(saves[0].1)
        XCTAssertEqual(saves[1].1, "event-one")
        XCTAssertEqual(saves[1].0.start, updated.start)
        XCTAssertEqual(deletions, ["event-one"])
    }

    func testRescheduleDoesNotRecreateEventDeletedOutsideTheApp() async throws {
        actor Fake: CalendarServicing {
            var creates = 0
            func requestAccess() async throws -> Bool { true }
            func create(_ descriptor: CalendarEventDescriptor) async throws -> String { creates += 1; return "event-one" }
            func update(_ descriptor: CalendarEventDescriptor, identifier: String) async throws -> Bool { false }
            func delete(identifier: String) async throws {}
        }
        let suite = "tests.calendar.external-delete.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let registry = CalendarEventRegistry(defaults: defaults, prefix: "test.calendar.")
        await registry.set("event-deleted-in-calendar", for: "g1", scope: "user:a")
        let fake = Fake()
        let reconciler = GatheringCalendarReconciler(service: fake, registry: registry)
        let descriptor = CalendarEventDescriptor(
            title: "改约后的局", start: .now, end: .now.addingTimeInterval(3_600), location: nil, notes: nil
        )
        let didUpdate = try await reconciler.updateIfPresent(gatheringID: "g1", scope: "user:a", descriptor: descriptor)
        XCTAssertFalse(didUpdate)
        let creates = await fake.creates
        XCTAssertEqual(creates, 0)
        let exists = await reconciler.hasEvent(gatheringID: "g1", scope: "user:a")
        XCTAssertFalse(exists)
    }

    func testCalendarRegistryIsIsolatedAcrossAccountScopes() async throws {
        actor Fake: CalendarServicing {
            var updates = 0
            func requestAccess() async throws -> Bool { true }
            func create(_ descriptor: CalendarEventDescriptor) async throws -> String { "event" }
            func update(_ descriptor: CalendarEventDescriptor, identifier: String) async throws -> Bool { updates += 1; return true }
            func delete(identifier: String) async throws {}
        }
        let suite = "tests.calendar.scope.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let registry = CalendarEventRegistry(defaults: defaults, prefix: "test.calendar.")
        await registry.set("event-a", for: "shared-gathering", scope: "user:a")
        let fake = Fake()
        let reconciler = GatheringCalendarReconciler(service: fake, registry: registry)
        let descriptor = CalendarEventDescriptor(title: "同一局", start: .now, end: .now.addingTimeInterval(60), location: nil, notes: nil)
        let bUpdated = try await reconciler.updateIfPresent(gatheringID: "shared-gathering", scope: "user:b", descriptor: descriptor)
        let bRemoved = try await reconciler.removeIfPresent(gatheringID: "shared-gathering", scope: "user:b")
        let aExists = await reconciler.hasEvent(gatheringID: "shared-gathering", scope: "user:a")
        let updateCount = await fake.updates
        XCTAssertFalse(bUpdated)
        XCTAssertFalse(bRemoved)
        XCTAssertTrue(aExists)
        XCTAssertEqual(updateCount, 0)
    }

    func testCalendarPreferenceIsAccountScopedAndRegistryCanRemoveAllDisabledEvents() async throws {
        actor Fake: CalendarServicing {
            var deleted: [String] = []
            func requestAccess() async throws -> Bool { true }
            func create(_ descriptor: CalendarEventDescriptor) async throws -> String { "unused" }
            func update(_ descriptor: CalendarEventDescriptor, identifier: String) async throws -> Bool { true }
            func delete(identifier: String) async throws { deleted.append(identifier) }
        }
        let suite = "tests.calendar.preference.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let preference = CalendarSyncPreferenceStore(defaults: defaults, prefix: "test.enabled.")
        await preference.set(true, scope: "user:a")
        let aInitiallyEnabled = await preference.isEnabled(scope: "user:a")
        let bInitiallyEnabled = await preference.isEnabled(scope: "user:b")
        XCTAssertTrue(aInitiallyEnabled)
        XCTAssertFalse(bInitiallyEnabled)

        let registry = CalendarEventRegistry(defaults: defaults, prefix: "test.events.")
        await registry.set("event-1", for: "g1", scope: "user:a")
        await registry.set("event-2", for: "g2", scope: "user:a")
        await registry.set("event-b", for: "g1", scope: "user:b")
        let fake = Fake()
        let reconciler = GatheringCalendarReconciler(service: fake, registry: registry)
        await preference.set(false, scope: "user:a")
        for gatheringID in await registry.gatheringIDs(scope: "user:a") {
            _ = try await reconciler.removeIfPresent(
                gatheringID: gatheringID,
                scope: "user:a"
            )
        }
        let aFinallyEnabled = await preference.isEnabled(scope: "user:a")
        let deleted = await fake.deleted
        let bEventStillExists = await reconciler.hasEvent(gatheringID: "g1", scope: "user:b")
        XCTAssertFalse(aFinallyEnabled)
        XCTAssertEqual(Set(deleted), Set(["event-1", "event-2"]))
        XCTAssertTrue(bEventStillExists)
    }

    func testAccountExportWriterProducesShareableJSONFile() throws {
        let root = FileManager.default.temporaryDirectory.appending(path: UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let now = Date(timeIntervalSince1970: 1_786_460_000)
        let url = try AccountExportFileWriter(root: root).write(
            ["identity": .object(["display_name": .string("刘同学")])],
            now: now
        )
        XCTAssertTrue(url.lastPathComponent.hasPrefix("one-more-data-"))
        XCTAssertTrue(url.lastPathComponent.hasSuffix(".json"))
        let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any]
        XCTAssertEqual((object?["identity"] as? [String: Any])?["display_name"] as? String, "刘同学")
    }
}
