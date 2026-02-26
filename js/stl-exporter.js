/**
 * STL Exporter - Exports Three.js geometry to binary STL format
 * Binary STL is smaller and loads faster in slicers than ASCII STL.
 */

'use strict';

const STLExporter = {
    /**
     * Export a Three.js mesh or geometry to a binary STL ArrayBuffer
     */
    exportBinary(mesh) {
        const geometry = mesh.geometry || mesh;
        const pos = geometry.getAttribute('position');
        const idx = geometry.getIndex();

        const triangleCount = idx ? idx.count / 3 : pos.count / 3;

        // Binary STL format:
        // 80 byte header + 4 byte triangle count + (50 bytes per triangle)
        const bufferLength = 84 + (triangleCount * 50);
        const buffer = new ArrayBuffer(bufferLength);
        const view = new DataView(buffer);

        // Header (80 bytes) - write a descriptive header
        const header = 'Binary STL exported by 3D Parts Generator';
        for (let i = 0; i < 80; i++) {
            view.setUint8(i, i < header.length ? header.charCodeAt(i) : 0);
        }

        // Triangle count
        view.setUint32(80, triangleCount, true);

        let offset = 84;
        const vA = new THREE.Vector3();
        const vB = new THREE.Vector3();
        const vC = new THREE.Vector3();
        const normal = new THREE.Vector3();

        for (let i = 0; i < triangleCount; i++) {
            let a, b, c;
            if (idx) {
                a = idx.getX(i * 3);
                b = idx.getX(i * 3 + 1);
                c = idx.getX(i * 3 + 2);
            } else {
                a = i * 3;
                b = i * 3 + 1;
                c = i * 3 + 2;
            }

            vA.set(pos.getX(a), pos.getY(a), pos.getZ(a));
            vB.set(pos.getX(b), pos.getY(b), pos.getZ(b));
            vC.set(pos.getX(c), pos.getY(c), pos.getZ(c));

            // Compute face normal
            normal.copy(vB).sub(vA).cross(vC.clone().sub(vA)).normalize();

            // Normal
            view.setFloat32(offset, normal.x, true); offset += 4;
            view.setFloat32(offset, normal.y, true); offset += 4;
            view.setFloat32(offset, normal.z, true); offset += 4;

            // Vertex A
            view.setFloat32(offset, vA.x, true); offset += 4;
            view.setFloat32(offset, vA.y, true); offset += 4;
            view.setFloat32(offset, vA.z, true); offset += 4;

            // Vertex B
            view.setFloat32(offset, vB.x, true); offset += 4;
            view.setFloat32(offset, vB.y, true); offset += 4;
            view.setFloat32(offset, vB.z, true); offset += 4;

            // Vertex C
            view.setFloat32(offset, vC.x, true); offset += 4;
            view.setFloat32(offset, vC.y, true); offset += 4;
            view.setFloat32(offset, vC.z, true); offset += 4;

            // Attribute byte count (unused)
            view.setUint16(offset, 0, true); offset += 2;
        }

        return buffer;
    },

    /**
     * Download an STL file
     */
    download(mesh, filename) {
        filename = filename || 'part.stl';
        const buffer = this.exportBinary(mesh);
        const blob = new Blob([buffer], { type: 'application/octet-stream' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
    }
};

window.STLExporter = STLExporter;
