import Foundation
import simd

/// Two-point metric calibration.
///
/// The user picks two distinguishable points on the object (e.g. the centers of two holes)
/// and tells us the real-world distance between them, D. We:
///
///   1) Detect the same two points in all three lens views (manually-confirmed in the wide
///      frame; auto-located in the ultra-wide / telephoto via NCC patch matching).
///   2) Triangulate them with the rig's projection matrices, producing two 3D points P0, P1.
///   3) Compute the scale factor s = D / |P1 - P0|.
///   4) Apply s to every translation (wide-to-lens extrinsics, future motion estimates),
///      establishing a metric world frame anchored at the midpoint of P0, P1.
///
/// In a setup where extrinsics come from `AVCameraCalibrationData` (already metric),
/// step (3) is a sanity check that should yield s ≈ 1.0; deviations indicate the
/// user-specified distance is wrong or the picked points are mismatched across views.
struct CalibrationResult {
    var scale: Double
    var anchorWorldFromWide: simd_double4x4   // moves world origin to mid-point of the two refs
    var pointA: SIMD3<Double>                  // metric world coordinates after rescaling
    var pointB: SIMD3<Double>
    var rmsReprojection: Double                // average reprojection error across views
}

enum CalibrationError: Error {
    case missingViews
    case triangulationFailed
    case nonpositiveDistance
    case extrinsicsUnknown
}

enum Calibration {

    struct ReferenceObservation {
        var lens: CameraFrame.Lens
        var pixel: SIMD2<Double>
    }

    /// Calibrate using the two reference points.
    /// `pointA_obs` and `pointB_obs` must each contain at least two views (lenses) of the
    /// corresponding point. The wide camera view is required for both.
    static func calibrate(rig: CameraRig,
                          pointA_obs: [ReferenceObservation],
                          pointB_obs: [ReferenceObservation],
                          knownDistance: Double) throws -> CalibrationResult {
        guard knownDistance > 0 else { throw CalibrationError.nonpositiveDistance }
        guard pointA_obs.count >= 2, pointB_obs.count >= 2 else { throw CalibrationError.missingViews }

        // World frame at calibration time = the wide camera frame. So world->wide is identity.
        let worldToWide = matrix_identity_double4x4
        var viewsA: [Triangulation.View] = []
        var viewsB: [Triangulation.View] = []
        for obs in pointA_obs {
            guard let P = rig.projection(for: obs.lens, worldToWide: worldToWide) else {
                throw CalibrationError.extrinsicsUnknown
            }
            viewsA.append(.init(projection: P, pixel: obs.pixel))
        }
        for obs in pointB_obs {
            guard let P = rig.projection(for: obs.lens, worldToWide: worldToWide) else {
                throw CalibrationError.extrinsicsUnknown
            }
            viewsB.append(.init(projection: P, pixel: obs.pixel))
        }
        guard let A = Triangulation.triangulate(viewsA) else { throw CalibrationError.triangulationFailed }
        guard let B = Triangulation.triangulate(viewsB) else { throw CalibrationError.triangulationFailed }

        let measured = simd_distance(A.point, B.point)
        guard measured > 1e-9 else { throw CalibrationError.triangulationFailed }
        let scale = knownDistance / measured

        let aMetric = A.point * scale
        let bMetric = B.point * scale
        let mid = (aMetric + bMetric) * 0.5

        // Anchor: translate so mid-point becomes origin; keep wide camera's orientation.
        var anchor = matrix_identity_double4x4
        anchor.columns.3 = SIMD4<Double>(-mid, 1)

        let rms = (A.rms + B.rms) * 0.5
        return CalibrationResult(
            scale: scale,
            anchorWorldFromWide: anchor,
            pointA: aMetric - mid,
            pointB: bMetric - mid,
            rmsReprojection: rms
        )
    }
}
