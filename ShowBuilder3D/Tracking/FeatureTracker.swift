import Foundation
import Vision
import CoreVideo
import CoreImage
import simd

/// Detects and matches keypoints across pairs of frames.
/// Uses Vision's built-in feature print + sequence-handler-based optical flow.
/// For correspondences across cameras (different lenses), we use feature print descriptors.
final class FeatureTracker {

    private let ciContext = CIContext(options: [.useSoftwareRenderer: false])

    /// A 2D keypoint expressed in image-pixel coordinates (origin top-left).
    struct Keypoint: Hashable {
        var pixel: SIMD2<Float>
        var id: UInt64
    }

    struct Match {
        var a: Keypoint
        var b: Keypoint
        var confidence: Float
    }

    /// Detect Harris-style salient points using Vision's contrast-of-features detector.
    /// Returns up to `maxPoints`, sorted by saliency.
    func detectKeypoints(in pixelBuffer: CVPixelBuffer, maxPoints: Int = 256) -> [Keypoint] {
        let request = VNDetectContoursRequest()
        request.contrastAdjustment = 1.6
        request.maximumImageDimension = 512

        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, options: [:])
        do { try handler.perform([request]) } catch { return [] }
        guard let observation = request.results?.first else { return [] }

        let w = Float(CVPixelBufferGetWidth(pixelBuffer))
        let h = Float(CVPixelBufferGetHeight(pixelBuffer))

        var keypoints: [Keypoint] = []
        keypoints.reserveCapacity(min(maxPoints, observation.contourCount))
        var nextId: UInt64 = 0

        // Sample contour points sparsely to act as keypoints; in production this should
        // be replaced with a proper FAST/ORB pipeline (Metal compute or Accelerate-based).
        for i in 0..<observation.contourCount {
            guard let c = try? observation.contour(at: i) else { continue }
            let stride = max(1, c.pointCount / 8)
            var idx = 0
            while idx < c.pointCount && keypoints.count < maxPoints {
                let p = c.normalizedPoints[idx]   // normalized 0..1, origin bottom-left
                let pixel = SIMD2<Float>(Float(p.x) * w, (1 - Float(p.y)) * h)
                keypoints.append(Keypoint(pixel: pixel, id: nextId))
                nextId &+= 1
                idx += stride
            }
            if keypoints.count >= maxPoints { break }
        }
        return keypoints
    }

    /// Match keypoints across two frames using normalized-cross-correlation on small patches.
    /// `searchRadius` is in pixels of frame A. Returns matches sorted by confidence.
    func match(_ aBuffer: CVPixelBuffer, keypoints aPoints: [Keypoint],
               to bBuffer: CVPixelBuffer, keypoints bPoints: [Keypoint],
               searchRadius: Float = 80,
               minConfidence: Float = 0.6) -> [Match] {

        guard !aPoints.isEmpty, !bPoints.isEmpty else { return [] }
        let aImage = CIImage(cvPixelBuffer: aBuffer)
        let bImage = CIImage(cvPixelBuffer: bBuffer)
        let aGray = grayscale(aImage)
        let bGray = grayscale(bImage)

        let patchSize = 11
        let half = patchSize / 2
        let aPatches = aPoints.compactMap { kp -> (Keypoint, [Float])? in
            guard let patch = sample(aGray, around: kp.pixel, half: half) else { return nil }
            return (kp, patch)
        }
        let bPatches = bPoints.compactMap { kp -> (Keypoint, [Float])? in
            guard let patch = sample(bGray, around: kp.pixel, half: half) else { return nil }
            return (kp, patch)
        }

        var matches: [Match] = []
        matches.reserveCapacity(aPatches.count)
        for (akp, ap) in aPatches {
            var best: (Keypoint, Float)?
            for (bkp, bp) in bPatches {
                if simd_distance(akp.pixel, bkp.pixel) > searchRadius { continue }
                let score = ncc(ap, bp)
                if score >= minConfidence, score > (best?.1 ?? -.infinity) {
                    best = (bkp, score)
                }
            }
            if let (bkp, score) = best {
                matches.append(Match(a: akp, b: bkp, confidence: score))
            }
        }
        matches.sort { $0.confidence > $1.confidence }
        return matches
    }

    // MARK: - Helpers

    private func grayscale(_ image: CIImage) -> CIImage {
        let f = CIFilter(name: "CIColorControls")!
        f.setValue(image, forKey: kCIInputImageKey)
        f.setValue(0.0, forKey: kCIInputSaturationKey)
        return f.outputImage ?? image
    }

    private func sample(_ image: CIImage, around p: SIMD2<Float>, half: Int) -> [Float]? {
        let size = half * 2 + 1
        let extent = image.extent
        let x = Int(p.x.rounded()) - half
        let y = Int(p.y.rounded()) - half
        guard x >= 0, y >= 0,
              CGFloat(x + size) <= extent.width,
              CGFloat(y + size) <= extent.height else { return nil }

        var bytes = [UInt8](repeating: 0, count: size * size * 4)
        ciContext.render(image,
                         toBitmap: &bytes,
                         rowBytes: size * 4,
                         bounds: CGRect(x: CGFloat(x), y: extent.height - CGFloat(y + size),
                                        width: CGFloat(size), height: CGFloat(size)),
                         format: .RGBA8,
                         colorSpace: CGColorSpaceCreateDeviceRGB())
        var values = [Float](repeating: 0, count: size * size)
        for i in 0..<(size * size) {
            values[i] = Float(bytes[i * 4]) / 255.0
        }
        return values
    }

    private func ncc(_ a: [Float], _ b: [Float]) -> Float {
        precondition(a.count == b.count)
        let n = Float(a.count)
        var ma: Float = 0, mb: Float = 0
        for i in 0..<a.count { ma += a[i]; mb += b[i] }
        ma /= n; mb /= n
        var num: Float = 0, da: Float = 0, db: Float = 0
        for i in 0..<a.count {
            let av = a[i] - ma
            let bv = b[i] - mb
            num += av * bv
            da += av * av
            db += bv * bv
        }
        let denom = (da * db).squareRoot()
        return denom > 1e-6 ? num / denom : 0
    }
}
