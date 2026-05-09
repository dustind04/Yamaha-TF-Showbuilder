import Foundation
import CoreMotion
import CoreMedia
import simd

/// Provides a per-frame orientation prior (and a heavily-drifting translation prior)
/// from CoreMotion. Translation from raw IMU is unreliable beyond a couple of seconds —
/// our reconstruction pipeline overrides translation with PnP estimates derived from the
/// metric-anchored point cloud.
final class IMUPoseProvider: PoseProviding {

    private let manager = CMMotionManager()
    private let queue = OperationQueue()

    private var samples: [Sample] = []
    private let samplesLock = NSLock()
    private let maxSamples = 600

    private struct Sample {
        let time: TimeInterval
        let attitude: simd_quatf
        let translation: SIMD3<Float>
    }

    // Simple double-integrated translation. Reset to zero whenever calibration anchors world.
    private var velocity: SIMD3<Float> = .zero
    private var position: SIMD3<Float> = .zero
    private var lastSampleTime: TimeInterval?

    init() {
        queue.name = "showbuilder.imu"
        queue.qualityOfService = .userInitiated
    }

    func start() {
        guard manager.isDeviceMotionAvailable else { return }
        manager.deviceMotionUpdateInterval = 1.0 / 100.0   // 100 Hz
        manager.startDeviceMotionUpdates(using: .xArbitraryCorrectedZVertical, to: queue) { [weak self] motion, _ in
            guard let self, let motion else { return }
            self.ingest(motion)
        }
    }

    func stop() {
        manager.stopDeviceMotionUpdates()
    }

    /// Reset the world frame to be aligned with the current device pose at this instant.
    /// Call this when the user confirms calibration.
    func resetWorldFrame() {
        samplesLock.lock()
        defer { samplesLock.unlock() }
        velocity = .zero
        position = .zero
        lastSampleTime = nil
        samples.removeAll(keepingCapacity: true)
    }

    private func ingest(_ motion: CMDeviceMotion) {
        let t = motion.timestamp
        let q = motion.attitude.quaternion
        let attitude = simd_quatf(ix: Float(q.x), iy: Float(q.y), iz: Float(q.z), r: Float(q.w))

        // World-frame user acceleration in m/s^2.
        let a = motion.userAcceleration
        let acc = SIMD3<Float>(Float(a.x), Float(a.y), Float(a.z)) * 9.80665

        samplesLock.lock()
        if let last = lastSampleTime {
            let dt = Float(max(0, t - last))
            // Trapezoidal integration; this WILL drift, hence we rely on PnP downstream.
            velocity += acc * dt
            position += velocity * dt
        }
        lastSampleTime = t

        samples.append(Sample(time: t, attitude: attitude, translation: position))
        if samples.count > maxSamples {
            samples.removeFirst(samples.count - maxSamples)
        }
        samplesLock.unlock()
    }

    func pose(at time: CMTime) -> Pose? {
        let target = CMTimeGetSeconds(time)
        samplesLock.lock()
        defer { samplesLock.unlock() }
        guard !samples.isEmpty else { return nil }
        // Find the nearest sample by timestamp (binary search would be tighter; linear is fine at 100 Hz).
        var best = samples[0]
        var bestDt = abs(samples[0].time - target)
        for s in samples.dropFirst() {
            let dt = abs(s.time - target)
            if dt < bestDt { best = s; bestDt = dt }
        }
        let R = simd_float3x3(best.attitude)
        var m = matrix_identity_float4x4
        m.columns.0 = SIMD4<Float>(R.columns.0, 0)
        m.columns.1 = SIMD4<Float>(R.columns.1, 0)
        m.columns.2 = SIMD4<Float>(R.columns.2, 0)
        m.columns.3 = SIMD4<Float>(best.translation, 1)
        return Pose(cameraToWorld: m, time: best.time)
    }
}
