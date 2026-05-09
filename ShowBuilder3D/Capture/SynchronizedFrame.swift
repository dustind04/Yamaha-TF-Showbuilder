import AVFoundation
import CoreVideo
import simd

/// One entry per physical camera in a synchronized frame.
struct CameraFrame {
    enum Lens: String, Hashable, CaseIterable {
        case ultraWide  // 0.5x
        case wide       // 1.0x
        case telephoto  // 2x / 3x depending on model
    }

    let lens: Lens
    let pixelBuffer: CVPixelBuffer
    let presentationTime: CMTime
    /// Per-frame intrinsic matrix, if AVFoundation provided one (it normalizes for cropping/binning).
    /// Units: pixels, with origin at top-left of the pixel buffer.
    let intrinsics: simd_float3x3?
    /// Physical pixel dimensions of `pixelBuffer`.
    let pixelDimensions: CGSize
}

/// A set of frames captured (close to) simultaneously across the available rear cameras,
/// stamped with the ARKit world->camera pose for the wide lens at the time of capture.
struct SynchronizedMultiCamFrame {
    let frames: [CameraFrame.Lens: CameraFrame]
    /// ARKit camera transform (camera-to-world, ARKit convention) at this frame.
    let arCameraTransform: simd_float4x4?
    /// ARKit intrinsics for the wide lens — useful when AVFoundation does not provide them.
    let arIntrinsics: simd_float3x3?
    let captureTimestamp: TimeInterval

    func frame(_ lens: CameraFrame.Lens) -> CameraFrame? { frames[lens] }
}
