import Foundation

protocol ResponseCaching: Sendable {
    func put(_ data: Data, key: String) async
    func get(key: String, maxAge: TimeInterval) async -> Data?
    func invalidate(prefix: String) async
    func removeAll() async
}

actor ResponseCache: ResponseCaching {
    struct Entry: Codable, Sendable { let data: Data; let storedAt: Date }
    private let root: URL
    init(root: URL? = nil) {
        self.root = root ?? FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0].appending(path: "OneMoreResponses")
        try? FileManager.default.createDirectory(at: self.root, withIntermediateDirectories: true)
    }
    func put(_ data: Data, key: String) {
        let safe = Data(key.utf8).base64EncodedString().replacingOccurrences(of: "/", with: "_")
        try? JSONEncoder().encode(Entry(data: data, storedAt: .now)).write(
            to: root.appending(path: safe),
            options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication]
        )
    }
    func get(key: String, maxAge: TimeInterval) -> Data? {
        let safe = Data(key.utf8).base64EncodedString().replacingOccurrences(of: "/", with: "_")
        guard let data = try? Data(contentsOf: root.appending(path: safe)),
              let entry = try? JSONDecoder().decode(Entry.self, from: data),
              Date().timeIntervalSince(entry.storedAt) <= maxAge else { return nil }
        return entry.data
    }
    func invalidate(prefix: String) {
        guard let files = try? FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil) else { return }
        for file in files where file.lastPathComponent.contains(Data(prefix.utf8).base64EncodedString().prefix(5)) { try? FileManager.default.removeItem(at: file) }
    }
    func removeAll() {
        try? FileManager.default.removeItem(at: root)
        try? FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    }
}
