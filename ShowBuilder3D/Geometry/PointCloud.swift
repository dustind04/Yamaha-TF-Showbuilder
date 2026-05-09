import Foundation
import simd

/// Thread-safe accumulator of 3D points produced by triangulation.
/// Points are stored in the calibrated metric world frame.
final class PointCloud {

    struct Point {
        var position: SIMD3<Float>
        var color: SIMD3<Float>      // 0..1 sRGB
        var confidence: Float        // ~ inverse of reprojection error in pixels
    }

    private var _points: [Point] = []
    private let lock = NSLock()

    var points: [Point] {
        lock.lock(); defer { lock.unlock() }
        return _points
    }

    var count: Int {
        lock.lock(); defer { lock.unlock() }
        return _points.count
    }

    /// Voxel size (meters) for duplicate suppression.
    var voxelSize: Float = 0.0015
    private var voxelIndex: [SIMD3<Int32>: Int] = [:]

    func add(_ point: Point) {
        lock.lock()
        defer { lock.unlock() }
        let key = voxelKey(point.position)
        if let existing = voxelIndex[key] {
            // Keep the higher-confidence sample.
            if point.confidence > _points[existing].confidence {
                _points[existing] = point
            }
        } else {
            voxelIndex[key] = _points.count
            _points.append(point)
        }
    }

    func add(contentsOf newPoints: [Point]) {
        for p in newPoints { add(p) }
    }

    func clear() {
        lock.lock()
        defer { lock.unlock() }
        _points.removeAll(keepingCapacity: true)
        voxelIndex.removeAll(keepingCapacity: true)
    }

    func snapshot() -> [Point] {
        lock.lock()
        defer { lock.unlock() }
        return _points
    }

    private func voxelKey(_ p: SIMD3<Float>) -> SIMD3<Int32> {
        SIMD3<Int32>(
            Int32((p.x / voxelSize).rounded(.down)),
            Int32((p.y / voxelSize).rounded(.down)),
            Int32((p.z / voxelSize).rounded(.down))
        )
    }
}
