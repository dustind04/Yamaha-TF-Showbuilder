import Foundation
import simd

/// Binary STL writer.
/// Layout:
///   - 80-byte header (any content; we put our app name)
///   - UInt32 little-endian triangle count
///   - For each triangle:
///       3 floats: normal
///       3 floats: vertex 0
///       3 floats: vertex 1
///       3 floats: vertex 2
///       UInt16: attribute byte count (0)
///
/// All floats are 32-bit IEEE-754 little-endian. Output is in meters; CAD/slicer tools that
/// expect millimeters will need an import-time scale of 1000.
enum STLWriter {

    static func write(triangles: [SurfaceReconstruction.Triangle], to url: URL,
                      header: String = "ShowBuilder3D") throws {
        var data = Data()
        data.reserveCapacity(84 + triangles.count * 50)

        // Header
        var headerBytes = [UInt8](repeating: 0, count: 80)
        let hb = Array(header.utf8.prefix(80))
        for (i, b) in hb.enumerated() { headerBytes[i] = b }
        data.append(contentsOf: headerBytes)

        // Triangle count
        var count = UInt32(triangles.count).littleEndian
        withUnsafeBytes(of: &count) { data.append(contentsOf: $0) }

        for t in triangles {
            appendVector(t.normal, to: &data)
            appendVector(t.v0, to: &data)
            appendVector(t.v1, to: &data)
            appendVector(t.v2, to: &data)
            var attr = UInt16(0).littleEndian
            withUnsafeBytes(of: &attr) { data.append(contentsOf: $0) }
        }

        try data.write(to: url, options: .atomic)
    }

    private static func appendVector(_ v: SIMD3<Float>, to data: inout Data) {
        var x = v.x.bitPattern.littleEndian
        var y = v.y.bitPattern.littleEndian
        var z = v.z.bitPattern.littleEndian
        withUnsafeBytes(of: &x) { data.append(contentsOf: $0) }
        withUnsafeBytes(of: &y) { data.append(contentsOf: $0) }
        withUnsafeBytes(of: &z) { data.append(contentsOf: $0) }
    }
}
