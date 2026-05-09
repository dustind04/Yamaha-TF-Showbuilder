import Foundation
import Combine
import simd
import CoreMedia
import CoreVideo
import os

/// Drives the end-to-end scan workflow:
///
///   1. configure cameras + start IMU
///   2. wait for the user to tap two reference points + enter their real-world distance
///   3. calibrate (build CameraRig, run two-point triangulation)
///   4. accumulate triangulated feature points as the user sweeps the phone
///   5. mesh + export STL
final class ScanSession: ObservableObject {

    enum Stage: Equatable {
        case preparing
        case awaitingFirstPoint
        case awaitingSecondPoint
        case awaitingDistance
        case calibrating
        case scanning
        case meshing
        case readyToExport
        case error(String)
    }

    @Published var stage: Stage = .preparing
    @Published var pickedPointA_pixel: CGPoint?     // in wide-frame normalized coords (0..1)
    @Published var pickedPointB_pixel: CGPoint?
    @Published var distanceMillimeters: Double = 20
    @Published var calibration: CalibrationResult?
    @Published var pointCount: Int = 0
    @Published var lastFrameTimestamp: TimeInterval = 0
    @Published var availableLenses: Set<CameraFrame.Lens> = []

    let camera = MultiCamSession()
    let pose = IMUPoseProvider()
    let cloud = PointCloud()
    let tracker = FeatureTracker()

    /// Set to true while we want frame triplets to grow the cloud.
    private var accumulating = false
    private var rig: CameraRig?

    /// Pixel size of the wide camera buffer at capture resolution. Used to convert
    /// normalized tap coordinates back to pixels for triangulation.
    @Published private(set) var widePixelSize: CGSize = .zero

    private var cancellables: Set<AnyCancellable> = []
    private let log = Logger(subsystem: "com.yamaha.showbuilder.scanner", category: "ScanSession")

    private let processingQueue = DispatchQueue(label: "showbuilder.scan.processing", qos: .userInitiated)
    /// Dropped if the previous frame is still processing — keeps us real-time.
    private var processing = false
    private let processingLock = NSLock()

    init() {
        camera.poseProvider = pose
        camera.onFrame = { [weak self] frame in
            self?.dispatchFrame(frame)
        }
        camera.$availableLenses
            .receive(on: DispatchQueue.main)
            .sink { [weak self] in self?.availableLenses = $0 }
            .store(in: &cancellables)
        camera.$lastError
            .compactMap { $0 }
            .receive(on: DispatchQueue.main)
            .sink { [weak self] err in
                self?.stage = .error(String(describing: err))
            }
            .store(in: &cancellables)
    }

    // MARK: - Lifecycle

    func startup() {
        pose.start()
        camera.configure()
        camera.start()
        stage = .awaitingFirstPoint
    }

    func shutdown() {
        camera.stop()
        pose.stop()
    }

    // MARK: - User input

    func setFirstPoint(_ p: CGPoint) {
        pickedPointA_pixel = p
        stage = .awaitingSecondPoint
    }

    func setSecondPoint(_ p: CGPoint) {
        pickedPointB_pixel = p
        stage = .awaitingDistance
    }

    func cancelPicks() {
        pickedPointA_pixel = nil
        pickedPointB_pixel = nil
        stage = .awaitingFirstPoint
    }

    /// Run two-point calibration with the currently-picked points and the user-entered distance.
    /// On success, latch the rig + result and move to scanning.
    func performCalibration() {
        guard let a = pickedPointA_pixel, let b = pickedPointB_pixel else { return }
        guard let latest = lastTripletForCalibration else {
            stage = .error("Waiting for a synchronized 3-camera frame; try again.")
            return
        }
        guard distanceMillimeters > 0 else {
            stage = .error("Enter a positive distance.")
            return
        }
        stage = .calibrating

        let distance = distanceMillimeters / 1000.0
        let tracker = self.tracker

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            do {
                let rig = try Self.buildRig(from: latest)
                let aObs = Self.locate(referencePoint: a, in: latest, rig: rig, tracker: tracker)
                let bObs = Self.locate(referencePoint: b, in: latest, rig: rig, tracker: tracker)
                let result = try Calibration.calibrate(
                    rig: rig,
                    pointA_obs: aObs,
                    pointB_obs: bObs,
                    knownDistance: distance
                )
                DispatchQueue.main.async {
                    self.rig = rig
                    self.calibration = result
                    self.cloud.clear()
                    self.pose.resetWorldFrame()
                    self.accumulating = true
                    self.stage = .scanning
                }
            } catch {
                DispatchQueue.main.async {
                    self.stage = .error("Calibration failed: \(error)")
                }
            }
        }
    }

    func finishScanning() {
        accumulating = false
        stage = .meshing
    }

    func resetEverything() {
        accumulating = false
        cloud.clear()
        rig = nil
        calibration = nil
        pickedPointA_pixel = nil
        pickedPointB_pixel = nil
        stage = .awaitingFirstPoint
    }

    // MARK: - Frame ingestion

    /// Most recent multi-cam triplet, kept for calibration use. Reads/writes on main only.
    private var lastTripletForCalibration: SynchronizedMultiCamFrame?

    /// Called from `MultiCamSession`'s frame queue. We hop to main to update Published state
    /// and snapshot the rig, then off-load the heavy keypoint+triangulation work to the
    /// processing queue. New frames are dropped while the previous one is still in flight.
    private func dispatchFrame(_ frame: SynchronizedMultiCamFrame) {
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            self.lastFrameTimestamp = frame.captureTimestamp
            if let wide = frame.frame(.wide) {
                self.widePixelSize = wide.pixelDimensions
            }
            if frame.frames.count >= 2 {
                self.lastTripletForCalibration = frame
            }

            guard self.accumulating, let rig = self.rig else { return }
            // Drop if we're still processing the previous frame.
            self.processingLock.lock()
            if self.processing { self.processingLock.unlock(); return }
            self.processing = true
            self.processingLock.unlock()

            let scale = self.calibration?.scale ?? 1.0
            self.processingQueue.async {
                let added = self.growCloud(from: frame, rig: rig, scale: scale)
                DispatchQueue.main.async {
                    self.pointCount = self.cloud.count
                    self.processingLock.lock()
                    self.processing = false
                    self.processingLock.unlock()
                    _ = added   // silence unused warning; could be used for telemetry
                }
            }
        }
    }

    /// Grow the point cloud from a single multi-cam triplet. Per-triplet we:
    ///   - Detect keypoints in the wide frame.
    ///   - For each keypoint, find a correspondence in the ultra-wide and telephoto frames
    ///     (using the rig extrinsics as a baseline epipolar prior is future work; for now
    ///     we use NCC search with a generous radius).
    ///   - Triangulate and add to the cloud.
    /// Runs on `processingQueue`. Mutates `cloud` (which is internally locked).
    /// Returns the count of newly-added points for telemetry.
    private func growCloud(from frame: SynchronizedMultiCamFrame,
                           rig: CameraRig,
                           scale: Double) -> Int {
        guard let wide = frame.frame(.wide) else { return 0 }
        let wideKp = tracker.detectKeypoints(in: wide.pixelBuffer, maxPoints: 256)
        if wideKp.isEmpty { return 0 }

        // For now we reconstruct in the rig's instantaneous frame at capture time.
        // Cross-frame registration is the next step — see README "Known limitations".
        let worldToWide = matrix_identity_double4x4
        var added = 0

        for lens in [CameraFrame.Lens.ultraWide, .telephoto] {
            guard let other = frame.frame(lens) else { continue }
            let otherKp = tracker.detectKeypoints(in: other.pixelBuffer, maxPoints: 256)
            let matches = tracker.match(wide.pixelBuffer, keypoints: wideKp,
                                        to: other.pixelBuffer, keypoints: otherKp,
                                        searchRadius: 120, minConfidence: 0.7)
            guard
                let pWide = rig.projection(for: .wide, worldToWide: worldToWide),
                let pOther = rig.projection(for: lens, worldToWide: worldToWide)
            else { continue }

            for m in matches.prefix(80) {
                let views: [Triangulation.View] = [
                    .init(projection: pWide,  pixel: SIMD2<Double>(Double(m.a.pixel.x), Double(m.a.pixel.y))),
                    .init(projection: pOther, pixel: SIMD2<Double>(Double(m.b.pixel.x), Double(m.b.pixel.y)))
                ]
                guard let result = Triangulation.triangulate(views) else { continue }
                if result.rms > 4.0 { continue }
                if result.point.z <= 0 { continue }
                let metric = result.point * scale
                let world = SIMD3<Float>(metric)
                cloud.add(.init(
                    position: world,
                    color: SIMD3<Float>(repeating: 0.7),
                    confidence: 1 / Float(max(0.1, result.rms))
                ))
                added += 1
            }
        }
        return added
    }

    // MARK: - Rig assembly

    /// Build a `CameraRig` from a triplet. Intrinsics come from per-frame attachments;
    /// inter-camera extrinsics come from the user's two-point calibration is not enough
    /// data on its own — for the v1 we use a rough factory baseline (small horizontal
    /// offset along +x for ultra-wide / -x for telephoto) and let the two-point step
    /// rescale globally. A future revision should query AVCameraCalibrationData.
    static func buildRig(from frame: SynchronizedMultiCamFrame) throws -> CameraRig {
        var intrinsics: [CameraFrame.Lens: simd_double3x3] = [:]
        var extrinsics: [CameraFrame.Lens: simd_double4x4] = [:]
        for (lens, f) in frame.frames {
            guard let k = f.intrinsics else {
                throw CalibrationError.extrinsicsUnknown
            }
            intrinsics[lens] = simd_double3x3(k)
            extrinsics[lens] = factoryWideToLens(lens: lens)
        }
        guard intrinsics[.wide] != nil else { throw CalibrationError.extrinsicsUnknown }
        return CameraRig(intrinsics: intrinsics, extrinsicFromWide: extrinsics)
    }

    /// Approximate factory baselines along the iPhone Pro camera-bump axis.
    /// These are placeholders, refined globally by two-point calibration scale.
    /// The wide camera is the rig origin (identity).
    private static func factoryWideToLens(lens: CameraFrame.Lens) -> simd_double4x4 {
        switch lens {
        case .wide:
            return matrix_identity_double4x4
        case .ultraWide:
            return translationMatrix(SIMD3<Double>(-0.014, 0.000, 0))
        case .telephoto:
            return translationMatrix(SIMD3<Double>(0.012, -0.012, 0))
        }
    }

    private static func translationMatrix(_ t: SIMD3<Double>) -> simd_double4x4 {
        var m = matrix_identity_double4x4
        m.columns.3 = SIMD4<Double>(t, 1)
        return m
    }

    /// Locate a user-tapped reference point across all available lenses.
    /// We patch-match around the mapped ultra-wide / telephoto location to find the same
    /// physical feature visible in the other cameras.
    static func locate(referencePoint normalized: CGPoint,
                       in frame: SynchronizedMultiCamFrame,
                       rig: CameraRig,
                       tracker: FeatureTracker) -> [Calibration.ReferenceObservation] {
        guard let wide = frame.frame(.wide) else { return [] }
        let widePixel = SIMD2<Double>(
            Double(normalized.x) * Double(wide.pixelDimensions.width),
            Double(normalized.y) * Double(wide.pixelDimensions.height)
        )
        var observations: [Calibration.ReferenceObservation] = [
            .init(lens: .wide, pixel: widePixel)
        ]

        for lens in [CameraFrame.Lens.ultraWide, .telephoto] {
            guard let other = frame.frame(lens) else { continue }
            let predicted = predictedPixel(of: widePixel, fromWideTo: lens, rig: rig)
            let aKey = FeatureTracker.Keypoint(pixel: SIMD2<Float>(Float(widePixel.x), Float(widePixel.y)), id: 0)
            let bKey = FeatureTracker.Keypoint(pixel: SIMD2<Float>(Float(predicted.x), Float(predicted.y)), id: 1)
            let matches = tracker.match(wide.pixelBuffer, keypoints: [aKey],
                                        to: other.pixelBuffer, keypoints: [bKey],
                                        searchRadius: 200, minConfidence: 0.5)
            if let m = matches.first {
                observations.append(.init(
                    lens: lens,
                    pixel: SIMD2<Double>(Double(m.b.pixel.x), Double(m.b.pixel.y))
                ))
            }
        }
        return observations
    }

    /// First-order pixel prediction in the other lens by assuming the reference point lies on
    /// a plane ~25cm in front of the wide camera. Refined by the patch-match above.
    private static func predictedPixel(of widePixel: SIMD2<Double>,
                                       fromWideTo lens: CameraFrame.Lens,
                                       rig: CameraRig) -> SIMD2<Double> {
        guard let kw = rig.intrinsics[.wide],
              let ke = rig.intrinsics[lens],
              let we = rig.extrinsicFromWide[lens] else { return widePixel }
        let x = (widePixel.x - kw.columns.2.x) / kw.columns.0.x
        let y = (widePixel.y - kw.columns.2.y) / kw.columns.1.y
        let Z = 0.25
        let Pwide = SIMD4<Double>(x * Z, y * Z, Z, 1)
        let Plens = we * Pwide
        guard Plens.z > 1e-6 else { return widePixel }
        let u = ke.columns.0.x * (Plens.x / Plens.z) + ke.columns.2.x
        let v = ke.columns.1.y * (Plens.y / Plens.z) + ke.columns.2.y
        return SIMD2<Double>(u, v)
    }
}
