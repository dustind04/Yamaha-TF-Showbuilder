import Foundation
import simd

/// Captures the fixed extrinsic geometry between the three rear cameras.
/// On iPhone Pro hardware these positions are factory-calibrated and recoverable
/// either via `AVCameraCalibrationData` (when depth output is enabled) or estimated
/// in software during the user's two-point calibration step.
struct CameraRig {
    /// Per-lens intrinsic matrix in pixels for the resolution we capture at.
    var intrinsics: [CameraFrame.Lens: simd_double3x3]
    /// Per-lens extrinsic: transform that takes a point from the *wide* camera frame
    /// to this lens's camera frame. Wide is the rig's reference frame, so its entry
    /// is the identity.
    var extrinsicFromWide: [CameraFrame.Lens: simd_double4x4]

    static func wideReference() -> simd_double4x4 { matrix_identity_double4x4 }

    /// Build a 3x4 projection P_i for `lens` given a world->wide-camera transform.
    /// World->lens = (wide->lens) * (world->wide), so P = K * (world->lens)[0..3, :].
    func projection(for lens: CameraFrame.Lens, worldToWide: simd_double4x4) -> simd_double4x3? {
        guard let K = intrinsics[lens], let wideToLens = extrinsicFromWide[lens] else { return nil }
        return LinearAlgebra.projection(intrinsics: K, extrinsic: wideToLens * worldToWide)
    }
}
