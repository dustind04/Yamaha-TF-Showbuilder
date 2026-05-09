import AVFoundation
import CoreMedia
import Combine
import os

/// Manages an `AVCaptureMultiCamSession` that simultaneously streams frames from
/// the rear ultra-wide, wide, and telephoto cameras on supported iPhone Pro hardware.
///
/// Frames from the three cameras are loosely synchronized into `SynchronizedMultiCamFrame`s
/// using a small in-memory buffer keyed by presentation timestamp.
final class MultiCamSession: NSObject, ObservableObject {

    enum SessionError: Error {
        case multiCamUnsupported
        case cameraUnavailable(CameraFrame.Lens)
        case configurationFailed(String)
    }

    @Published private(set) var isRunning = false
    @Published private(set) var availableLenses: Set<CameraFrame.Lens> = []
    @Published private(set) var lastError: SessionError?

    let session = AVCaptureMultiCamSession()

    /// Callback invoked on `frameQueue` for every loosely-synchronized frame set.
    var onFrame: ((SynchronizedMultiCamFrame) -> Void)?

    private let frameQueue = DispatchQueue(label: "showbuilder.multicam.frames", qos: .userInteractive)
    private let sessionQueue = DispatchQueue(label: "showbuilder.multicam.session")
    private let log = Logger(subsystem: "com.yamaha.showbuilder.scanner", category: "MultiCam")

    // Per-lens state.
    private var inputs: [CameraFrame.Lens: AVCaptureDeviceInput] = [:]
    private var outputs: [CameraFrame.Lens: AVCaptureVideoDataOutput] = [:]
    private var connections: [CameraFrame.Lens: AVCaptureConnection] = [:]

    // Loose sync buffer: per-lens latest frame, matched by closest timestamp.
    private struct PendingFrame {
        let frame: CameraFrame
        let receivedAt: TimeInterval
    }
    private var pending: [CameraFrame.Lens: PendingFrame] = [:]
    private let syncToleranceSeconds: Double = 0.040  // ~2 frames at 30 fps

    // External pose provider (IMU + visual SfM-derived).
    var poseProvider: PoseProviding?

    // MARK: - Lifecycle

    func configure() {
        sessionQueue.async { [weak self] in
            guard let self else { return }
            do {
                try self.configureLocked()
            } catch let err as SessionError {
                DispatchQueue.main.async { self.lastError = err }
            } catch {
                DispatchQueue.main.async {
                    self.lastError = .configurationFailed(error.localizedDescription)
                }
            }
        }
    }

    func start() {
        sessionQueue.async { [weak self] in
            guard let self else { return }
            if !self.session.isRunning {
                self.session.startRunning()
                DispatchQueue.main.async { self.isRunning = self.session.isRunning }
            }
        }
    }

    func stop() {
        sessionQueue.async { [weak self] in
            guard let self else { return }
            if self.session.isRunning {
                self.session.stopRunning()
                DispatchQueue.main.async { self.isRunning = false }
            }
        }
    }

    // MARK: - Configuration

    private func configureLocked() throws {
        guard AVCaptureMultiCamSession.isMultiCamSupported else {
            throw SessionError.multiCamUnsupported
        }

        session.beginConfiguration()
        defer { session.commitConfiguration() }

        // Each lens is added independently. If any one fails we skip it but keep going —
        // we want the app usable on devices with only two of the three lenses (e.g. some
        // Pro models without telephoto in some regions / future SKUs).
        let lensSpecs: [(CameraFrame.Lens, AVCaptureDevice.DeviceType)] = [
            (.wide,       .builtInWideAngleCamera),
            (.ultraWide,  .builtInUltraWideCamera),
            (.telephoto,  .builtInTelephotoCamera)
        ]

        var added: [CameraFrame.Lens] = []
        for (lens, type) in lensSpecs {
            do {
                try addCamera(lens: lens, type: type)
                added.append(lens)
            } catch {
                log.warning("Skipping \(lens.rawValue, privacy: .public): \(error.localizedDescription, privacy: .public)")
            }
        }

        guard added.contains(.wide) else {
            throw SessionError.cameraUnavailable(.wide)
        }

        DispatchQueue.main.async { [added] in
            self.availableLenses = Set(added)
        }
    }

    // MARK: - Preview

    /// Build a preview layer for a given lens. Must be called after `configure()`.
    /// The returned layer connects to the same input port that's already in the session.
    func makePreviewLayer(for lens: CameraFrame.Lens) -> AVCaptureVideoPreviewLayer? {
        guard let input = inputs[lens] else { return nil }
        let deviceType: AVCaptureDevice.DeviceType
        switch lens {
        case .wide: deviceType = .builtInWideAngleCamera
        case .ultraWide: deviceType = .builtInUltraWideCamera
        case .telephoto: deviceType = .builtInTelephotoCamera
        }
        guard let port = input.ports(for: .video,
                                     sourceDeviceType: deviceType,
                                     sourceDevicePosition: .back).first else { return nil }
        let layer = AVCaptureVideoPreviewLayer(sessionWithNoConnection: session)
        let connection = AVCaptureConnection(inputPort: port, videoPreviewLayer: layer)
        if session.canAddConnection(connection) {
            session.addConnection(connection)
            connection.videoOrientation = .portrait
        }
        layer.videoGravity = .resizeAspectFill
        return layer
    }

    private func addCamera(lens: CameraFrame.Lens, type: AVCaptureDevice.DeviceType) throws {
        guard let device = AVCaptureDevice.default(type, for: .video, position: .back) else {
            throw SessionError.cameraUnavailable(lens)
        }
        let input = try AVCaptureDeviceInput(device: device)
        guard session.canAddInput(input) else {
            throw SessionError.configurationFailed("can't add input for \(lens.rawValue)")
        }
        // Use addInputWithNoConnections so we explicitly wire the right port to the right output.
        session.addInputWithNoConnections(input)
        inputs[lens] = input

        let output = AVCaptureVideoDataOutput()
        output.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_420YpCbCr8BiPlanarFullRange
        ]
        output.alwaysDiscardsLateVideoFrames = true
        output.setSampleBufferDelegate(self, queue: frameQueue)
        guard session.canAddOutput(output) else {
            throw SessionError.configurationFailed("can't add output for \(lens.rawValue)")
        }
        session.addOutputWithNoConnections(output)
        outputs[lens] = output

        guard let port = input.ports(for: .video,
                                     sourceDeviceType: type,
                                     sourceDevicePosition: .back).first else {
            throw SessionError.configurationFailed("no video port for \(lens.rawValue)")
        }
        let connection = AVCaptureConnection(inputPorts: [port], output: output)
        guard session.canAddConnection(connection) else {
            throw SessionError.configurationFailed("can't add connection for \(lens.rawValue)")
        }
        session.addConnection(connection)
        connection.videoOrientation = .portrait
        if connection.isCameraIntrinsicMatrixDeliverySupported {
            connection.isCameraIntrinsicMatrixDeliveryEnabled = true
        }
        connections[lens] = connection

        // Lock format to a balanced resolution to fit MultiCam hardware budget.
        try lockFormat(on: device, target: CGSize(width: 1280, height: 720), maxFps: 30)
    }

    private func lockFormat(on device: AVCaptureDevice, target: CGSize, maxFps: Double) throws {
        try device.lockForConfiguration()
        defer { device.unlockForConfiguration() }

        // Prefer multi-cam-supported formats nearest the target dimensions.
        let candidates = device.formats.filter { $0.isMultiCamSupported }
        let best = candidates.min { lhs, rhs in
            let ld = abs(CGFloat(CMVideoFormatDescriptionGetDimensions(lhs.formatDescription).width) - target.width)
            let rd = abs(CGFloat(CMVideoFormatDescriptionGetDimensions(rhs.formatDescription).width) - target.width)
            return ld < rd
        }
        if let format = best {
            device.activeFormat = format
            let fps = min(maxFps, format.videoSupportedFrameRateRanges.first?.maxFrameRate ?? maxFps)
            let duration = CMTimeMake(value: 1, timescale: Int32(fps))
            device.activeVideoMinFrameDuration = duration
            device.activeVideoMaxFrameDuration = duration
        }
    }

    // MARK: - Synchronization

    private func ingest(_ frame: CameraFrame) {
        pending[frame.lens] = PendingFrame(frame: frame, receivedAt: CACurrentMediaTime())
        // Anchor matching on the wide frame's timestamp — it's our reference camera.
        guard let wide = pending[.wide] else { return }
        let target = CMTimeGetSeconds(wide.frame.presentationTime)
        var matched: [CameraFrame.Lens: CameraFrame] = [.wide: wide.frame]

        for lens in CameraFrame.Lens.allCases where lens != .wide {
            if let p = pending[lens] {
                let dt = abs(CMTimeGetSeconds(p.frame.presentationTime) - target)
                if dt <= syncToleranceSeconds {
                    matched[lens] = p.frame
                }
            }
        }

        // We require at least the wide; if both other lenses are configured but missing
        // for >2x tolerance, emit anyway so the pipeline keeps moving.
        let configured = Set(inputs.keys)
        let configuredOthers = configured.subtracting([.wide])
        let missingOthers = configuredOthers.subtracting(Set(matched.keys))
        let oldestPending = pending.values.map(\.receivedAt).min() ?? CACurrentMediaTime()
        let staleness = CACurrentMediaTime() - oldestPending
        let shouldEmit = missingOthers.isEmpty || staleness > 2 * syncToleranceSeconds
        guard shouldEmit else { return }

        let pose = poseProvider?.pose(at: wide.frame.presentationTime)

        let sync = SynchronizedMultiCamFrame(
            frames: matched,
            arCameraTransform: pose?.cameraToWorld,
            arIntrinsics: nil,
            captureTimestamp: target
        )
        onFrame?(sync)

        // Clear the wide; let other lenses catch up against the next wide frame.
        pending[.wide] = nil
    }
}

// MARK: - AVCaptureVideoDataOutputSampleBufferDelegate

extension MultiCamSession: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(_ output: AVCaptureOutput,
                       didOutput sampleBuffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        guard let lens = lens(for: output) else { return }
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let pts = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
        let dims = CGSize(
            width: CVPixelBufferGetWidth(pixelBuffer),
            height: CVPixelBufferGetHeight(pixelBuffer)
        )
        let intrinsics = CameraCalibration.intrinsics(from: sampleBuffer)
        let frame = CameraFrame(
            lens: lens,
            pixelBuffer: pixelBuffer,
            presentationTime: pts,
            intrinsics: intrinsics,
            pixelDimensions: dims
        )
        ingest(frame)
    }

    private func lens(for output: AVCaptureOutput) -> CameraFrame.Lens? {
        outputs.first { $0.value === output }?.key
    }
}

/// Adopted by IMU/visual pose providers so MultiCamSession can stamp frames with pose.
protocol PoseProviding: AnyObject {
    func pose(at time: CMTime) -> Pose?
}
