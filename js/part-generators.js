/**
 * Part Generators - Parametric 3D part definitions
 *
 * Each part type defines:
 *   - params: array of parameter definitions (UI inputs)
 *   - generate(values): function returning a CSG object
 */

'use strict';

// Helper: translation matrix
function mat4Translate(x, y, z) {
    return new THREE.Matrix4().makeTranslation(x, y, z);
}

// Helper: rotation matrix (axis, angle in radians)
function mat4RotateX(angle) {
    return new THREE.Matrix4().makeRotationX(angle);
}
function mat4RotateY(angle) {
    return new THREE.Matrix4().makeRotationY(angle);
}
function mat4RotateZ(angle) {
    return new THREE.Matrix4().makeRotationZ(angle);
}

// Helper: combined transform
function mat4(tx, ty, tz, rx, ry, rz) {
    const m = new THREE.Matrix4();
    if (rx) m.multiply(mat4RotateX(rx));
    if (ry) m.multiply(mat4RotateY(ry));
    if (rz) m.multiply(mat4RotateZ(rz));
    m.setPosition(tx || 0, ty || 0, tz || 0);
    return m;
}

// Helper: create a cylinder hole (for bolt holes)
function boltHole(diameter, depth, x, y, z, rotX) {
    const r = diameter / 2;
    const m = new THREE.Matrix4();
    if (rotX !== undefined) m.multiply(mat4RotateX(rotX));
    m.setPosition(x || 0, y || 0, z || 0);
    return CSG.fromCylinder(r, r, depth, 24, m);
}

// Helper: countersink around a hole
function countersink(holeDiameter, csinkDiameter, csinkDepth, x, y, z, rotX) {
    const m = new THREE.Matrix4();
    if (rotX !== undefined) m.multiply(mat4RotateX(rotX));
    m.setPosition(x || 0, y || 0, z || 0);
    return CSG.fromCylinder(csinkDiameter / 2, holeDiameter / 2, csinkDepth, 24, m);
}

// Helper: fillet-like chamfer on edges (simplified as a box subtraction at 45 degrees)
function roundedBoxCSG(width, height, depth, radius) {
    // For simplicity we use a plain box; true fillets would need more geometry
    return CSG.fromBox(width, height, depth);
}

// ============================================================
// PART DEFINITIONS
// ============================================================

const PartGenerators = {

    // --------------------------------------------------------
    // L-BRACKET
    // --------------------------------------------------------
    'l-bracket': {
        name: 'L-Bracket',
        params: [
            { group: 'Dimensions', items: [
                { id: 'width', label: 'Width', default: 40, min: 5, max: 300 },
                { id: 'legA', label: 'Leg A Length', default: 30, min: 5, max: 300 },
                { id: 'legB', label: 'Leg B Length', default: 30, min: 5, max: 300 },
                { id: 'thickness', label: 'Thickness', default: 3, min: 1, max: 20 },
            ]},
            { group: 'Holes', items: [
                { id: 'holeDia', label: 'Hole Diameter', default: 4, min: 0, max: 20 },
                { id: 'holesA', label: 'Holes on Leg A', default: 1, min: 0, max: 5, step: 1 },
                { id: 'holesB', label: 'Holes on Leg B', default: 1, min: 0, max: 5, step: 1 },
            ]},
            { group: 'Options', items: [
                { id: 'gusset', label: 'Add Gusset', type: 'checkbox', default: true },
                { id: 'gussetSize', label: 'Gusset Size', default: 10, min: 0, max: 50 },
            ]},
        ],
        generate(v) {
            const t = v.thickness;
            // Leg A: horizontal
            let part = CSG.fromBox(v.width, t, v.legA, mat4Translate(0, t / 2, v.legA / 2));
            // Leg B: vertical
            part = part.union(CSG.fromBox(v.width, v.legB, t, mat4Translate(0, v.legB / 2, t / 2)));

            // Gusset (triangle support)
            if (v.gusset && v.gussetSize > 0) {
                const gs = Math.min(v.gussetSize, v.legA - t, v.legB - t);
                if (gs > 1) {
                    // Create a triangular gusset using a box and subtract a diagonal
                    const gussetBlock = CSG.fromBox(v.width, gs, gs,
                        mat4Translate(0, t + gs / 2, t + gs / 2));
                    // Diagonal cut: large box rotated 45 degrees
                    const cutSize = gs * 2;
                    const cutM = new THREE.Matrix4()
                        .makeRotationX(Math.PI / 4)
                        .setPosition(0, t + gs + gs * 0.2, t + gs + gs * 0.2);
                    const cutBox = CSG.fromBox(v.width + 2, cutSize, cutSize, cutM);
                    const gusset = gussetBlock.subtract(cutBox);
                    part = part.union(gusset);
                }
            }

            // Holes on Leg A (top face, into Z direction)
            if (v.holeDia > 0 && v.holesA > 0) {
                const spacing = v.legA - t;
                for (let i = 0; i < v.holesA; i++) {
                    const zPos = t + spacing * (i + 1) / (v.holesA + 1);
                    part = part.subtract(boltHole(v.holeDia, t + 2, 0, t / 2, zPos));
                }
            }

            // Holes on Leg B (front face, into Y direction)
            if (v.holeDia > 0 && v.holesB > 0) {
                const spacing = v.legB - t;
                for (let i = 0; i < v.holesB; i++) {
                    const yPos = t + spacing * (i + 1) / (v.holesB + 1);
                    part = part.subtract(boltHole(v.holeDia, t + 2, 0, yPos, t / 2, Math.PI / 2));
                }
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // U-BRACKET
    // --------------------------------------------------------
    'u-bracket': {
        name: 'U-Bracket',
        params: [
            { group: 'Dimensions', items: [
                { id: 'width', label: 'Width', default: 40, min: 5, max: 300 },
                { id: 'innerWidth', label: 'Channel Width', default: 20, min: 2, max: 200 },
                { id: 'legHeight', label: 'Leg Height', default: 25, min: 5, max: 200 },
                { id: 'thickness', label: 'Thickness', default: 3, min: 1, max: 20 },
            ]},
            { group: 'Holes', items: [
                { id: 'holeDia', label: 'Hole Diameter', default: 4, min: 0, max: 20 },
                { id: 'baseHoles', label: 'Base Holes', default: 1, min: 0, max: 5, step: 1 },
                { id: 'legHoles', label: 'Leg Holes', default: 1, min: 0, max: 5, step: 1 },
            ]},
        ],
        generate(v) {
            const t = v.thickness;
            const totalWidth = v.innerWidth + 2 * t;
            // Base
            let part = CSG.fromBox(v.width, t, totalWidth, mat4Translate(0, t / 2, 0));
            // Left leg
            part = part.union(CSG.fromBox(v.width, v.legHeight, t,
                mat4Translate(0, t + v.legHeight / 2, -(v.innerWidth / 2 + t / 2))));
            // Right leg
            part = part.union(CSG.fromBox(v.width, v.legHeight, t,
                mat4Translate(0, t + v.legHeight / 2, v.innerWidth / 2 + t / 2)));

            // Base holes
            if (v.holeDia > 0 && v.baseHoles > 0) {
                for (let i = 0; i < v.baseHoles; i++) {
                    const xPos = v.width * (i + 1) / (v.baseHoles + 1) - v.width / 2;
                    part = part.subtract(boltHole(v.holeDia, t + 2, xPos, t / 2, 0));
                }
            }

            // Leg holes
            if (v.holeDia > 0 && v.legHoles > 0) {
                for (let i = 0; i < v.legHoles; i++) {
                    const yPos = t + v.legHeight * (i + 1) / (v.legHoles + 1);
                    // Left leg holes
                    part = part.subtract(boltHole(v.holeDia, t + 2,
                        0, yPos, -(v.innerWidth / 2 + t / 2), Math.PI / 2));
                    // Right leg holes
                    part = part.subtract(boltHole(v.holeDia, t + 2,
                        0, yPos, v.innerWidth / 2 + t / 2, Math.PI / 2));
                }
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // FLAT BRACKET
    // --------------------------------------------------------
    'flat-bracket': {
        name: 'Flat Bracket',
        params: [
            { group: 'Dimensions', items: [
                { id: 'width', label: 'Width', default: 60, min: 10, max: 300 },
                { id: 'height', label: 'Height', default: 25, min: 5, max: 200 },
                { id: 'thickness', label: 'Thickness', default: 3, min: 1, max: 20 },
            ]},
            { group: 'Holes', items: [
                { id: 'holeDia', label: 'Hole Diameter', default: 4, min: 0, max: 20 },
                { id: 'holeCount', label: 'Number of Holes', default: 2, min: 0, max: 10, step: 1 },
            ]},
        ],
        generate(v) {
            let part = CSG.fromBox(v.width, v.height, v.thickness);

            if (v.holeDia > 0 && v.holeCount > 0) {
                for (let i = 0; i < v.holeCount; i++) {
                    const xPos = v.width * (i + 1) / (v.holeCount + 1) - v.width / 2;
                    part = part.subtract(boltHole(v.holeDia, v.thickness + 2,
                        xPos, 0, 0, Math.PI / 2));
                }
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // WALL MOUNT
    // --------------------------------------------------------
    'wall-mount': {
        name: 'Wall Mount',
        params: [
            { group: 'Base Plate', items: [
                { id: 'plateWidth', label: 'Plate Width', default: 50, min: 10, max: 300 },
                { id: 'plateHeight', label: 'Plate Height', default: 60, min: 10, max: 300 },
                { id: 'plateThick', label: 'Plate Thickness', default: 4, min: 1, max: 20 },
            ]},
            { group: 'Hook/Shelf', items: [
                { id: 'shelfDepth', label: 'Shelf Depth', default: 30, min: 5, max: 200 },
                { id: 'shelfThick', label: 'Shelf Thickness', default: 4, min: 1, max: 20 },
                { id: 'lipHeight', label: 'Front Lip', default: 5, min: 0, max: 50 },
            ]},
            { group: 'Mounting', items: [
                { id: 'holeDia', label: 'Screw Hole Dia', default: 4, min: 0, max: 12 },
                { id: 'holeCount', label: 'Screw Holes', default: 2, min: 1, max: 6, step: 1 },
            ]},
        ],
        generate(v) {
            // Back plate
            let part = CSG.fromBox(v.plateWidth, v.plateHeight, v.plateThick,
                mat4Translate(0, v.plateHeight / 2, v.plateThick / 2));

            // Shelf
            part = part.union(CSG.fromBox(v.plateWidth, v.shelfThick, v.shelfDepth,
                mat4Translate(0, v.shelfThick / 2, v.plateThick + v.shelfDepth / 2)));

            // Gussets (triangular supports under shelf)
            const gussetSize = Math.min(v.shelfDepth * 0.6, v.plateHeight * 0.4);
            if (gussetSize > 3) {
                const gBlock = CSG.fromBox(v.plateWidth * 0.15, gussetSize, gussetSize,
                    mat4Translate(0, v.shelfThick + gussetSize / 2, v.plateThick + gussetSize / 2));
                const cutM = new THREE.Matrix4()
                    .makeRotationX(Math.PI / 4)
                    .setPosition(0, v.shelfThick + gussetSize * 1.2, v.plateThick + gussetSize * 1.2);
                const gCut = CSG.fromBox(v.plateWidth + 2, gussetSize * 2, gussetSize * 2, cutM);
                const gusset = gBlock.subtract(gCut);
                part = part.union(gusset);
            }

            // Front lip
            if (v.lipHeight > 0) {
                part = part.union(CSG.fromBox(v.plateWidth, v.lipHeight, v.shelfThick,
                    mat4Translate(0, v.lipHeight / 2, v.plateThick + v.shelfDepth + v.shelfThick / 2)));
            }

            // Mounting holes
            if (v.holeDia > 0) {
                for (let i = 0; i < v.holeCount; i++) {
                    const yPos = v.plateHeight * (i + 1) / (v.holeCount + 1);
                    part = part.subtract(boltHole(v.holeDia, v.plateThick + 2,
                        0, yPos, v.plateThick / 2, Math.PI / 2));
                }
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // SHELF BRACKET
    // --------------------------------------------------------
    'shelf-bracket': {
        name: 'Shelf Bracket',
        params: [
            { group: 'Dimensions', items: [
                { id: 'depth', label: 'Depth (horizontal)', default: 60, min: 10, max: 300 },
                { id: 'height', label: 'Height (vertical)', default: 80, min: 10, max: 300 },
                { id: 'width', label: 'Width (thickness)', default: 20, min: 5, max: 100 },
                { id: 'thickness', label: 'Material Thickness', default: 4, min: 1, max: 20 },
            ]},
            { group: 'Holes', items: [
                { id: 'holeDia', label: 'Hole Diameter', default: 5, min: 0, max: 15 },
                { id: 'wallHoles', label: 'Wall Holes', default: 2, min: 0, max: 4, step: 1 },
            ]},
        ],
        generate(v) {
            const t = v.thickness;
            // Vertical plate (wall side)
            let part = CSG.fromBox(v.width, v.height, t,
                mat4Translate(0, v.height / 2, t / 2));

            // Horizontal plate (shelf side)
            part = part.union(CSG.fromBox(v.width, t, v.depth,
                mat4Translate(0, t / 2, v.depth / 2)));

            // Diagonal brace
            const diagLen = Math.sqrt(v.height * v.height + v.depth * v.depth);
            const angle = Math.atan2(v.height, v.depth);
            const diagGeom = new THREE.BoxGeometry(v.width, t, diagLen);
            const diagMatrix = new THREE.Matrix4()
                .makeRotationX(angle)
                .setPosition(0, v.height / 2, v.depth / 2);
            const diagCSG = CSG.fromGeometry(diagGeom, diagMatrix);
            part = part.union(diagCSG);

            // Wall holes
            if (v.holeDia > 0 && v.wallHoles > 0) {
                for (let i = 0; i < v.wallHoles; i++) {
                    const yPos = v.height * (i + 1) / (v.wallHoles + 1);
                    part = part.subtract(boltHole(v.holeDia, t + 2,
                        0, yPos, t / 2, Math.PI / 2));
                }
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // CABLE ORGANIZER
    // --------------------------------------------------------
    'cable-organizer': {
        name: 'Cable Organizer',
        params: [
            { group: 'Dimensions', items: [
                { id: 'slotCount', label: 'Number of Slots', default: 4, min: 1, max: 12, step: 1 },
                { id: 'slotDia', label: 'Slot Diameter', default: 8, min: 2, max: 40 },
                { id: 'depth', label: 'Depth', default: 15, min: 5, max: 60 },
                { id: 'thickness', label: 'Wall Thickness', default: 2.5, min: 1, max: 10 },
            ]},
            { group: 'Mounting', items: [
                { id: 'mountType', label: 'Mount', type: 'select',
                    options: ['screw', 'adhesive', 'none'], default: 'screw' },
                { id: 'holeDia', label: 'Screw Hole Dia', default: 4, min: 2, max: 8 },
            ]},
        ],
        generate(v) {
            const t = v.thickness;
            const slotR = v.slotDia / 2;
            const pitch = v.slotDia + t * 2;
            const totalWidth = v.slotCount * pitch + t;
            const bodyHeight = slotR + t * 2;
            const slotEntry = slotR * 0.7; // Opening width

            // Main body
            let part = CSG.fromBox(totalWidth, bodyHeight, v.depth,
                mat4Translate(0, bodyHeight / 2, 0));

            // Cut slots
            for (let i = 0; i < v.slotCount; i++) {
                const cx = -totalWidth / 2 + t + slotR + i * pitch;
                const cy = bodyHeight - slotR - t + t;

                // Round slot
                const slotM = mat4RotateX(Math.PI / 2);
                slotM.setPosition(cx, cy, 0);
                part = part.subtract(CSG.fromCylinder(slotR, slotR, v.depth + 2, 24, slotM));

                // Entry slit from top
                part = part.subtract(CSG.fromBox(slotEntry, t + slotR, v.depth + 2,
                    mat4Translate(cx, bodyHeight - (t + slotR) / 2 + 0.5, 0)));
            }

            // Mounting flange
            if (v.mountType === 'screw') {
                const flangeH = t + v.holeDia + t;
                const flange = CSG.fromBox(totalWidth, flangeH, t,
                    mat4Translate(0, bodyHeight + flangeH / 2, -v.depth / 2 + t / 2));
                part = part.union(flange);

                // Screw holes
                const hx1 = -totalWidth / 3;
                const hx2 = totalWidth / 3;
                const hy = bodyHeight + flangeH / 2;
                part = part.subtract(boltHole(v.holeDia, t + 2, hx1, hy, -v.depth / 2 + t / 2, Math.PI / 2));
                part = part.subtract(boltHole(v.holeDia, t + 2, hx2, hy, -v.depth / 2 + t / 2, Math.PI / 2));
            } else if (v.mountType === 'adhesive') {
                // Flat back for adhesive
                const flangeH = 8;
                const flange = CSG.fromBox(totalWidth, flangeH, t / 2,
                    mat4Translate(0, bodyHeight + flangeH / 2, -v.depth / 2 + t / 4));
                part = part.union(flange);
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // GRID ORGANIZER
    // --------------------------------------------------------
    'grid-organizer': {
        name: 'Grid Organizer',
        params: [
            { group: 'Grid', items: [
                { id: 'cols', label: 'Columns', default: 3, min: 1, max: 10, step: 1 },
                { id: 'rows', label: 'Rows', default: 2, min: 1, max: 10, step: 1 },
                { id: 'cellWidth', label: 'Cell Width', default: 30, min: 10, max: 100 },
                { id: 'cellDepth', label: 'Cell Depth', default: 30, min: 10, max: 100 },
                { id: 'cellHeight', label: 'Cell Height', default: 25, min: 5, max: 100 },
            ]},
            { group: 'Construction', items: [
                { id: 'wallThick', label: 'Wall Thickness', default: 2, min: 0.8, max: 5 },
                { id: 'bottomThick', label: 'Bottom Thickness', default: 1.5, min: 0.6, max: 5 },
            ]},
        ],
        generate(v) {
            const wt = v.wallThick;
            const totalW = v.cols * v.cellWidth + (v.cols + 1) * wt;
            const totalD = v.rows * v.cellDepth + (v.rows + 1) * wt;
            const totalH = v.cellHeight + v.bottomThick;

            // Outer shell
            let part = CSG.fromBox(totalW, totalH, totalD,
                mat4Translate(0, totalH / 2, 0));

            // Hollow out cells
            for (let c = 0; c < v.cols; c++) {
                for (let r = 0; r < v.rows; r++) {
                    const cx = -totalW / 2 + wt + v.cellWidth / 2 + c * (v.cellWidth + wt);
                    const cz = -totalD / 2 + wt + v.cellDepth / 2 + r * (v.cellDepth + wt);
                    const cy = v.bottomThick + v.cellHeight / 2 + 0.5;
                    part = part.subtract(CSG.fromBox(v.cellWidth, v.cellHeight + 1, v.cellDepth,
                        mat4Translate(cx, cy, cz)));
                }
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // PHONE/TABLET STAND
    // --------------------------------------------------------
    'phone-stand': {
        name: 'Phone/Tablet Stand',
        params: [
            { group: 'Device', items: [
                { id: 'deviceWidth', label: 'Device Width', default: 75, min: 30, max: 300 },
                { id: 'deviceThick', label: 'Device Thickness', default: 10, min: 4, max: 20 },
            ]},
            { group: 'Stand', items: [
                { id: 'baseDepth', label: 'Base Depth', default: 60, min: 20, max: 150 },
                { id: 'backHeight', label: 'Back Height', default: 40, min: 15, max: 150 },
                { id: 'angle', label: 'Tilt Angle', default: 70, min: 30, max: 85 },
                { id: 'thickness', label: 'Thickness', default: 4, min: 2, max: 10 },
                { id: 'lipHeight', label: 'Front Lip', default: 8, min: 3, max: 30 },
            ]},
            { group: 'Options', items: [
                { id: 'cableSlot', label: 'Cable Slot', type: 'checkbox', default: true },
                { id: 'cableWidth', label: 'Cable Slot Width', default: 15, min: 5, max: 30 },
            ]},
        ],
        generate(v) {
            const t = v.thickness;
            const standW = v.deviceWidth + t * 2;
            const angleRad = v.angle * Math.PI / 180;

            // Base plate
            let part = CSG.fromBox(standW, t, v.baseDepth,
                mat4Translate(0, t / 2, v.baseDepth / 2));

            // Front lip
            part = part.union(CSG.fromBox(standW, v.lipHeight, t,
                mat4Translate(0, v.lipHeight / 2, t / 2)));

            // Back support (angled)
            const backH = v.backHeight;
            const backGeom = new THREE.BoxGeometry(standW, backH, t);
            const backM = new THREE.Matrix4()
                .makeRotationX(Math.PI / 2 - angleRad)
                .setPosition(0, backH / 2 * Math.sin(angleRad),
                    v.baseDepth - backH / 2 * Math.cos(angleRad));
            const backCSG = CSG.fromGeometry(backGeom, backM);
            part = part.union(backCSG);

            // Device slot groove
            const slotW = v.deviceThick + 1; // slight tolerance
            part = part.subtract(CSG.fromBox(v.deviceWidth, v.lipHeight + 2, slotW,
                mat4Translate(0, t + v.lipHeight / 2, slotW / 2 + t)));

            // Cable slot
            if (v.cableSlot) {
                part = part.subtract(CSG.fromBox(v.cableWidth, t + 2, t + 2,
                    mat4Translate(0, t / 2, t + slotW / 2)));
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // ENCLOSURE / BOX
    // --------------------------------------------------------
    'enclosure': {
        name: 'Box / Enclosure',
        params: [
            { group: 'Outer Dimensions', items: [
                { id: 'innerWidth', label: 'Inner Width', default: 60, min: 10, max: 300 },
                { id: 'innerDepth', label: 'Inner Depth', default: 40, min: 10, max: 300 },
                { id: 'innerHeight', label: 'Inner Height', default: 25, min: 5, max: 200 },
                { id: 'wallThick', label: 'Wall Thickness', default: 2.5, min: 0.8, max: 10 },
                { id: 'bottomThick', label: 'Bottom Thickness', default: 2, min: 0.6, max: 10 },
            ]},
            { group: 'Lid', items: [
                { id: 'lid', label: 'Include Lid', type: 'checkbox', default: true },
                { id: 'lidThick', label: 'Lid Thickness', default: 2, min: 0.6, max: 10 },
                { id: 'lidLip', label: 'Lid Lip Depth', default: 3, min: 0, max: 15 },
            ]},
            { group: 'Options', items: [
                { id: 'screwPosts', label: 'Screw Posts', type: 'checkbox', default: true },
                { id: 'screwDia', label: 'Screw Diameter', default: 3, min: 1, max: 6 },
            ]},
        ],
        generate(v) {
            const wt = v.wallThick;
            const bt = v.bottomThick;
            const ow = v.innerWidth + wt * 2;
            const od = v.innerDepth + wt * 2;
            const oh = v.innerHeight + bt;
            const tol = 0.2;

            // Box outer shell
            let box = CSG.fromBox(ow, oh, od, mat4Translate(0, oh / 2, 0));
            // Hollow inside
            box = box.subtract(CSG.fromBox(v.innerWidth, v.innerHeight + 1, v.innerDepth,
                mat4Translate(0, bt + v.innerHeight / 2 + 0.5, 0)));

            // Screw posts in corners
            if (v.screwPosts) {
                const postR = v.screwDia + wt;
                const corners = [
                    [v.innerWidth / 2 - postR / 2, v.innerDepth / 2 - postR / 2],
                    [-v.innerWidth / 2 + postR / 2, v.innerDepth / 2 - postR / 2],
                    [v.innerWidth / 2 - postR / 2, -v.innerDepth / 2 + postR / 2],
                    [-v.innerWidth / 2 + postR / 2, -v.innerDepth / 2 + postR / 2],
                ];
                for (const [cx, cz] of corners) {
                    const post = CSG.fromCylinder(postR, postR, v.innerHeight, 16,
                        mat4Translate(cx, bt + v.innerHeight / 2, cz));
                    const hole = CSG.fromCylinder(v.screwDia / 2, v.screwDia / 2, v.innerHeight + 2, 16,
                        mat4Translate(cx, bt + v.innerHeight / 2, cz));
                    box = box.union(post).subtract(hole);
                }
            }

            // Lid (separate piece, positioned above)
            if (v.lid) {
                const lidW = ow;
                const lidD = od;
                let lid = CSG.fromBox(lidW, v.lidThick, lidD,
                    mat4Translate(0, oh + 2 + v.lidThick / 2, 0));

                // Lip that fits inside the box
                if (v.lidLip > 0) {
                    const lipW = v.innerWidth - tol * 2;
                    const lipD = v.innerDepth - tol * 2;
                    let lip = CSG.fromBox(lipW, v.lidLip, lipD,
                        mat4Translate(0, oh + 2 - v.lidLip / 2, 0));
                    const lipInner = CSG.fromBox(lipW - wt * 2, v.lidLip + 1, lipD - wt * 2,
                        mat4Translate(0, oh + 2 - v.lidLip / 2, 0));
                    lip = lip.subtract(lipInner);
                    lid = lid.union(lip);
                }

                // Screw holes in lid
                if (v.screwPosts) {
                    const postR = v.screwDia + wt;
                    const corners = [
                        [v.innerWidth / 2 - postR / 2, v.innerDepth / 2 - postR / 2],
                        [-v.innerWidth / 2 + postR / 2, v.innerDepth / 2 - postR / 2],
                        [v.innerWidth / 2 - postR / 2, -v.innerDepth / 2 + postR / 2],
                        [-v.innerWidth / 2 + postR / 2, -v.innerDepth / 2 + postR / 2],
                    ];
                    for (const [cx, cz] of corners) {
                        lid = lid.subtract(boltHole(v.screwDia + 0.5, v.lidThick + 2,
                            cx, oh + 2 + v.lidThick / 2, cz));
                    }
                }

                box = box.union(lid);
            }

            return box;
        }
    },

    // --------------------------------------------------------
    // PIPE / ROD CLAMP
    // --------------------------------------------------------
    'pipe-clamp': {
        name: 'Pipe/Rod Clamp',
        params: [
            { group: 'Pipe', items: [
                { id: 'pipeDia', label: 'Pipe Diameter', default: 25, min: 3, max: 100 },
                { id: 'clampWidth', label: 'Clamp Width', default: 20, min: 5, max: 100 },
            ]},
            { group: 'Construction', items: [
                { id: 'wallThick', label: 'Wall Thickness', default: 3, min: 1.5, max: 15 },
                { id: 'boltDia', label: 'Bolt Diameter', default: 4, min: 2, max: 10 },
                { id: 'split', label: 'Split Clamp', type: 'checkbox', default: true },
            ]},
            { group: 'Mounting', items: [
                { id: 'mountTab', label: 'Mount Tab', type: 'checkbox', default: true },
                { id: 'tabWidth', label: 'Tab Width', default: 20, min: 5, max: 60 },
                { id: 'mountHoleDia', label: 'Mount Hole Dia', default: 4, min: 0, max: 10 },
            ]},
        ],
        generate(v) {
            const pipeR = v.pipeDia / 2;
            const outerR = pipeR + v.wallThick;
            const w = v.clampWidth;

            // Outer cylinder
            const outerM = mat4RotateX(Math.PI / 2);
            outerM.setPosition(0, outerR, 0);
            let part = CSG.fromCylinder(outerR, outerR, w, 32, outerM);

            // Inner bore
            const innerM = mat4RotateX(Math.PI / 2);
            innerM.setPosition(0, outerR, 0);
            part = part.subtract(CSG.fromCylinder(pipeR, pipeR, w + 2, 32, innerM));

            // Bolt ears/flanges
            if (v.split) {
                const earH = v.wallThick + v.boltDia + v.wallThick;
                const earW = w;

                // Right ear
                part = part.union(CSG.fromBox(earH, v.wallThick, earW,
                    mat4Translate(outerR + earH / 2, outerR + pipeR + v.wallThick / 2, 0)));
                // Left ear
                part = part.union(CSG.fromBox(earH, v.wallThick, earW,
                    mat4Translate(-(outerR + earH / 2), outerR + pipeR + v.wallThick / 2, 0)));

                // Bolt holes in ears
                const boltY = outerR + pipeR + v.wallThick / 2;
                part = part.subtract(boltHole(v.boltDia, earW + 2,
                    outerR + earH / 2, boltY, 0, Math.PI / 2));
                part = part.subtract(boltHole(v.boltDia, earW + 2,
                    -(outerR + earH / 2), boltY, 0, Math.PI / 2));

                // Split cut
                part = part.subtract(CSG.fromBox(0.5, pipeR + v.wallThick + earH, w + 2,
                    mat4Translate(0, outerR + (pipeR + v.wallThick) / 2, 0)));
            }

            // Mount tab
            if (v.mountTab) {
                const tabH = outerR;
                const tabThick = v.wallThick;
                part = part.union(CSG.fromBox(v.tabWidth, tabThick, tabH,
                    mat4Translate(0, -tabThick / 2, -tabH / 2)));

                if (v.mountHoleDia > 0) {
                    part = part.subtract(boltHole(v.mountHoleDia, tabThick + 2,
                        0, -tabThick / 2, -tabH / 2));
                }
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // ADAPTER RING
    // --------------------------------------------------------
    'adapter-ring': {
        name: 'Adapter Ring',
        params: [
            { group: 'Diameters', items: [
                { id: 'outerDia', label: 'Outer Diameter', default: 40, min: 5, max: 200 },
                { id: 'innerDia', label: 'Inner Diameter', default: 25, min: 2, max: 195 },
            ]},
            { group: 'Dimensions', items: [
                { id: 'height', label: 'Height', default: 10, min: 1, max: 100 },
                { id: 'tapered', label: 'Tapered', type: 'checkbox', default: false },
            ]},
        ],
        generate(v) {
            const outerR = v.outerDia / 2;
            const innerR = v.innerDia / 2;

            let part;
            if (v.tapered) {
                part = CSG.fromCylinder(outerR, innerR + (outerR - innerR) * 0.2, v.height, 32,
                    mat4Translate(0, v.height / 2, 0));
                part = part.subtract(CSG.fromCylinder(innerR, outerR * 0.8, v.height + 2, 32,
                    mat4Translate(0, v.height / 2, 0)));
            } else {
                part = CSG.fromCylinder(outerR, outerR, v.height, 32,
                    mat4Translate(0, v.height / 2, 0));
                part = part.subtract(CSG.fromCylinder(innerR, innerR, v.height + 2, 32,
                    mat4Translate(0, v.height / 2, 0)));
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // SPACER / WASHER
    // --------------------------------------------------------
    'spacer': {
        name: 'Spacer / Washer',
        params: [
            { group: 'Dimensions', items: [
                { id: 'outerDia', label: 'Outer Diameter', default: 16, min: 3, max: 100 },
                { id: 'innerDia', label: 'Hole Diameter', default: 5, min: 1, max: 95 },
                { id: 'height', label: 'Height', default: 3, min: 0.4, max: 50 },
            ]},
        ],
        generate(v) {
            let part = CSG.fromCylinder(v.outerDia / 2, v.outerDia / 2, v.height, 32,
                mat4Translate(0, v.height / 2, 0));
            part = part.subtract(CSG.fromCylinder(v.innerDia / 2, v.innerDia / 2, v.height + 2, 32,
                mat4Translate(0, v.height / 2, 0)));
            return part;
        }
    },

    // --------------------------------------------------------
    // HOOK
    // --------------------------------------------------------
    'hook': {
        name: 'Hook',
        params: [
            { group: 'Hook', items: [
                { id: 'hookDepth', label: 'Hook Depth', default: 25, min: 5, max: 100 },
                { id: 'hookHeight', label: 'Hook Opening', default: 15, min: 5, max: 80 },
                { id: 'hookThick', label: 'Thickness', default: 5, min: 2, max: 20 },
                { id: 'hookWidth', label: 'Width', default: 20, min: 5, max: 100 },
            ]},
            { group: 'Base Plate', items: [
                { id: 'plateHeight', label: 'Plate Height', default: 50, min: 15, max: 200 },
                { id: 'plateThick', label: 'Plate Thickness', default: 4, min: 1, max: 15 },
            ]},
            { group: 'Mounting', items: [
                { id: 'holeDia', label: 'Screw Hole Dia', default: 4, min: 0, max: 10 },
                { id: 'holeCount', label: 'Screw Holes', default: 2, min: 0, max: 4, step: 1 },
            ]},
        ],
        generate(v) {
            const t = v.hookThick;
            const pt = v.plateThick;

            // Back plate
            let part = CSG.fromBox(v.hookWidth, v.plateHeight, pt,
                mat4Translate(0, v.plateHeight / 2, pt / 2));

            // Bottom arm (extends out from plate)
            part = part.union(CSG.fromBox(v.hookWidth, t, v.hookDepth,
                mat4Translate(0, t / 2, pt + v.hookDepth / 2)));

            // Front upright
            part = part.union(CSG.fromBox(v.hookWidth, v.hookHeight + t, t,
                mat4Translate(0, (v.hookHeight + t) / 2, pt + v.hookDepth - t / 2)));

            // Top lip (curves back in)
            const lipLen = Math.min(v.hookDepth * 0.4, 15);
            part = part.union(CSG.fromBox(v.hookWidth, t, lipLen,
                mat4Translate(0, v.hookHeight + t / 2, pt + v.hookDepth - lipLen / 2)));

            // Screw holes
            if (v.holeDia > 0 && v.holeCount > 0) {
                for (let i = 0; i < v.holeCount; i++) {
                    const yPos = v.plateHeight * (i + 1) / (v.holeCount + 1);
                    part = part.subtract(boltHole(v.holeDia, pt + 2,
                        0, yPos, pt / 2, Math.PI / 2));
                }
            }

            return part;
        }
    },

    // --------------------------------------------------------
    // KNOB / HANDLE
    // --------------------------------------------------------
    'knob': {
        name: 'Knob / Handle',
        params: [
            { group: 'Knob', items: [
                { id: 'knobDia', label: 'Knob Diameter', default: 30, min: 10, max: 100 },
                { id: 'knobHeight', label: 'Knob Height', default: 15, min: 3, max: 60 },
                { id: 'gripStyle', label: 'Grip Style', type: 'select',
                    options: ['smooth', 'knurled', 'hex'], default: 'knurled' },
            ]},
            { group: 'Shaft', items: [
                { id: 'shaftType', label: 'Shaft Type', type: 'select',
                    options: ['round', 'D-shaft', 'hex', 'none'], default: 'D-shaft' },
                { id: 'shaftDia', label: 'Shaft Diameter', default: 6, min: 1, max: 30 },
                { id: 'shaftDepth', label: 'Shaft Hole Depth', default: 10, min: 1, max: 50 },
            ]},
            { group: 'Options', items: [
                { id: 'setScrew', label: 'Set Screw Hole', type: 'checkbox', default: true },
                { id: 'setScrewDia', label: 'Set Screw Dia', default: 3, min: 1, max: 6 },
            ]},
        ],
        generate(v) {
            const r = v.knobDia / 2;
            const h = v.knobHeight;
            let part;

            if (v.gripStyle === 'hex') {
                // Hexagonal knob
                const hexGeom = new THREE.CylinderGeometry(r, r, h, 6);
                hexGeom.applyMatrix4(mat4Translate(0, h / 2, 0));
                part = CSG.fromGeometry(hexGeom);
            } else if (v.gripStyle === 'knurled') {
                // Knurled: base cylinder with vertical grooves
                part = CSG.fromCylinder(r, r, h, 32, mat4Translate(0, h / 2, 0));
                // Add knurl grooves
                const grooveCount = Math.floor(r * 2);
                const grooveR = r * 0.08;
                for (let i = 0; i < grooveCount; i++) {
                    const angle = (i / grooveCount) * Math.PI * 2;
                    const gx = Math.cos(angle) * (r + grooveR * 0.3);
                    const gz = Math.sin(angle) * (r + grooveR * 0.3);
                    part = part.subtract(CSG.fromCylinder(grooveR, grooveR, h + 2, 8,
                        mat4Translate(gx, h / 2, gz)));
                }
            } else {
                // Smooth
                part = CSG.fromCylinder(r, r, h, 32, mat4Translate(0, h / 2, 0));
            }

            // Top dome/cap
            const capH = h * 0.15;
            part = part.union(CSG.fromCylinder(r * 0.85, r * 0.5, capH, 32,
                mat4Translate(0, h + capH / 2, 0)));

            // Shaft hole
            if (v.shaftType !== 'none') {
                const sr = v.shaftDia / 2;
                if (v.shaftType === 'round') {
                    part = part.subtract(CSG.fromCylinder(sr, sr, v.shaftDepth, 24,
                        mat4Translate(0, v.shaftDepth / 2, 0)));
                } else if (v.shaftType === 'D-shaft') {
                    // Round hole with flat
                    part = part.subtract(CSG.fromCylinder(sr, sr, v.shaftDepth, 24,
                        mat4Translate(0, v.shaftDepth / 2, 0)));
                    // D-flat: remove a slice
                    const flatDepth = sr * 0.3;
                    part = part.subtract(CSG.fromBox(sr * 2, v.shaftDepth, flatDepth,
                        mat4Translate(0, v.shaftDepth / 2, sr - flatDepth / 2 + 0.1)));
                } else if (v.shaftType === 'hex') {
                    const hexHole = new THREE.CylinderGeometry(sr, sr, v.shaftDepth, 6);
                    hexHole.applyMatrix4(mat4Translate(0, v.shaftDepth / 2, 0));
                    part = part.subtract(CSG.fromGeometry(hexHole));
                }
            }

            // Set screw hole
            if (v.setScrew && v.shaftType !== 'none') {
                const ssR = v.setScrewDia / 2;
                const ssM = mat4RotateX(Math.PI / 2);
                ssM.setPosition(0, v.shaftDepth * 0.6, 0);
                // Actually we want it going radially in. Use rotateY for radial.
                const ssM2 = mat4RotateZ(Math.PI / 2);
                ssM2.setPosition(0, v.shaftDepth * 0.6, 0);
                part = part.subtract(CSG.fromCylinder(ssR, ssR, r + 2, 16, ssM2));
            }

            return part;
        }
    },
};

window.PartGenerators = PartGenerators;
