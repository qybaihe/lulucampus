import CryptoKit
import Foundation

struct ReferencePlace: Identifiable, Hashable, Sendable {
    let id, campusID, name, category, location: String
    let aliases: [String]
    let confidence: String
}

struct ReferenceVenue: Identifiable, Hashable, Sendable {
    let id, campusID, placeID, name, type, confidence: String
    let capacity: Int?
}

struct ReferenceCampus: Identifiable, Hashable, Sendable {
    let id, name, city, address, confidence: String
    let aliases: [String]
}

struct ReferenceAcademicCalendar: Equatable, Sendable {
    struct Holiday: Equatable, Sendable {
        let name, startDate, endDate: String
    }
    let academicYear, term, termStart, termEnd: String
    let teachingWeekCount: Int
    let holidays: [Holiday]
    let confidence: String
}

actor StaticReferenceRepository {
    static let supportedBundleVersion = "sysu-campus-reference-v1.1-south-first"
    enum ReferenceError: LocalizedError { case missing(String), checksum(String), mixedVersion, malformed(String) }
    struct Manifest: Decodable { let bundleVersion: String; let schemaVersion: String; let checksums: [String: String]; let unresolvedGapCount: Int }
    private(set) var bundleVersion: String?
    private(set) var places: [ReferencePlace] = []
    private(set) var venues: [ReferenceVenue] = []
    private(set) var campuses: [ReferenceCampus] = []
    private(set) var academicCalendar: ReferenceAcademicCalendar?
    private var aliases: [String: String] = [:]
    private var commute: [String: Int?] = [:]
    private var sections: [(Int, String, String)] = []
    private let bundle: Bundle

    init(bundle: Bundle = .main) { self.bundle = bundle }

    nonisolated static func validateMetadata(
        bundleVersion: String,
        schemaVersion: String,
        unresolvedGapCount: Int
    ) throws {
        guard bundleVersion == supportedBundleVersion,
              schemaVersion == "1.1.0",
              unresolvedGapCount == 13 else { throw ReferenceError.mixedVersion }
    }

    func loadAndValidate() throws {
        let manifestData = try data(named: "sysu-manifest.json")
        let decoder = JSONDecoder(); decoder.keyDecodingStrategy = .convertFromSnakeCase
        let manifest = try decoder.decode(Manifest.self, from: manifestData)
        try Self.validateMetadata(
            bundleVersion: manifest.bundleVersion,
            schemaVersion: manifest.schemaVersion,
            unresolvedGapCount: manifest.unresolvedGapCount
        )
        var validated: [String: Data] = [:]
        for (name, expected) in manifest.checksums {
            let payload = try data(named: name.replacingOccurrences(of: "/", with: "__"))
            let digest = SHA256.hash(data: payload).map { String(format: "%02x", $0) }.joined()
            guard digest == expected else { throw ReferenceError.checksum(name) }
            validated[name] = payload
        }
        guard Set(["campuses.v1.json", "aliases.v1.json", "places.v1.json", "venues.v1.json", "transit_2026_fall.json", "section_times_2026_fall.json", "academic_calendar_2026_2027.json"]).isSubset(of: validated.keys) else { throw ReferenceError.mixedVersion }
        campuses = try parseCampuses(validated["campuses.v1.json"]!)
        aliases = try parseAliases(validated["aliases.v1.json"]!)
        places = try parsePlaces(validated["places.v1.json"]!)
        venues = try parseVenues(validated["venues.v1.json"]!)
        commute = try parseCommute(validated["transit_2026_fall.json"]!)
        sections = try parseSections(validated["section_times_2026_fall.json"]!)
        academicCalendar = try parseAcademicCalendar(validated["academic_calendar_2026_2027.json"]!)
        bundleVersion = manifest.bundleVersion
    }

    func ensureReady() throws {
        if bundleVersion == nil { try loadAndValidate() }
    }

    func search(_ query: String) -> [ReferencePlace] {
        let value = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !value.isEmpty else { return Array(places.prefix(20)) }
        let canonical = aliases[value]
        return places.filter { item in item.id == canonical || item.name.lowercased().contains(value) || item.aliases.contains(where: { $0.lowercased().contains(value) }) }.prefix(30).map { $0 }
    }
    func campusDirectory() -> [ReferenceCampus] { campuses }
    func calendarSummary() -> ReferenceAcademicCalendar? { academicCalendar }
    func venueDirectory(campusID: String?) -> [ReferenceVenue] { venues.filter { campusID == nil || $0.campusID == campusID } }
    func commuteMinutes(from: String, to: String) -> Int? { commute["\(from)->\(to)"] ?? nil }
    func section(_ number: Int) -> (String, String)? { sections.first(where: { $0.0 == number }).map { ($0.1, $0.2) } }

    private func data(named filename: String) throws -> Data {
        let name = (filename as NSString).deletingPathExtension, ext = (filename as NSString).pathExtension
        guard let url = bundle.url(forResource: name, withExtension: ext.isEmpty ? nil : ext) ?? bundle.url(forResource: name, withExtension: ext.isEmpty ? nil : ext, subdirectory: "SYSU") else { throw ReferenceError.missing(filename) }
        return try Data(contentsOf: url)
    }
    private func object(_ data: Data) throws -> [String: Any] { guard let value = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw ReferenceError.malformed("json") }; return value }
    private func parseAliases(_ data: Data) throws -> [String: String] {
        let rows = try object(data)["aliases"] as? [[String: Any]] ?? []
        return Dictionary(uniqueKeysWithValues: rows.compactMap { row in guard let alias = row["alias"] as? String, let id = row["canonical_id"] as? String else { return nil }; return (alias.lowercased(), id) })
    }
    private func parseCampuses(_ data: Data) throws -> [ReferenceCampus] {
        (try object(data)["campuses"] as? [[String: Any]] ?? []).compactMap { row in
            guard let id = row["id"] as? String,
                  let name = row["canonical_name"] as? String else { return nil }
            return ReferenceCampus(
                id: id,
                name: name,
                city: row["city"] as? String ?? "",
                address: row["official_address"] as? String ?? "",
                confidence: row["confidence"] as? String ?? "partial",
                aliases: row["aliases"] as? [String] ?? []
            )
        }
    }
    private func parsePlaces(_ data: Data) throws -> [ReferencePlace] {
        (try object(data)["places"] as? [[String: Any]] ?? []).compactMap { row in
            guard let id = row["id"] as? String, let campus = row["campus_id"] as? String, let name = row["canonical_name"] as? String else { return nil }
            return ReferencePlace(id: id, campusID: campus, name: name, category: row["category"] as? String ?? "unknown", location: row["location_text"] as? String ?? "", aliases: row["aliases"] as? [String] ?? [], confidence: row["confidence"] as? String ?? "unverified")
        }
    }
    private func parseVenues(_ data: Data) throws -> [ReferenceVenue] {
        (try object(data)["venues"] as? [[String: Any]] ?? []).compactMap { row in
            guard let id = row["id"] as? String, let campus = row["campus_id"] as? String, let place = row["place_id"] as? String, let name = row["canonical_name"] as? String else { return nil }
            return ReferenceVenue(id: id, campusID: campus, placeID: place, name: name, type: row["venue_type"] as? String ?? "unknown", confidence: row["confidence"] as? String ?? "unverified", capacity: row["capacity"] as? Int)
        }
    }
    private func parseCommute(_ data: Data) throws -> [String: Int?] {
        let rows = try object(data)["campus_commute_matrix"] as? [[String: Any]] ?? []
        return Dictionary(uniqueKeysWithValues: rows.compactMap { row in guard let from = row["from_campus_id"] as? String, let to = row["to_campus_id"] as? String else { return nil }; return ("\(from)->\(to)", row["typical_minutes"] as? Int) })
    }
    private func parseSections(_ data: Data) throws -> [(Int, String, String)] {
        (try object(data)["sections"] as? [[String: Any]] ?? []).compactMap { row in guard let number = row["section_number"] as? Int, let start = row["start_time"] as? String, let end = row["end_time"] as? String else { return nil }; return (number, start, end) }
    }
    private func parseAcademicCalendar(_ data: Data) throws -> ReferenceAcademicCalendar {
        let root = try object(data)
        guard let academicYear = root["academic_year"] as? String,
              let term = root["term"] as? String,
              let termStart = root["term_start"] as? String,
              let termEnd = root["term_end"] as? String else {
            throw ReferenceError.malformed("academic_calendar")
        }
        let holidays = (root["holidays"] as? [[String: Any]] ?? []).compactMap { row -> ReferenceAcademicCalendar.Holiday? in
            guard let name = row["name"] as? String,
                  let start = row["start_date"] as? String,
                  let end = row["end_date"] as? String else { return nil }
            return .init(name: name, startDate: start, endDate: end)
        }
        return .init(
            academicYear: academicYear,
            term: term,
            termStart: termStart,
            termEnd: termEnd,
            teachingWeekCount: root["teaching_week_count"] as? Int ?? 0,
            holidays: holidays,
            confidence: root["confidence"] as? String ?? "partial"
        )
    }
}
