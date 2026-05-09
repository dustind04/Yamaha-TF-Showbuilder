import Foundation
import simd

/// Direct Linear Transform triangulation from N >= 2 views.
/// Each view provides a 3x4 projection matrix P_i (in pixels) and a 2D pixel observation x_i.
/// We solve the homogeneous system A X = 0 with rows
///     x * P[2] - P[0]
///     y * P[2] - P[1]
/// stacked across views, then take the right-singular vector for the smallest singular value.
enum Triangulation {

    struct View {
        var projection: simd_double4x3
        var pixel: SIMD2<Double>
    }

    /// Returns the 3D point in the world frame implicit in the projection matrices, and the
    /// reprojection RMS error in pixels. Returns nil on degenerate inputs.
    static func triangulate(_ views: [View]) -> (point: SIMD3<Double>, rms: Double)? {
        guard views.count >= 2 else { return nil }
        var rows: [Double] = []
        rows.reserveCapacity(views.count * 2 * 4)
        for v in views {
            let P = v.projection
            let p0 = SIMD4<Double>(P.columns.0.x, P.columns.1.x, P.columns.2.x, P.columns.3.x)
            let p1 = SIMD4<Double>(P.columns.0.y, P.columns.1.y, P.columns.2.y, P.columns.3.y)
            let p2 = SIMD4<Double>(P.columns.0.z, P.columns.1.z, P.columns.2.z, P.columns.3.z)
            let r0 = v.pixel.x * p2 - p0
            let r1 = v.pixel.y * p2 - p1
            rows.append(contentsOf: [r0.x, r0.y, r0.z, r0.w])
            rows.append(contentsOf: [r1.x, r1.y, r1.z, r1.w])
        }
        guard let X = LinearAlgebra.nullSpace(rows, rows: views.count * 2, cols: 4) else { return nil }
        guard abs(X[3]) > 1e-10 else { return nil }
        let X3 = SIMD3<Double>(X[0] / X[3], X[1] / X[3], X[2] / X[3])

        // Reprojection residuals.
        var sumSq = 0.0
        for v in views {
            let P = v.projection
            let xh = SIMD4<Double>(X3, 1)
            let u = simd_dot(SIMD4<Double>(P.columns.0.x, P.columns.1.x, P.columns.2.x, P.columns.3.x), xh)
            let vv = simd_dot(SIMD4<Double>(P.columns.0.y, P.columns.1.y, P.columns.2.y, P.columns.3.y), xh)
            let w = simd_dot(SIMD4<Double>(P.columns.0.z, P.columns.1.z, P.columns.2.z, P.columns.3.z), xh)
            guard abs(w) > 1e-10 else { return nil }
            let dx = u/w - v.pixel.x
            let dy = vv/w - v.pixel.y
            sumSq += dx * dx + dy * dy
        }
        let rms = (sumSq / Double(views.count)).squareRoot()
        return (X3, rms)
    }
}
