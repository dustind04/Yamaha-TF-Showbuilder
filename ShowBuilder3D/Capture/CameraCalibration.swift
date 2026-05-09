import AVFoundation
import simd

/// Helpers for working with `AVCameraCalibrationData` and per-frame intrinsics.
enum CameraCalibration {

    /// Pull the per-frame intrinsic matrix that AVFoundation attaches to a sample buffer
    /// when `isCameraIntrinsicMatrixDeliveryEnabled` is true on the connection.
    static func intrinsics(from sampleBuffer: CMSampleBuffer) -> simd_float3x3? {
        let key = kCMSampleBufferAttachmentKey_CameraIntrinsicMatrix as String
        guard
            let attachments = CMGetAttachment(sampleBuffer, key: key as CFString, attachmentModeOut: nil),
            let data = attachments as? Data
        else { return nil }
        guard data.count == MemoryLayout<simd_float3x3>.size else { return nil }
        var k = simd_float3x3()
        _ = withUnsafeMutableBytes(of: &k) { dst in
            data.copyBytes(to: dst)
        }
        return k
    }

    /// Scale an intrinsic matrix from one image size to another (e.g. when downsampling).
    static func scale(_ k: simd_float3x3, from src: CGSize, to dst: CGSize) -> simd_float3x3 {
        let sx = Float(dst.width / src.width)
        let sy = Float(dst.height / src.height)
        var out = k
        out.columns.0.x *= sx                   // fx
        out.columns.1.y *= sy                   // fy
        out.columns.2.x = (out.columns.2.x + 0.5) * sx - 0.5   // cx
        out.columns.2.y = (out.columns.2.y + 0.5) * sy - 0.5   // cy
        return out
    }
}
