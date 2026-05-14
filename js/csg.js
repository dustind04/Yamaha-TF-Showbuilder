/**
 * CSG.js - Constructive Solid Geometry Library
 * Adapted for Three.js r128+
 *
 * Performs boolean operations (union, subtract, intersect) on Three.js meshes.
 * Based on the csg.js algorithm by Evan Wallace.
 */

'use strict';

// ============================================================
// CSG Core
// ============================================================

class CSG {
    constructor() {
        this.polygons = [];
    }

    clone() {
        const csg = new CSG();
        csg.polygons = this.polygons.map(p => p.clone());
        return csg;
    }

    toPolygons() {
        return this.polygons;
    }

    union(csg) {
        const a = new CSGNode(this.clone().polygons);
        const b = new CSGNode(csg.clone().polygons);
        a.clipTo(b);
        b.clipTo(a);
        b.invert();
        b.clipTo(a);
        b.invert();
        a.build(b.allPolygons());
        return CSG.fromPolygons(a.allPolygons());
    }

    subtract(csg) {
        const a = new CSGNode(this.clone().polygons);
        const b = new CSGNode(csg.clone().polygons);
        a.invert();
        a.clipTo(b);
        b.clipTo(a);
        b.invert();
        b.clipTo(a);
        b.invert();
        a.build(b.allPolygons());
        a.invert();
        return CSG.fromPolygons(a.allPolygons());
    }

    intersect(csg) {
        const a = new CSGNode(this.clone().polygons);
        const b = new CSGNode(csg.clone().polygons);
        a.invert();
        b.clipTo(a);
        b.invert();
        a.clipTo(b);
        b.clipTo(a);
        a.build(b.allPolygons());
        a.invert();
        return CSG.fromPolygons(a.allPolygons());
    }

    inverse() {
        const csg = this.clone();
        csg.polygons.forEach(p => p.flip());
        return csg;
    }

    // Convert Three.js geometry to CSG
    static fromGeometry(geom, matrix) {
        let tgeom = geom;
        if (geom.isBufferGeometry) {
            tgeom = geom;
        }

        const pos = tgeom.getAttribute('position');
        const idx = tgeom.getIndex();
        const polygons = [];

        const vertexCount = idx ? idx.count : pos.count;
        for (let i = 0; i < vertexCount; i += 3) {
            const vertices = [];
            for (let j = 0; j < 3; j++) {
                const vi = idx ? idx.getX(i + j) : (i + j);
                const v = new THREE.Vector3(pos.getX(vi), pos.getY(vi), pos.getZ(vi));
                if (matrix) v.applyMatrix4(matrix);
                vertices.push(new CSGVertex(v));
            }
            polygons.push(new CSGPolygon(vertices));
        }

        return CSG.fromPolygons(polygons);
    }

    static fromMesh(mesh) {
        const geom = mesh.geometry.clone();
        if (geom.index === null) {
            // Already non-indexed, fine
        }
        return CSG.fromGeometry(geom, mesh.matrixWorld);
    }

    // Convert CSG back to Three.js BufferGeometry
    toGeometry() {
        const polygons = this.polygons;
        const vertices = [];
        const normals = [];

        for (const polygon of polygons) {
            const verts = polygon.vertices;
            // Triangulate polygon (fan triangulation)
            for (let i = 2; i < verts.length; i++) {
                vertices.push(
                    verts[0].pos.x, verts[0].pos.y, verts[0].pos.z,
                    verts[i - 1].pos.x, verts[i - 1].pos.y, verts[i - 1].pos.z,
                    verts[i].pos.x, verts[i].pos.y, verts[i].pos.z
                );
                const n = polygon.plane.normal;
                normals.push(
                    n.x, n.y, n.z,
                    n.x, n.y, n.z,
                    n.x, n.y, n.z
                );
            }
        }

        const geom = new THREE.BufferGeometry();
        geom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
        geom.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
        return geom;
    }

    toMesh(material) {
        const geom = this.toGeometry();
        return new THREE.Mesh(geom, material);
    }

    static fromPolygons(polygons) {
        const csg = new CSG();
        csg.polygons = polygons;
        return csg;
    }
}

// ============================================================
// Helper: Create CSG from Three.js primitives with transforms
// ============================================================

CSG.fromBox = function(width, height, depth, matrix) {
    const geom = new THREE.BoxGeometry(width, height, depth);
    if (matrix) {
        geom.applyMatrix4(matrix);
    }
    return CSG.fromGeometry(geom);
};

CSG.fromCylinder = function(radiusTop, radiusBottom, height, segments, matrix) {
    segments = segments || 32;
    const geom = new THREE.CylinderGeometry(radiusTop, radiusBottom, height, segments);
    if (matrix) {
        geom.applyMatrix4(matrix);
    }
    return CSG.fromGeometry(geom);
};

CSG.fromSphere = function(radius, widthSegments, heightSegments, matrix) {
    widthSegments = widthSegments || 16;
    heightSegments = heightSegments || 16;
    const geom = new THREE.SphereGeometry(radius, widthSegments, heightSegments);
    if (matrix) {
        geom.applyMatrix4(matrix);
    }
    return CSG.fromGeometry(geom);
};

// ============================================================
// CSG Vertex
// ============================================================

class CSGVertex {
    constructor(pos) {
        this.pos = pos instanceof THREE.Vector3 ? pos : new THREE.Vector3(pos.x, pos.y, pos.z);
    }

    clone() {
        return new CSGVertex(this.pos.clone());
    }

    flip() {
        // Nothing to flip for position-only vertices
    }

    interpolate(other, t) {
        return new CSGVertex(this.pos.clone().lerp(other.pos, t));
    }
}

// ============================================================
// CSG Plane
// ============================================================

const CSG_EPSILON = 1e-5;
const CSG_COPLANAR = 0;
const CSG_FRONT = 1;
const CSG_BACK = 2;
const CSG_SPANNING = 3;

class CSGPlane {
    constructor(normal, w) {
        this.normal = normal;
        this.w = w;
    }

    clone() {
        return new CSGPlane(this.normal.clone(), this.w);
    }

    flip() {
        this.normal.negate();
        this.w = -this.w;
    }

    splitPolygon(polygon, coplanarFront, coplanarBack, front, back) {
        let polygonType = 0;
        const types = [];

        for (const vertex of polygon.vertices) {
            const t = this.normal.dot(vertex.pos) - this.w;
            const type = (t < -CSG_EPSILON) ? CSG_BACK : (t > CSG_EPSILON) ? CSG_FRONT : CSG_COPLANAR;
            polygonType |= type;
            types.push(type);
        }

        switch (polygonType) {
            case CSG_COPLANAR:
                (this.normal.dot(polygon.plane.normal) > 0 ? coplanarFront : coplanarBack).push(polygon);
                break;
            case CSG_FRONT:
                front.push(polygon);
                break;
            case CSG_BACK:
                back.push(polygon);
                break;
            case CSG_SPANNING: {
                const f = [], b = [];
                for (let i = 0; i < polygon.vertices.length; i++) {
                    const j = (i + 1) % polygon.vertices.length;
                    const ti = types[i], tj = types[j];
                    const vi = polygon.vertices[i], vj = polygon.vertices[j];
                    if (ti !== CSG_BACK) f.push(vi);
                    if (ti !== CSG_FRONT) b.push(ti !== CSG_BACK ? vi.clone() : vi);
                    if ((ti | tj) === CSG_SPANNING) {
                        const t = (this.w - this.normal.dot(vi.pos)) / this.normal.dot(vj.pos.clone().sub(vi.pos));
                        const v = vi.interpolate(vj, t);
                        f.push(v);
                        b.push(v.clone());
                    }
                }
                if (f.length >= 3) front.push(new CSGPolygon(f, polygon.shared));
                if (b.length >= 3) back.push(new CSGPolygon(b, polygon.shared));
                break;
            }
        }
    }

    static fromPoints(a, b, c) {
        const n = b.clone().sub(a).cross(c.clone().sub(a)).normalize();
        return new CSGPlane(n, n.dot(a));
    }
}

// ============================================================
// CSG Polygon
// ============================================================

class CSGPolygon {
    constructor(vertices, shared) {
        this.vertices = vertices;
        this.shared = shared;
        this.plane = CSGPlane.fromPoints(vertices[0].pos, vertices[1].pos, vertices[2].pos);
    }

    clone() {
        const verts = this.vertices.map(v => v.clone());
        return new CSGPolygon(verts, this.shared);
    }

    flip() {
        this.vertices.reverse().forEach(v => v.flip());
        this.plane.flip();
    }
}

// ============================================================
// CSG Node (BSP Tree)
// ============================================================

class CSGNode {
    constructor(polygons) {
        this.plane = null;
        this.front = null;
        this.back = null;
        this.polygons = [];
        if (polygons && polygons.length) {
            this.build(polygons);
        }
    }

    clone() {
        const node = new CSGNode();
        node.plane = this.plane && this.plane.clone();
        node.front = this.front && this.front.clone();
        node.back = this.back && this.back.clone();
        node.polygons = this.polygons.map(p => p.clone());
        return node;
    }

    invert() {
        for (const polygon of this.polygons) {
            polygon.flip();
        }
        if (this.plane) this.plane.flip();
        if (this.front) this.front.invert();
        if (this.back) this.back.invert();
        const temp = this.front;
        this.front = this.back;
        this.back = temp;
    }

    clipPolygons(polygons) {
        if (!this.plane) return polygons.slice();
        let front = [], back = [];
        for (const polygon of polygons) {
            this.plane.splitPolygon(polygon, front, back, front, back);
        }
        if (this.front) front = this.front.clipPolygons(front);
        if (this.back) back = this.back.clipPolygons(back);
        else back = [];
        return front.concat(back);
    }

    clipTo(bsp) {
        this.polygons = bsp.clipPolygons(this.polygons);
        if (this.front) this.front.clipTo(bsp);
        if (this.back) this.back.clipTo(bsp);
    }

    allPolygons() {
        let polygons = this.polygons.slice();
        if (this.front) polygons = polygons.concat(this.front.allPolygons());
        if (this.back) polygons = polygons.concat(this.back.allPolygons());
        return polygons;
    }

    build(polygons) {
        if (!polygons.length) return;
        if (!this.plane) this.plane = polygons[0].plane.clone();
        const front = [], back = [];
        for (const polygon of polygons) {
            this.plane.splitPolygon(polygon, this.polygons, this.polygons, front, back);
        }
        if (front.length) {
            if (!this.front) this.front = new CSGNode();
            this.front.build(front);
        }
        if (back.length) {
            if (!this.back) this.back = new CSGNode();
            this.back.build(back);
        }
    }
}

// Make CSG available globally
window.CSG = CSG;
