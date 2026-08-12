import Network
import SwiftUI

protocol NetworkAvailabilityProviding: Sendable {
    func online() async -> Bool
}

actor NetworkAvailability: NetworkAvailabilityProviding {
    private var value: Bool
    init(initiallyOnline: Bool = true) { value = initiallyOnline }
    func online() -> Bool { value }
    func update(_ online: Bool) { value = online }
}

@MainActor
final class NetworkMonitor: ObservableObject {
    @Published private(set) var isOnline = true
    @Published private(set) var isExpensive = false
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "OneMore.NetworkMonitor")
    private let availability: NetworkAvailability
    private let onReconnect: @Sendable () async -> Void
    init(
        availability: NetworkAvailability,
        onReconnect: @escaping @Sendable () async -> Void = {}
    ) {
        self.availability = availability
        self.onReconnect = onReconnect
        monitor.pathUpdateHandler = { [weak self] path in
            guard let self else { return }
            let online = path.status == .satisfied
            Task {
                await availability.update(online)
                await MainActor.run {
                    let reconnected = !self.isOnline && online
                    self.isOnline = online
                    self.isExpensive = path.isExpensive
                    if reconnected { Task { await self.onReconnect() } }
                }
            }
        }
        monitor.start(queue: queue)
    }
    deinit { monitor.cancel() }
}
