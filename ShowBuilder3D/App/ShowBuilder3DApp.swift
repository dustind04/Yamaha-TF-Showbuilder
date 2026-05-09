import SwiftUI

@main
struct ShowBuilder3DApp: App {
    @StateObject private var session = ScanSession()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(session)
                .preferredColorScheme(.dark)
        }
    }
}
