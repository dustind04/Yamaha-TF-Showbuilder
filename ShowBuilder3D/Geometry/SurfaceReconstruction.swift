import Foundation
import simd

/// Coarse surface reconstruction strategies.
///
/// `heightField` projects the cloud onto its dominant plane (via PCA), bins points
/// into a regular grid, and stitches a triangle mesh from the populated cells. It
/// produces a watertight 2.5D mesh appropriate for "scan a face / profile" workflows.
///
/// `pointMarkers` emits a small octahedron per point — a fall-back useful for quickly
/// visualizing the cloud in any STL viewer when the surface is too sparse for meshing.
enum SurfaceReconstruction {

    struct Triangle {
        var v0: SIMD3<Float>
        var v1: SIMD3<Float>
        var v2: SIMD3<Float>
        var normal: SIMD3<Float> {
            let n = simd_cross(v1 - v0, v2 - v0)
            let len = simd_length(n)
            return len > 0 ? n / len : SIMD3<Float>(0, 0, 1)
        }
    }

    enum Method {
        case heightField(gridResolution: Int)   // grid cells along the longest in-plane axis
        case pointMarkers(size: Float)          // marker side length in meters
    }

    static func mesh(from cloud: [PointCloud.Point], method: Method) -> [Triangle] {
        switch method {
        case .heightField(let res):
            return heightFieldMesh(cloud, resolution: max(8, res))
        case .pointMarkers(let s):
            return pointMarkerMesh(cloud, size: s)
        }
    }

    // MARK: - Height field

    private static func heightFieldMesh(_ cloud: [PointCloud.Point], resolution: Int) -> [Triangle] {
        guard cloud.count >= 16 else { return [] }

        // 1. Compute centroid and principal axes via PCA on the 3xN data matrix.
        var mean = SIMD3<Float>(repeating: 0)
        for p in cloud { mean += p.position }
        mean /= Float(cloud.count)

        var cxx: Float = 0, cyy: Float = 0, czz: Float = 0
        var cxy: Float = 0, cxz: Float = 0, cyz: Float = 0
        for p in cloud {
            let d = p.position - mean
            cxx += d.x * d.x; cyy += d.y * d.y; czz += d.z * d.z
            cxy += d.x * d.y; cxz += d.x * d.z; cyz += d.y * d.z
        }
        let n = Float(cloud.count)
        let cov = simd_float3x3(rows: [
            SIMD3<Float>(cxx / n, cxy / n, cxz / n),
            SIMD3<Float>(cxy / n, cyy / n, cyz / n),
            SIMD3<Float>(cxz / n, cyz / n, czz / n)
        ])

        let basis = jacobiEigenBasis(cov)   // columns sorted by eigenvalue, descending

        // u, v lie in plane (largest two eigenvalues); w is the normal.
        let u = basis.columns.0
        let v = basis.columns.1
        let w = basis.columns.2

        // 2. Project all points into (u, v, w) coordinates relative to centroid.
        struct Local { var u: Float; var v: Float; var w: Float; var color: SIMD3<Float> }
        var locals: [Local] = []
        locals.reserveCapacity(cloud.count)
        var uMin: Float =  .infinity, uMax: Float = -.infinity
        var vMin: Float =  .infinity, vMax: Float = -.infinity
        for p in cloud {
            let d = p.position - mean
            let lu = simd_dot(d, u)
            let lv = simd_dot(d, v)
            let lw = simd_dot(d, w)
            locals.append(Local(u: lu, v: lv, w: lw, color: p.color))
            uMin = min(uMin, lu); uMax = max(uMax, lu)
            vMin = min(vMin, lv); vMax = max(vMax, lv)
        }
        guard uMax > uMin, vMax > vMin else { return [] }

        // 3. Choose grid sized to keep cells roughly square; resolution = cells along longer axis.
        let extentU = uMax - uMin, extentV = vMax - vMin
        let cols: Int, rows: Int
        if extentU >= extentV {
            cols = resolution
            rows = max(8, Int((Float(resolution) * extentV / extentU).rounded()))
        } else {
            rows = resolution
            cols = max(8, Int((Float(resolution) * extentU / extentV).rounded()))
        }
        let du = extentU / Float(cols - 1)
        let dv = extentV / Float(rows - 1)

        // 4. Fill cells with the median w (height) of contained points.
        var bins: [[[Float]]] = Array(repeating: Array(repeating: [], count: cols), count: rows)
        for l in locals {
            let ci = clamp(Int(((l.u - uMin) / du).rounded()), 0, cols - 1)
            let ri = clamp(Int(((l.v - vMin) / dv).rounded()), 0, rows - 1)
            bins[ri][ci].append(l.w)
        }
        var grid: [[Float?]] = Array(repeating: Array(repeating: nil, count: cols), count: rows)
        for r in 0..<rows {
            for c in 0..<cols {
                if !bins[r][c].isEmpty {
                    let sorted = bins[r][c].sorted()
                    grid[r][c] = sorted[sorted.count / 2]
                }
            }
        }

        // 5. Fill empty cells with bilateral neighborhood mean (a couple of passes).
        for _ in 0..<3 {
            var next = grid
            for r in 0..<rows {
                for c in 0..<cols {
                    if grid[r][c] != nil { continue }
                    var sum: Float = 0; var n: Int = 0
                    for dr in -1...1 {
                        for dc in -1...1 {
                            let nr = r + dr, nc = c + dc
                            if nr >= 0, nr < rows, nc >= 0, nc < cols, let v = grid[nr][nc] {
                                sum += v; n += 1
                            }
                        }
                    }
                    if n > 0 { next[r][c] = sum / Float(n) }
                }
            }
            grid = next
        }

        // 6. Emit triangles for every quad with all four corners populated.
        var tris: [Triangle] = []
        for r in 0..<(rows - 1) {
            for c in 0..<(cols - 1) {
                guard let h00 = grid[r][c], let h10 = grid[r][c + 1],
                      let h01 = grid[r + 1][c], let h11 = grid[r + 1][c + 1] else { continue }
                let p00 = lift(uIdx: c,     vIdx: r,     h: h00, uMin: uMin, vMin: vMin, du: du, dv: dv, mean: mean, u: u, v: v, w: w)
                let p10 = lift(uIdx: c + 1, vIdx: r,     h: h10, uMin: uMin, vMin: vMin, du: du, dv: dv, mean: mean, u: u, v: v, w: w)
                let p01 = lift(uIdx: c,     vIdx: r + 1, h: h01, uMin: uMin, vMin: vMin, du: du, dv: dv, mean: mean, u: u, v: v, w: w)
                let p11 = lift(uIdx: c + 1, vIdx: r + 1, h: h11, uMin: uMin, vMin: vMin, du: du, dv: dv, mean: mean, u: u, v: v, w: w)
                tris.append(Triangle(v0: p00, v1: p10, v2: p11))
                tris.append(Triangle(v0: p00, v1: p11, v2: p01))
            }
        }
        return tris
    }

    private static func lift(uIdx: Int, vIdx: Int, h: Float,
                             uMin: Float, vMin: Float, du: Float, dv: Float,
                             mean: SIMD3<Float>,
                             u: SIMD3<Float>, v: SIMD3<Float>, w: SIMD3<Float>) -> SIMD3<Float> {
        let lu = uMin + Float(uIdx) * du
        let lv = vMin + Float(vIdx) * dv
        return mean + lu * u + lv * v + h * w
    }

    // MARK: - Point markers

    private static func pointMarkerMesh(_ cloud: [PointCloud.Point], size s: Float) -> [Triangle] {
        var tris: [Triangle] = []
        tris.reserveCapacity(cloud.count * 8)
        let h = s * 0.5
        // Octahedron template (6 vertices, 8 faces).
        let template: [SIMD3<Float>] = [
            SIMD3( h, 0, 0), SIMD3(-h, 0, 0),
            SIMD3(0,  h, 0), SIMD3(0, -h, 0),
            SIMD3(0, 0,  h), SIMD3(0, 0, -h)
        ]
        let faces: [(Int, Int, Int)] = [
            (0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
            (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)
        ]
        for p in cloud {
            for (a, b, c) in faces {
                tris.append(Triangle(
                    v0: template[a] + p.position,
                    v1: template[b] + p.position,
                    v2: template[c] + p.position
                ))
            }
        }
        return tris
    }

    // MARK: - PCA helpers

    /// Symmetric 3x3 Jacobi eigendecomposition. Returns a basis whose columns are the
    /// eigenvectors sorted by descending eigenvalue.
    private static func jacobiEigenBasis(_ A: simd_float3x3) -> simd_float3x3 {
        // Work on a row-major 3x3 buffer for legibility.
        var a: [Float] = [
            A.columns.0.x, A.columns.1.x, A.columns.2.x,
            A.columns.0.y, A.columns.1.y, A.columns.2.y,
            A.columns.0.z, A.columns.1.z, A.columns.2.z
        ]
        var v: [Float] = [1, 0, 0,  0, 1, 0,  0, 0, 1]

        @inline(__always) func get(_ m: [Float], _ r: Int, _ c: Int) -> Float { m[r * 3 + c] }
        @inline(__always) func set(_ m: inout [Float], _ r: Int, _ c: Int, _ x: Float) { m[r * 3 + c] = x }

        for _ in 0..<32 {
            // Find the largest absolute off-diagonal entry.
            var p = 0, q = 1
            var maxOff = abs(get(a, 0, 1))
            let off02 = abs(get(a, 0, 2)); if off02 > maxOff { p = 0; q = 2; maxOff = off02 }
            let off12 = abs(get(a, 1, 2)); if off12 > maxOff { p = 1; q = 2; maxOff = off12 }
            if maxOff < 1e-9 { break }

            let app = get(a, p, p)
            let aqq = get(a, q, q)
            let apq = get(a, p, q)
            let theta = (aqq - app) / (2 * apq)
            let t: Float = theta >= 0
                ? 1 / (theta + sqrtf(1 + theta * theta))
                : 1 / (theta - sqrtf(1 + theta * theta))
            let c = 1 / sqrtf(1 + t * t)
            let s = t * c

            // Update A <- R^T A R for the (p,q) Givens rotation.
            for i in 0..<3 {
                let aip = get(a, i, p)
                let aiq = get(a, i, q)
                set(&a, i, p,  c * aip - s * aiq)
                set(&a, i, q,  s * aip + c * aiq)
            }
            for j in 0..<3 {
                let apj = get(a, p, j)
                let aqj = get(a, q, j)
                set(&a, p, j,  c * apj - s * aqj)
                set(&a, q, j,  s * apj + c * aqj)
            }
            // Update V <- V R.
            for i in 0..<3 {
                let vip = get(v, i, p)
                let viq = get(v, i, q)
                set(&v, i, p,  c * vip - s * viq)
                set(&v, i, q,  s * vip + c * viq)
            }
        }

        var pairs: [(Float, SIMD3<Float>)] = [
            (get(a, 0, 0), SIMD3(get(v, 0, 0), get(v, 1, 0), get(v, 2, 0))),
            (get(a, 1, 1), SIMD3(get(v, 0, 1), get(v, 1, 1), get(v, 2, 1))),
            (get(a, 2, 2), SIMD3(get(v, 0, 2), get(v, 1, 2), get(v, 2, 2)))
        ]
        pairs.sort { $0.0 > $1.0 }
        return simd_float3x3(pairs[0].1, pairs[1].1, pairs[2].1)
    }
}

private func clamp<T: Comparable>(_ x: T, _ lo: T, _ hi: T) -> T {
    return min(max(x, lo), hi)
}
