import Foundation
import simd

/// Camera-to-world rigid transform plus the time it was sampled.
/// Convention used throughout the app:
///   Camera frame: +x right, +y down, +z forward (looks down +z).
///   World frame: right-handed, established at calibration time.
struct Pose {
    var cameraToWorld: simd_float4x4
    var time: TimeInterval

    static let identity = Pose(cameraToWorld: matrix_identity_float4x4, time: 0)

    var rotation: simd_float3x3 {
        simd_float3x3(
            SIMD3<Float>(cameraToWorld.columns.0.x, cameraToWorld.columns.0.y, cameraToWorld.columns.0.z),
            SIMD3<Float>(cameraToWorld.columns.1.x, cameraToWorld.columns.1.y, cameraToWorld.columns.1.z),
            SIMD3<Float>(cameraToWorld.columns.2.x, cameraToWorld.columns.2.y, cameraToWorld.columns.2.z)
        )
    }

    var translation: SIMD3<Float> {
        SIMD3<Float>(cameraToWorld.columns.3.x, cameraToWorld.columns.3.y, cameraToWorld.columns.3.z)
    }
}
