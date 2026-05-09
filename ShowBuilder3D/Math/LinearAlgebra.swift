import Foundation
import simd
import Accelerate

enum LinearAlgebra {

    /// Solve A x = 0 for the unit-norm x using SVD: x is the right-singular vector
    /// associated with the smallest singular value. `a` is row-major, m x n.
    static func nullSpace(_ a: [Double], rows m: Int, cols n: Int) -> [Double]? {
        precondition(a.count == m * n)
        // LAPACK is column-major; transpose into column-major buffer.
        var aCol = [Double](repeating: 0, count: m * n)
        for r in 0..<m {
            for c in 0..<n {
                aCol[c * m + r] = a[r * n + c]
            }
        }

        var jobu: Int8 = 0x4E   // 'N' — don't compute U
        var jobvt: Int8 = 0x41  // 'A' — full V^T
        var mInt = __CLPK_integer(m)
        var nInt = __CLPK_integer(n)
        var lda = __CLPK_integer(m)
        var s = [Double](repeating: 0, count: min(m, n))
        var u = [Double](repeating: 0, count: 1)
        var ldu = __CLPK_integer(1)
        var vt = [Double](repeating: 0, count: n * n)
        var ldvt = __CLPK_integer(n)
        var workQuery = Double(0)
        var lwork = __CLPK_integer(-1)
        var info = __CLPK_integer(0)

        dgesvd_(&jobu, &jobvt, &mInt, &nInt, &aCol, &lda, &s, &u, &ldu,
                &vt, &ldvt, &workQuery, &lwork, &info)
        guard info == 0 else { return nil }
        lwork = __CLPK_integer(workQuery)
        var work = [Double](repeating: 0, count: Int(lwork))
        dgesvd_(&jobu, &jobvt, &mInt, &nInt, &aCol, &lda, &s, &u, &ldu,
                &vt, &ldvt, &work, &lwork, &info)
        guard info == 0 else { return nil }

        // V^T is n x n column-major; we want last row of V^T = last column of V.
        var x = [Double](repeating: 0, count: n)
        for i in 0..<n {
            x[i] = vt[i * n + (n - 1)]
        }
        return x
    }

    /// 4x4 column-major inverse.
    static func invert(_ m: simd_double4x4) -> simd_double4x4 {
        return m.inverse
    }

    /// Convert ARKit / simd float3x3 intrinsics K and a 4x4 extrinsic to a 3x4 projection matrix P = K [R|t].
    /// Extrinsic is world->camera (the convention this app uses internally).
    static func projection(intrinsics K: simd_double3x3, extrinsic Rt: simd_double4x4) -> simd_double4x3 {
        // Extract [R|t] from the 4x4 (top 3 rows).
        let r0 = SIMD3<Double>(Rt.columns.0.x, Rt.columns.0.y, Rt.columns.0.z)
        let r1 = SIMD3<Double>(Rt.columns.1.x, Rt.columns.1.y, Rt.columns.1.z)
        let r2 = SIMD3<Double>(Rt.columns.2.x, Rt.columns.2.y, Rt.columns.2.z)
        let t  = SIMD3<Double>(Rt.columns.3.x, Rt.columns.3.y, Rt.columns.3.z)
        let RT = simd_double3x3(columns: (r0, r1, r2))   // matches Rt's rotation
        let KR = K * RT
        let Kt = K * t
        return simd_double4x3(columns: (
            SIMD3<Double>(KR.columns.0),
            SIMD3<Double>(KR.columns.1),
            SIMD3<Double>(KR.columns.2),
            Kt
        ))
    }

    /// Convert ARKit camera transform (camera-to-world) to world-to-camera extrinsic
    /// using the convention y-down, z-forward.
    /// ARKit convention: camera is +x right, +y up, -z forward (looks down -z).
    /// Computer vision convention: +x right, +y down, +z forward.
    /// Apply T_cv_ar = diag(1, -1, -1, 1) on the left of (camera->world)^-1.
    static func cvExtrinsic(fromARKitCameraToWorld c2w: simd_float4x4) -> simd_double4x4 {
        let c2w_d = simd_double4x4(c2w)
        let w2c = c2w_d.inverse
        var flip = matrix_identity_double4x4
        flip.columns.1.y = -1
        flip.columns.2.z = -1
        return flip * w2c
    }
}

extension simd_double4x4 {
    init(_ m: simd_float4x4) {
        self.init(columns: (
            SIMD4<Double>(m.columns.0),
            SIMD4<Double>(m.columns.1),
            SIMD4<Double>(m.columns.2),
            SIMD4<Double>(m.columns.3)
        ))
    }
}

extension simd_double3x3 {
    init(_ m: simd_float3x3) {
        self.init(columns: (
            SIMD3<Double>(m.columns.0),
            SIMD3<Double>(m.columns.1),
            SIMD3<Double>(m.columns.2)
        ))
    }
}
