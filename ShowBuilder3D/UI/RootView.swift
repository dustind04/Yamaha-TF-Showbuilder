import SwiftUI

struct RootView: View {
    @EnvironmentObject var session: ScanSession

    var body: some View {
        ZStack {
            CameraPreviewView(session: session.camera, lens: .wide) { point in
                handleTap(at: point)
            }
            .ignoresSafeArea()
            .overlay(pickedPointOverlay)

            VStack {
                Spacer()
                stagePanel
                    .padding()
                    .background(.black.opacity(0.55))
                    .cornerRadius(18)
                    .padding(.horizontal, 16)
                    .padding(.bottom, 32)
            }
        }
        .task {
            session.startup()
        }
        .onDisappear {
            session.shutdown()
        }
        .alert("Error", isPresented: errorBinding, actions: {
            Button("OK") { session.resetEverything() }
        }, message: {
            Text(errorMessage)
        })
    }

    // MARK: - Subviews

    @ViewBuilder
    private var stagePanel: some View {
        switch session.stage {
        case .preparing:
            ProgressView("Preparing cameras…").foregroundStyle(.white)
        case .awaitingFirstPoint:
            instructions("Tap the first reference point on the object.")
        case .awaitingSecondPoint:
            instructions("Tap the second reference point.")
        case .awaitingDistance:
            distanceEntry
        case .calibrating:
            ProgressView("Calibrating…").foregroundStyle(.white)
        case .scanning:
            scanningPanel
        case .meshing:
            ProgressView("Building mesh…").foregroundStyle(.white)
        case .readyToExport:
            exportPanel
        case .error(let message):
            VStack {
                Text(message).foregroundStyle(.red).font(.callout)
                Button("Reset") { session.resetEverything() }
                    .buttonStyle(.borderedProminent)
            }
        }
    }

    private func instructions(_ text: String) -> some View {
        VStack(spacing: 8) {
            Text(text).foregroundStyle(.white).multilineTextAlignment(.center)
            HStack {
                if session.pickedPointA_pixel != nil {
                    Button("Re-pick") { session.cancelPicks() }
                        .buttonStyle(.bordered)
                        .tint(.white)
                }
                Text(lensSummary).font(.caption).foregroundStyle(.white.opacity(0.7))
            }
        }
    }

    private var distanceEntry: some View {
        VStack(spacing: 12) {
            Text("Distance between reference points")
                .foregroundStyle(.white)
            HStack {
                TextField("mm", value: $session.distanceMillimeters, format: .number)
                    .keyboardType(.decimalPad)
                    .padding(8)
                    .background(.white)
                    .cornerRadius(8)
                    .frame(width: 110)
                Text("mm").foregroundStyle(.white)
            }
            HStack {
                Button("Back") { session.cancelPicks() }
                    .buttonStyle(.bordered)
                    .tint(.white)
                Button("Calibrate") { session.performCalibration() }
                    .buttonStyle(.borderedProminent)
            }
        }
    }

    private var scanningPanel: some View {
        VStack(spacing: 8) {
            Text("Sweep the phone slowly around the object.")
                .foregroundStyle(.white)
            Text("Points: \(session.pointCount)")
                .font(.caption)
                .foregroundStyle(.white.opacity(0.85))
            HStack {
                Button("Restart") { session.resetEverything() }
                    .buttonStyle(.bordered)
                    .tint(.white)
                Button("Finish") {
                    session.finishScanning()
                    Task { await runMesh() }
                }
                .buttonStyle(.borderedProminent)
                .disabled(session.pointCount < 64)
            }
        }
    }

    @State private var lastSavedURL: URL?
    @State private var lastTriangleCount: Int = 0

    private var exportPanel: some View {
        VStack(spacing: 12) {
            Text("Mesh ready · \(lastTriangleCount) triangles · \(session.pointCount) points")
                .foregroundStyle(.white)
                .font(.subheadline)
            if let url = lastSavedURL {
                ShareLink(item: url) {
                    Label("Share STL", systemImage: "square.and.arrow.up")
                }
                .buttonStyle(.borderedProminent)
            }
            HStack {
                Button("New Scan") { session.resetEverything() }
                    .buttonStyle(.bordered)
                    .tint(.white)
            }
        }
    }

    private var lensSummary: String {
        let lenses = session.availableLenses.map(\.rawValue).sorted().joined(separator: ", ")
        return lenses.isEmpty ? "Waiting for cameras…" : "Cameras: \(lenses)"
    }

    // MARK: - Overlays

    @ViewBuilder
    private var pickedPointOverlay: some View {
        GeometryReader { proxy in
            ZStack {
                if let a = session.pickedPointA_pixel {
                    PickedDot(color: .yellow)
                        .position(x: a.x * proxy.size.width, y: a.y * proxy.size.height)
                }
                if let b = session.pickedPointB_pixel {
                    PickedDot(color: .cyan)
                        .position(x: b.x * proxy.size.width, y: b.y * proxy.size.height)
                }
            }
        }
        .allowsHitTesting(false)
    }

    // MARK: - Tap handling

    private func handleTap(at normalized: CGPoint) {
        switch session.stage {
        case .awaitingFirstPoint:
            session.setFirstPoint(normalized)
        case .awaitingSecondPoint:
            session.setSecondPoint(normalized)
        default:
            break
        }
    }

    // MARK: - Mesh + export

    @MainActor
    private func runMesh() async {
        let cloudPoints = session.cloud.snapshot()
        let resolution = max(32, min(160, Int(Double(cloudPoints.count).squareRoot() * 2)))
        let triangles = await Task.detached(priority: .userInitiated) {
            SurfaceReconstruction.mesh(from: cloudPoints,
                                       method: .heightField(gridResolution: resolution))
        }.value
        if triangles.isEmpty {
            session.stage = .error("Not enough points to mesh — try sweeping more area.")
            return
        }
        do {
            let url = try writeSTL(triangles)
            lastSavedURL = url
            lastTriangleCount = triangles.count
            session.stage = .readyToExport
        } catch {
            session.stage = .error("Export failed: \(error.localizedDescription)")
        }
    }

    private func writeSTL(_ triangles: [SurfaceReconstruction.Triangle]) throws -> URL {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withYear, .withMonth, .withDay, .withTime]
        let stamp = formatter.string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let url = dir.appendingPathComponent("scan-\(stamp).stl")
        try STLWriter.write(triangles: triangles, to: url)
        return url
    }

    // MARK: - Error binding

    private var errorBinding: Binding<Bool> {
        Binding(
            get: { if case .error = session.stage { return true } else { return false } },
            set: { _ in }
        )
    }
    private var errorMessage: String {
        if case .error(let m) = session.stage { return m }
        return ""
    }
}

private struct PickedDot: View {
    let color: Color
    var body: some View {
        Circle()
            .stroke(color, lineWidth: 2)
            .frame(width: 28, height: 28)
            .background(Circle().fill(color.opacity(0.25)))
    }
}
