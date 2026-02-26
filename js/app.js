/**
 * 3D Parts Generator - Main Application
 *
 * Manages the Three.js scene, parameter UI, real-time preview,
 * measurement tools, and STL export.
 */

'use strict';

// ============================================================
// APP STATE
// ============================================================

const App = {
    scene: null,
    camera: null,
    renderer: null,
    controls: null,
    currentPart: 'l-bracket',
    currentMesh: null,
    gridHelper: null,
    showGrid: true,
    showDimensions: true,
    dimensionLabels: [],
    debounceTimer: null,
    material: new THREE.MeshPhysicalMaterial({
        color: 0x00b4d8,
        metalness: 0.1,
        roughness: 0.4,
        clearcoat: 0.3,
        clearcoatRoughness: 0.2,
    }),
    ghostMaterial: new THREE.MeshPhysicalMaterial({
        color: 0x00b4d8,
        metalness: 0.1,
        roughness: 0.4,
        transparent: true,
        opacity: 0.3,
        clearcoat: 0.3,
    }),
};

// ============================================================
// INITIALIZATION
// ============================================================

function init() {
    initScene();
    initUI();
    selectPart('l-bracket');
    animate();
}

function initScene() {
    const canvas = document.getElementById('render-canvas');
    const container = document.getElementById('viewport');

    // Renderer
    App.renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: true,
        alpha: false,
    });
    App.renderer.setPixelRatio(window.devicePixelRatio);
    App.renderer.setClearColor(0x0d1117, 1);
    App.renderer.shadowMap.enabled = true;
    App.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    App.renderer.outputEncoding = THREE.sRGBEncoding;

    // Scene
    App.scene = new THREE.Scene();
    App.scene.fog = new THREE.FogExp2(0x0d1117, 0.003);

    // Camera
    App.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 2000);
    App.camera.position.set(80, 60, 80);
    App.camera.lookAt(0, 15, 0);

    // Controls
    App.controls = new THREE.OrbitControls(App.camera, canvas);
    App.controls.enableDamping = true;
    App.controls.dampingFactor = 0.08;
    App.controls.target.set(0, 15, 0);
    App.controls.minDistance = 5;
    App.controls.maxDistance = 500;

    // Lighting
    const ambient = new THREE.AmbientLight(0x404060, 0.6);
    App.scene.add(ambient);

    const hemiLight = new THREE.HemisphereLight(0xb0d0ff, 0x303050, 0.4);
    App.scene.add(hemiLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(50, 80, 60);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    App.scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x80a0ff, 0.3);
    fillLight.position.set(-40, 30, -50);
    App.scene.add(fillLight);

    // Grid
    App.gridHelper = new THREE.GridHelper(200, 20, 0x1a3a5c, 0x0f2030);
    App.scene.add(App.gridHelper);

    // Ground plane (for shadows)
    const groundGeom = new THREE.PlaneGeometry(400, 400);
    const groundMat = new THREE.ShadowMaterial({ opacity: 0.15 });
    const ground = new THREE.Mesh(groundGeom, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    App.scene.add(ground);

    // Handle resize
    function resize() {
        const w = container.clientWidth;
        const h = container.clientHeight;
        App.camera.aspect = w / h;
        App.camera.updateProjectionMatrix();
        App.renderer.setSize(w, h);
    }
    window.addEventListener('resize', resize);
    resize();
}

// ============================================================
// ANIMATION LOOP
// ============================================================

function animate() {
    requestAnimationFrame(animate);
    App.controls.update();
    App.renderer.render(App.scene, App.camera);
}

// ============================================================
// UI INITIALIZATION
// ============================================================

function initUI() {
    // Part selection buttons
    document.querySelectorAll('.part-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.part-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectPart(btn.dataset.part);
        });
    });

    // Viewport control buttons
    document.getElementById('btn-reset-view').addEventListener('click', resetCamera);
    document.getElementById('btn-toggle-grid').addEventListener('click', toggleGrid);
    document.getElementById('btn-toggle-dimensions').addEventListener('click', toggleDimensions);

    // Export button
    document.getElementById('btn-export-stl').addEventListener('click', exportSTL);

    // Print settings change
    document.getElementById('wall-thickness').addEventListener('input', debouncedRegenerate);
    document.getElementById('tolerance').addEventListener('input', debouncedRegenerate);
}

// ============================================================
// PART SELECTION & PARAMETER UI
// ============================================================

function selectPart(partId) {
    App.currentPart = partId;
    const gen = PartGenerators[partId];
    if (!gen) return;

    buildParamUI(gen.params);
    regeneratePart();
}

function buildParamUI(paramGroups) {
    const container = document.getElementById('params-container');
    container.innerHTML = '';

    for (const group of paramGroups) {
        const groupDiv = document.createElement('div');
        groupDiv.className = 'param-group';

        const title = document.createElement('h4');
        title.textContent = group.group;
        groupDiv.appendChild(title);

        for (const param of group.items) {
            const row = document.createElement('div');
            row.className = 'param-row';

            const label = document.createElement('span');
            label.className = 'param-label';
            label.textContent = param.label;
            row.appendChild(label);

            if (param.type === 'checkbox') {
                const input = document.createElement('input');
                input.type = 'checkbox';
                input.id = 'param-' + param.id;
                input.checked = param.default;
                input.addEventListener('change', debouncedRegenerate);
                row.appendChild(input);
            } else if (param.type === 'select') {
                const select = document.createElement('select');
                select.id = 'param-' + param.id;
                for (const opt of param.options) {
                    const option = document.createElement('option');
                    option.value = opt;
                    option.textContent = opt;
                    if (opt === param.default) option.selected = true;
                    select.appendChild(option);
                }
                select.addEventListener('change', debouncedRegenerate);
                row.appendChild(select);
            } else {
                const input = document.createElement('input');
                input.type = 'number';
                input.id = 'param-' + param.id;
                input.value = param.default;
                input.min = param.min || 0;
                input.max = param.max || 999;
                input.step = param.step || 0.1;
                input.addEventListener('input', debouncedRegenerate);
                row.appendChild(input);

                const unit = document.createElement('span');
                unit.className = 'param-unit';
                unit.textContent = 'mm';
                row.appendChild(unit);
            }

            groupDiv.appendChild(row);
        }

        container.appendChild(groupDiv);
    }

    // Add measurement tools section
    addMeasurementToolsUI(container);
}

// ============================================================
// MEASUREMENT TOOLS UI
// ============================================================

function addMeasurementToolsUI(container) {
    const group = document.createElement('div');
    group.className = 'param-group';

    const title = document.createElement('h4');
    title.textContent = 'Measurement Tools';
    group.appendChild(title);

    // Photo measurement button
    const photoRow = document.createElement('div');
    photoRow.className = 'param-row';
    photoRow.style.flexDirection = 'column';
    photoRow.style.alignItems = 'stretch';
    photoRow.style.gap = '6px';

    const photoBtn = document.createElement('button');
    photoBtn.className = 'measure-btn';
    photoBtn.textContent = 'Measure from Photo';
    photoBtn.title = 'Upload a photo with a reference object to extract dimensions';
    photoBtn.addEventListener('click', openPhotoMeasure);
    styleSecondaryBtn(photoBtn);
    photoRow.appendChild(photoBtn);

    // Import dimensions from file
    const importBtn = document.createElement('button');
    importBtn.className = 'measure-btn';
    importBtn.textContent = 'Import Dimensions';
    importBtn.title = 'Import dimensions from a JSON or CSV file';
    importBtn.addEventListener('click', importDimensions);
    styleSecondaryBtn(importBtn);
    photoRow.appendChild(importBtn);

    // STL reference import
    const stlBtn = document.createElement('button');
    stlBtn.className = 'measure-btn';
    stlBtn.textContent = 'Import Reference STL';
    stlBtn.title = 'Load an STL scan to measure and trace dimensions';
    stlBtn.addEventListener('click', importReferenceSTL);
    styleSecondaryBtn(stlBtn);
    photoRow.appendChild(stlBtn);

    // Webcam + Grid Mat measurement
    const webcamBtn = document.createElement('button');
    webcamBtn.className = 'measure-btn';
    webcamBtn.textContent = 'Webcam + Grid Mat';
    webcamBtn.title = 'Use your webcam with a calibration grid mat to measure objects live';
    webcamBtn.addEventListener('click', openWebcamMeasure);
    styleSecondaryBtn(webcamBtn);
    photoRow.appendChild(webcamBtn);

    group.appendChild(photoRow);
    container.appendChild(group);
}

function styleSecondaryBtn(btn) {
    btn.style.cssText = `
        padding: 8px 12px;
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 4px;
        color: var(--text);
        font-size: 12px;
        cursor: pointer;
        transition: all 0.15s;
        text-align: center;
    `;
    btn.addEventListener('mouseenter', () => {
        btn.style.borderColor = 'var(--accent)';
        btn.style.color = 'var(--accent)';
    });
    btn.addEventListener('mouseleave', () => {
        btn.style.borderColor = 'var(--border)';
        btn.style.color = 'var(--text)';
    });
}

// ============================================================
// PHOTO MEASUREMENT TOOL
// ============================================================

function openPhotoMeasure() {
    // Create modal overlay
    const modal = createModal('Measure from Photo');

    const content = modal.querySelector('.modal-body');
    content.innerHTML = `
        <p style="margin-bottom:12px;color:var(--text-dim);font-size:13px;">
            Upload a photo of the object you want to replicate. Include a reference object
            of known size (coin, ruler, credit card) for scale.
        </p>
        <div id="photo-drop-zone" style="
            border: 2px dashed var(--border);
            border-radius: 8px;
            padding: 40px 20px;
            text-align: center;
            cursor: pointer;
            margin-bottom: 12px;
            transition: border-color 0.2s;
        ">
            <div style="font-size:14px;color:var(--text);">Drop image here or click to upload</div>
            <div style="font-size:12px;color:var(--text-dim);margin-top:4px;">JPG, PNG supported</div>
            <input type="file" id="photo-input" accept="image/*" style="display:none">
        </div>

        <div id="photo-reference" style="display:none;">
            <label style="display:block;margin-bottom:8px;">
                <span style="font-size:13px;">Reference object:</span>
                <select id="ref-object" style="
                    margin-left:8px;padding:4px 8px;background:var(--bg-input);
                    border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:13px;
                ">
                    <option value="25.00">US Quarter (25mm)</option>
                    <option value="24.26">US Nickel (21.21mm)</option>
                    <option value="85.60">Credit Card Width (85.6mm)</option>
                    <option value="custom">Custom size...</option>
                </select>
            </label>
            <div id="custom-ref" style="display:none;margin-bottom:8px;">
                <label style="font-size:13px;">
                    Reference size:
                    <input type="number" id="custom-ref-size" value="25" style="
                        width:70px;padding:4px 8px;background:var(--bg-input);
                        border:1px solid var(--border);border-radius:4px;color:var(--text);
                        font-size:13px;text-align:right;margin-left:4px;
                    "> mm
                </label>
            </div>
            <div id="photo-canvas-container" style="position:relative;margin-bottom:12px;">
                <canvas id="photo-canvas" style="max-width:100%;border-radius:4px;cursor:crosshair;"></canvas>
            </div>
            <div id="photo-instructions" style="font-size:12px;color:var(--text-dim);margin-bottom:8px;">
                <strong>Step 1:</strong> Click two points on the reference object to set scale.<br>
                <strong>Step 2:</strong> Click two points on the part to measure a dimension.<br>
                Measurements will appear below.
            </div>
            <div id="photo-measurements" style="font-size:13px;"></div>
        </div>
    `;

    document.body.appendChild(modal);

    // Event handlers
    const dropZone = modal.querySelector('#photo-drop-zone');
    const fileInput = modal.querySelector('#photo-input');
    const refSelect = modal.querySelector('#ref-object');
    const customRef = modal.querySelector('#custom-ref');

    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--accent)';
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--border)';
    });
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--border)';
        if (e.dataTransfer.files.length) handlePhotoUpload(e.dataTransfer.files[0], modal);
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) handlePhotoUpload(fileInput.files[0], modal);
    });
    refSelect.addEventListener('change', () => {
        customRef.style.display = refSelect.value === 'custom' ? 'block' : 'none';
    });
}

function handlePhotoUpload(file, modal) {
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {
            modal.querySelector('#photo-drop-zone').style.display = 'none';
            modal.querySelector('#photo-reference').style.display = 'block';

            const canvas = modal.querySelector('#photo-canvas');
            const maxW = 500;
            const scale = Math.min(maxW / img.width, 1);
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;

            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

            initPhotoMeasurement(canvas, ctx, img, scale, modal);
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function initPhotoMeasurement(canvas, ctx, img, imgScale, modal) {
    const state = {
        mode: 'reference', // 'reference' or 'measure'
        clicks: [],
        refPixelDist: null,
        refRealSize: null,
        pixelsPerMm: null,
        measurements: [],
        imgData: null,
    };

    // Store image data for redrawing
    state.imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);

    const measDiv = modal.querySelector('#photo-measurements');
    const instrDiv = modal.querySelector('#photo-instructions');

    canvas.addEventListener('click', function(e) {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        state.clicks.push({ x, y });

        // Draw click point
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = state.mode === 'reference' ? '#ffa502' : '#00d4ff';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        ctx.stroke();

        if (state.clicks.length === 2) {
            const [p1, p2] = state.clicks;
            const dist = Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2);

            // Draw line
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = state.mode === 'reference' ? '#ffa502' : '#00d4ff';
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 4]);
            ctx.stroke();
            ctx.setLineDash([]);

            if (state.mode === 'reference') {
                const refSelect = modal.querySelector('#ref-object');
                const customInput = modal.querySelector('#custom-ref-size');
                state.refRealSize = refSelect.value === 'custom'
                    ? parseFloat(customInput.value)
                    : parseFloat(refSelect.value);
                state.refPixelDist = dist;
                state.pixelsPerMm = dist / state.refRealSize;

                instrDiv.innerHTML = `
                    <span style="color:var(--success);">Scale set: ${state.pixelsPerMm.toFixed(2)} px/mm</span><br>
                    Now click two points on the part to measure.
                `;
                state.mode = 'measure';
            } else {
                const realDist = dist / state.pixelsPerMm;
                state.measurements.push(realDist);

                // Draw measurement label
                const midX = (p1.x + p2.x) / 2;
                const midY = (p1.y + p2.y) / 2;
                ctx.font = '12px sans-serif';
                ctx.fillStyle = '#000';
                ctx.fillRect(midX - 25, midY - 8, 50, 16);
                ctx.fillStyle = '#00d4ff';
                ctx.textAlign = 'center';
                ctx.fillText(realDist.toFixed(1) + 'mm', midX, midY + 4);

                // Update measurements list
                let html = '<strong>Measurements:</strong><br>';
                state.measurements.forEach((m, i) => {
                    html += `<span style="color:var(--accent);">#${i + 1}: ${m.toFixed(2)} mm</span>`;
                    html += ` <button class="apply-meas" data-value="${m.toFixed(2)}" style="
                        padding:2px 8px;font-size:11px;background:var(--bg-card);border:1px solid var(--border);
                        border-radius:3px;color:var(--accent);cursor:pointer;margin-left:4px;
                    ">Apply</button><br>`;
                });
                measDiv.innerHTML = html;

                // Add apply buttons
                measDiv.querySelectorAll('.apply-meas').forEach(btn => {
                    btn.addEventListener('click', () => {
                        // Copy measurement to clipboard and show notification
                        const val = btn.dataset.value;
                        showNotification(`Measurement: ${val}mm copied! Paste into any parameter field.`);
                        navigator.clipboard.writeText(val).catch(() => {});
                    });
                });
            }

            state.clicks = [];
        }
    });
}

// ============================================================
// WEBCAM + GRID MAT MEASUREMENT
// ============================================================

function openWebcamMeasure() {
    const modal = createModal('Webcam + Grid Mat Measurement');
    const content = modal.querySelector('.modal-body');

    content.innerHTML = `
        <p style="margin-bottom:12px;color:var(--text-dim);font-size:13px;">
            Place your object on a grid/cutting mat. The webcam will detect the grid to
            auto-calibrate scale, then you can click to measure dimensions directly.
        </p>

        <div style="margin-bottom:12px;">
            <label style="font-size:13px;">
                Grid spacing:
                <input type="number" id="grid-spacing" value="10" min="1" max="100" style="
                    width:60px;padding:4px 8px;background:var(--bg-input);
                    border:1px solid var(--border);border-radius:4px;color:var(--text);
                    font-size:13px;text-align:right;margin:0 4px;
                "> mm
            </label>
            <span style="font-size:11px;color:var(--text-dim);margin-left:8px;">
                (distance between grid lines on your mat)
            </span>
        </div>

        <div id="webcam-container" style="position:relative;margin-bottom:12px;">
            <video id="webcam-video" autoplay playsinline style="
                max-width:100%;border-radius:4px;background:#000;display:block;
            "></video>
            <canvas id="webcam-overlay" style="
                position:absolute;top:0;left:0;width:100%;height:100%;
                pointer-events:none;
            "></canvas>
            <canvas id="webcam-measure-canvas" style="
                position:absolute;top:0;left:0;width:100%;height:100%;
                cursor:crosshair;
            "></canvas>
        </div>

        <div id="webcam-controls" style="display:flex;gap:8px;margin-bottom:12px;">
            <button id="wcam-start" style="
                flex:1;padding:8px;background:var(--accent);border:none;border-radius:4px;
                color:#000;font-weight:600;font-size:13px;cursor:pointer;
            ">Start Camera</button>
            <button id="wcam-calibrate" disabled style="
                flex:1;padding:8px;background:var(--bg-card);border:1px solid var(--border);
                border-radius:4px;color:var(--text-dim);font-size:13px;cursor:pointer;
            ">Calibrate Grid</button>
            <button id="wcam-snapshot" disabled style="
                flex:1;padding:8px;background:var(--bg-card);border:1px solid var(--border);
                border-radius:4px;color:var(--text-dim);font-size:13px;cursor:pointer;
            ">Snapshot</button>
        </div>

        <div id="wcam-status" style="font-size:12px;color:var(--text-dim);margin-bottom:8px;">
            Click "Start Camera" to begin.
        </div>

        <div id="wcam-instructions" style="font-size:12px;color:var(--text-dim);display:none;">
            <strong>After calibration:</strong> Click two points on your object to measure
            the distance between them. Measurements appear below.
        </div>

        <div id="wcam-measurements" style="font-size:13px;margin-top:8px;"></div>
    `;

    document.body.appendChild(modal);

    // Webcam state
    const wcamState = {
        stream: null,
        video: null,
        calibrated: false,
        pixelsPerMm: null,
        frozen: false,
        clicks: [],
        measurements: [],
    };

    const startBtn = modal.querySelector('#wcam-start');
    const calibrateBtn = modal.querySelector('#wcam-calibrate');
    const snapshotBtn = modal.querySelector('#wcam-snapshot');
    const statusDiv = modal.querySelector('#wcam-status');
    const instrDiv = modal.querySelector('#wcam-instructions');
    const measDiv = modal.querySelector('#wcam-measurements');
    const video = modal.querySelector('#webcam-video');
    const measureCanvas = modal.querySelector('#webcam-measure-canvas');

    startBtn.addEventListener('click', async () => {
        try {
            wcamState.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
            });
            video.srcObject = wcamState.stream;
            wcamState.video = video;

            video.addEventListener('loadedmetadata', () => {
                measureCanvas.width = video.videoWidth;
                measureCanvas.height = video.videoHeight;
                const overlay = modal.querySelector('#webcam-overlay');
                overlay.width = video.videoWidth;
                overlay.height = video.videoHeight;
            });

            startBtn.textContent = 'Camera Active';
            startBtn.disabled = true;
            startBtn.style.background = 'var(--success)';
            calibrateBtn.disabled = false;
            calibrateBtn.style.color = 'var(--text)';
            snapshotBtn.disabled = false;
            snapshotBtn.style.color = 'var(--text)';
            statusDiv.innerHTML = '<span style="color:var(--success);">Camera active.</span> Position your grid mat and click "Calibrate Grid".';
        } catch (err) {
            statusDiv.innerHTML = `<span style="color:var(--danger);">Camera error: ${err.message}</span>`;
        }
    });

    calibrateBtn.addEventListener('click', () => {
        // Auto-calibrate: detect grid lines via simple edge detection
        const gridSpacing = parseFloat(modal.querySelector('#grid-spacing').value) || 10;
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = video.videoWidth;
        tempCanvas.height = video.videoHeight;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(video, 0, 0);

        const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
        const gridPixelSpacing = detectGridSpacing(imageData, tempCanvas.width, tempCanvas.height);

        if (gridPixelSpacing > 0) {
            wcamState.pixelsPerMm = gridPixelSpacing / gridSpacing;
            wcamState.calibrated = true;
            statusDiv.innerHTML = `<span style="color:var(--success);">Calibrated! Grid detected: ${gridPixelSpacing.toFixed(1)}px = ${gridSpacing}mm (${wcamState.pixelsPerMm.toFixed(2)} px/mm)</span>`;
            instrDiv.style.display = 'block';

            // Draw grid overlay
            const overlay = modal.querySelector('#webcam-overlay');
            const octx = overlay.getContext('2d');
            octx.clearRect(0, 0, overlay.width, overlay.height);
            octx.strokeStyle = 'rgba(0, 212, 255, 0.3)';
            octx.lineWidth = 1;
            for (let x = 0; x < overlay.width; x += gridPixelSpacing) {
                octx.beginPath();
                octx.moveTo(x, 0);
                octx.lineTo(x, overlay.height);
                octx.stroke();
            }
            for (let y = 0; y < overlay.height; y += gridPixelSpacing) {
                octx.beginPath();
                octx.moveTo(0, y);
                octx.lineTo(overlay.width, y);
                octx.stroke();
            }
        } else {
            // Fallback: manual calibration
            statusDiv.innerHTML = '<span style="color:var(--warning);">Auto-detect failed. Click "Snapshot" then click two grid intersections to calibrate manually.</span>';
        }
    });

    snapshotBtn.addEventListener('click', () => {
        // Freeze frame for measurement
        const ctx = measureCanvas.getContext('2d');
        measureCanvas.width = video.videoWidth;
        measureCanvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);
        wcamState.frozen = true;
        snapshotBtn.textContent = 'New Snapshot';
        statusDiv.innerHTML = wcamState.calibrated
            ? '<span style="color:var(--accent);">Frame captured. Click two points to measure.</span>'
            : '<span style="color:var(--warning);">Frame captured. Click two grid intersections to set scale, then measure.</span>';

        if (!wcamState.calibrated) {
            wcamState.calibrateMode = true;
        }
    });

    measureCanvas.addEventListener('click', function(e) {
        if (!wcamState.frozen) return;

        const rect = measureCanvas.getBoundingClientRect();
        const scaleX = measureCanvas.width / rect.width;
        const scaleY = measureCanvas.height / rect.height;
        const x = (e.clientX - rect.left) * scaleX;
        const y = (e.clientY - rect.top) * scaleY;

        const ctx = measureCanvas.getContext('2d');

        // Draw point
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fillStyle = wcamState.calibrateMode ? '#ffa502' : '#00d4ff';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();

        wcamState.clicks.push({ x, y });

        if (wcamState.clicks.length === 2) {
            const [p1, p2] = wcamState.clicks;
            const pixDist = Math.sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2);

            // Draw line
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = wcamState.calibrateMode ? '#ffa502' : '#00d4ff';
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 4]);
            ctx.stroke();
            ctx.setLineDash([]);

            if (wcamState.calibrateMode) {
                // Use this as grid calibration
                const gridSpacing = parseFloat(modal.querySelector('#grid-spacing').value) || 10;
                wcamState.pixelsPerMm = pixDist / gridSpacing;
                wcamState.calibrated = true;
                wcamState.calibrateMode = false;
                statusDiv.innerHTML = `<span style="color:var(--success);">Manual calibration set: ${wcamState.pixelsPerMm.toFixed(2)} px/mm. Now click to measure.</span>`;
                instrDiv.style.display = 'block';
            } else if (wcamState.calibrated) {
                const realDist = pixDist / wcamState.pixelsPerMm;
                wcamState.measurements.push(realDist);

                // Label on canvas
                const midX = (p1.x + p2.x) / 2;
                const midY = (p1.y + p2.y) / 2;
                ctx.font = '16px sans-serif';
                const text = realDist.toFixed(1) + 'mm';
                const tw = ctx.measureText(text).width;
                ctx.fillStyle = 'rgba(0,0,0,0.7)';
                ctx.fillRect(midX - tw / 2 - 4, midY - 10, tw + 8, 20);
                ctx.fillStyle = '#00d4ff';
                ctx.textAlign = 'center';
                ctx.fillText(text, midX, midY + 5);

                // Update list
                let html = '<strong>Measurements:</strong><br>';
                wcamState.measurements.forEach((m, i) => {
                    html += `<span style="color:var(--accent);">#${i + 1}: ${m.toFixed(2)} mm</span>`;
                    html += ` <button class="apply-meas" data-value="${m.toFixed(2)}" style="
                        padding:2px 8px;font-size:11px;background:var(--bg-card);border:1px solid var(--border);
                        border-radius:3px;color:var(--accent);cursor:pointer;margin-left:4px;
                    ">Apply</button><br>`;
                });
                measDiv.innerHTML = html;

                measDiv.querySelectorAll('.apply-meas').forEach(btn => {
                    btn.addEventListener('click', () => {
                        navigator.clipboard.writeText(btn.dataset.value).catch(() => {});
                        showNotification(`Measurement: ${btn.dataset.value}mm copied!`);
                    });
                });
            }

            wcamState.clicks = [];
        }
    });

    // Cleanup on modal close
    const origClose = modal.querySelector('button:last-of-type');
    const closeHandler = () => {
        if (wcamState.stream) {
            wcamState.stream.getTracks().forEach(t => t.stop());
        }
    };
    modal.addEventListener('click', e => {
        if (e.target === modal) closeHandler();
    });
    modal.querySelector('button[style*="font-size: 24px"]') &&
        modal.querySelector('button[style*="font-size: 24px"]').addEventListener('click', closeHandler);
}

/**
 * Simple grid line detection via frequency analysis of horizontal/vertical edge profiles.
 * Scans the image for periodic bright/dark transitions to estimate grid spacing in pixels.
 */
function detectGridSpacing(imageData, width, height) {
    const data = imageData.data;

    // Convert center strip to grayscale and compute horizontal edge profile
    const centerY = Math.floor(height / 2);
    const stripHeight = Math.min(50, Math.floor(height / 4));
    const profile = new Float32Array(width);

    for (let x = 0; x < width; x++) {
        let sum = 0;
        for (let dy = -stripHeight; dy <= stripHeight; dy++) {
            const y = centerY + dy;
            if (y < 0 || y >= height) continue;
            const idx = (y * width + x) * 4;
            // Grayscale
            sum += data[idx] * 0.299 + data[idx + 1] * 0.587 + data[idx + 2] * 0.114;
        }
        profile[x] = sum / (stripHeight * 2 + 1);
    }

    // Compute derivative (edge detection)
    const edges = new Float32Array(width);
    for (let x = 1; x < width - 1; x++) {
        edges[x] = Math.abs(profile[x + 1] - profile[x - 1]);
    }

    // Auto-correlation to find periodicity
    const minSpacing = 15; // minimum grid spacing in pixels
    const maxSpacing = Math.min(200, Math.floor(width / 3));
    let bestSpacing = 0;
    let bestScore = 0;

    for (let spacing = minSpacing; spacing <= maxSpacing; spacing++) {
        let score = 0;
        let count = 0;
        for (let x = 0; x < width - spacing; x++) {
            score += edges[x] * edges[x + spacing];
            count++;
        }
        score /= count;
        if (score > bestScore) {
            bestScore = score;
            bestSpacing = spacing;
        }
    }

    // Verify: the score should be significantly above average
    let avgScore = 0;
    for (let spacing = minSpacing; spacing <= maxSpacing; spacing++) {
        let score = 0;
        let count = 0;
        for (let x = 0; x < width - spacing; x++) {
            score += edges[x] * edges[x + spacing];
            count++;
        }
        avgScore += score / count;
    }
    avgScore /= (maxSpacing - minSpacing + 1);

    if (bestScore > avgScore * 1.5 && bestSpacing > 0) {
        return bestSpacing;
    }

    return 0; // detection failed
}

// ============================================================
// IMPORT DIMENSIONS (JSON/CSV)
// ============================================================

function importDimensions() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.csv,.txt';
    input.addEventListener('change', () => {
        const file = input.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const text = e.target.result;
                let dimensions = {};

                if (file.name.endsWith('.json')) {
                    dimensions = JSON.parse(text);
                } else {
                    // CSV/TXT: expect "key,value" or "key=value" lines
                    text.split('\n').forEach(line => {
                        line = line.trim();
                        if (!line || line.startsWith('#')) return;
                        const parts = line.split(/[,=\t]/);
                        if (parts.length >= 2) {
                            const key = parts[0].trim().toLowerCase().replace(/\s+/g, '');
                            const val = parseFloat(parts[1].trim());
                            if (!isNaN(val)) dimensions[key] = val;
                        }
                    });
                }

                // Try to apply dimensions to current parameters
                let applied = 0;
                for (const [key, value] of Object.entries(dimensions)) {
                    // Try matching param IDs
                    const input = document.getElementById('param-' + key);
                    if (input) {
                        input.value = value;
                        applied++;
                    }
                }

                if (applied > 0) {
                    regeneratePart();
                    showNotification(`Applied ${applied} dimension(s) from file.`);
                } else {
                    showNotification('No matching parameters found. Check parameter names.', 'warning');
                }
            } catch (err) {
                showNotification('Error reading file: ' + err.message, 'error');
            }
        };
        reader.readAsText(file);
    });
    input.click();
}

// ============================================================
// REFERENCE STL IMPORT (3D Scan overlay)
// ============================================================

function importReferenceSTL() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.stl,.obj';
    input.addEventListener('change', () => {
        const file = input.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const buffer = e.target.result;
                const geometry = parseSTLBinary(buffer);

                if (!geometry) {
                    showNotification('Could not parse STL file.', 'error');
                    return;
                }

                // Remove existing reference mesh
                const existing = App.scene.getObjectByName('reference-stl');
                if (existing) App.scene.remove(existing);

                // Add as ghost overlay
                geometry.computeVertexNormals();
                geometry.center();
                // Auto-scale if enormous
                geometry.computeBoundingBox();
                const bbox = geometry.boundingBox;
                const maxDim = Math.max(
                    bbox.max.x - bbox.min.x,
                    bbox.max.y - bbox.min.y,
                    bbox.max.z - bbox.min.z
                );
                if (maxDim > 500) {
                    const s = 100 / maxDim;
                    geometry.scale(s, s, s);
                }

                // Position on ground
                geometry.computeBoundingBox();
                const yOffset = -geometry.boundingBox.min.y;
                geometry.translate(0, yOffset, 0);

                const mesh = new THREE.Mesh(geometry, App.ghostMaterial);
                mesh.name = 'reference-stl';
                App.scene.add(mesh);

                // Compute and show bounding dimensions
                geometry.computeBoundingBox();
                const bb = geometry.boundingBox;
                const dims = {
                    width: (bb.max.x - bb.min.x).toFixed(1),
                    height: (bb.max.y - bb.min.y).toFixed(1),
                    depth: (bb.max.z - bb.min.z).toFixed(1),
                };

                showNotification(
                    `Reference loaded: ${dims.width} x ${dims.height} x ${dims.depth} mm`
                );
            } catch (err) {
                showNotification('Error loading STL: ' + err.message, 'error');
            }
        };
        reader.readAsArrayBuffer(file);
    });
    input.click();
}

function parseSTLBinary(buffer) {
    const dv = new DataView(buffer);

    // Check if ASCII STL
    const header = String.fromCharCode.apply(null, new Uint8Array(buffer, 0, 5));
    if (header === 'solid') {
        // Might be ASCII — try binary anyway if large enough
        if (buffer.byteLength < 84) return null;
    }

    const triangles = dv.getUint32(80, true);
    const expectedSize = 84 + triangles * 50;

    if (buffer.byteLength < expectedSize) return null;

    const vertices = new Float32Array(triangles * 9);
    const normals = new Float32Array(triangles * 9);

    let offset = 84;
    for (let i = 0; i < triangles; i++) {
        const nx = dv.getFloat32(offset, true); offset += 4;
        const ny = dv.getFloat32(offset, true); offset += 4;
        const nz = dv.getFloat32(offset, true); offset += 4;

        for (let j = 0; j < 3; j++) {
            const idx = i * 9 + j * 3;
            vertices[idx] = dv.getFloat32(offset, true); offset += 4;
            vertices[idx + 1] = dv.getFloat32(offset, true); offset += 4;
            vertices[idx + 2] = dv.getFloat32(offset, true); offset += 4;
            normals[idx] = nx;
            normals[idx + 1] = ny;
            normals[idx + 2] = nz;
        }
        offset += 2; // attribute byte count
    }

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geom.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    return geom;
}

// ============================================================
// PART GENERATION
// ============================================================

function getParamValues() {
    const gen = PartGenerators[App.currentPart];
    if (!gen) return {};

    const values = {};
    for (const group of gen.params) {
        for (const param of group.items) {
            const el = document.getElementById('param-' + param.id);
            if (!el) continue;

            if (param.type === 'checkbox') {
                values[param.id] = el.checked;
            } else if (param.type === 'select') {
                values[param.id] = el.value;
            } else {
                values[param.id] = parseFloat(el.value) || param.default;
            }
        }
    }

    return values;
}

function regeneratePart() {
    const gen = PartGenerators[App.currentPart];
    if (!gen) return;

    const values = getParamValues();

    try {
        const csg = gen.generate(values);
        const geometry = csg.toGeometry();
        geometry.computeVertexNormals();

        // Remove old mesh
        if (App.currentMesh) {
            App.scene.remove(App.currentMesh);
            App.currentMesh.geometry.dispose();
        }

        // Create new mesh
        App.currentMesh = new THREE.Mesh(geometry, App.material);
        App.currentMesh.castShadow = true;
        App.currentMesh.receiveShadow = true;
        App.scene.add(App.currentMesh);

        // Update bounding box info
        geometry.computeBoundingBox();
        const bb = geometry.boundingBox;
        const dims = {
            x: (bb.max.x - bb.min.x).toFixed(1),
            y: (bb.max.y - bb.min.y).toFixed(1),
            z: (bb.max.z - bb.min.z).toFixed(1),
        };
        document.getElementById('part-dimensions').textContent =
            `Bounding box: ${dims.x} x ${dims.y} x ${dims.z} mm`;

        // Update dimension labels
        if (App.showDimensions) {
            updateDimensionLabels(bb);
        }
    } catch (err) {
        console.error('Part generation error:', err);
    }
}

function debouncedRegenerate() {
    clearTimeout(App.debounceTimer);
    App.debounceTimer = setTimeout(regeneratePart, 150);
}

// ============================================================
// DIMENSION LABELS (3D scene annotations)
// ============================================================

function updateDimensionLabels(bb) {
    // Remove old labels
    clearDimensionLabels();

    if (!App.showDimensions) return;

    const offset = 5;

    // Width (X axis) - red
    addDimensionLine(
        new THREE.Vector3(bb.min.x, bb.min.y - offset, bb.min.z),
        new THREE.Vector3(bb.max.x, bb.min.y - offset, bb.min.z),
        0xff4757
    );

    // Height (Y axis) - green
    addDimensionLine(
        new THREE.Vector3(bb.max.x + offset, bb.min.y, bb.min.z),
        new THREE.Vector3(bb.max.x + offset, bb.max.y, bb.min.z),
        0x2ed573
    );

    // Depth (Z axis) - blue
    addDimensionLine(
        new THREE.Vector3(bb.min.x, bb.min.y - offset, bb.min.z),
        new THREE.Vector3(bb.min.x, bb.min.y - offset, bb.max.z),
        0x00d4ff
    );
}

function addDimensionLine(start, end, color) {
    const points = [start, end];
    const geom = new THREE.BufferGeometry().setFromPoints(points);
    const mat = new THREE.LineBasicMaterial({ color: color, linewidth: 2 });
    const line = new THREE.Line(geom, mat);
    line.userData.isDimensionLabel = true;
    App.scene.add(line);
    App.dimensionLabels.push(line);

    // End caps
    for (const p of [start, end]) {
        const capGeom = new THREE.SphereGeometry(0.5, 6, 6);
        const capMat = new THREE.MeshBasicMaterial({ color: color });
        const cap = new THREE.Mesh(capGeom, capMat);
        cap.position.copy(p);
        cap.userData.isDimensionLabel = true;
        App.scene.add(cap);
        App.dimensionLabels.push(cap);
    }
}

function clearDimensionLabels() {
    for (const obj of App.dimensionLabels) {
        App.scene.remove(obj);
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) obj.material.dispose();
    }
    App.dimensionLabels = [];
}

// ============================================================
// VIEWPORT CONTROLS
// ============================================================

function resetCamera() {
    if (App.currentMesh) {
        App.currentMesh.geometry.computeBoundingBox();
        const bb = App.currentMesh.geometry.boundingBox;
        const center = new THREE.Vector3();
        bb.getCenter(center);
        const size = new THREE.Vector3();
        bb.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        const dist = maxDim * 2.5;

        App.camera.position.set(center.x + dist * 0.7, center.y + dist * 0.5, center.z + dist * 0.7);
        App.controls.target.copy(center);
    } else {
        App.camera.position.set(80, 60, 80);
        App.controls.target.set(0, 15, 0);
    }
    App.controls.update();
}

function toggleGrid() {
    App.showGrid = !App.showGrid;
    App.gridHelper.visible = App.showGrid;
    document.getElementById('btn-toggle-grid').classList.toggle('active', App.showGrid);
}

function toggleDimensions() {
    App.showDimensions = !App.showDimensions;
    document.getElementById('btn-toggle-dimensions').classList.toggle('active', App.showDimensions);
    if (App.showDimensions && App.currentMesh) {
        App.currentMesh.geometry.computeBoundingBox();
        updateDimensionLabels(App.currentMesh.geometry.boundingBox);
    } else {
        clearDimensionLabels();
    }
}

// ============================================================
// STL EXPORT
// ============================================================

function exportSTL() {
    if (!App.currentMesh) {
        showNotification('No part to export!', 'error');
        return;
    }

    const gen = PartGenerators[App.currentPart];
    const filename = (gen ? gen.name.replace(/[^a-zA-Z0-9]/g, '_') : 'part') + '.stl';
    STLExporter.download(App.currentMesh, filename);
    showNotification('STL exported: ' + filename);
}

// ============================================================
// NOTIFICATIONS
// ============================================================

function showNotification(message, type) {
    type = type || 'info';
    const colors = {
        info: 'var(--accent)',
        warning: 'var(--warning)',
        error: 'var(--danger)',
    };

    const notif = document.createElement('div');
    notif.style.cssText = `
        position: fixed;
        top: 60px;
        left: 50%;
        transform: translateX(-50%);
        padding: 10px 20px;
        background: var(--bg-panel);
        border: 1px solid ${colors[type]};
        border-radius: 8px;
        color: ${colors[type]};
        font-size: 13px;
        z-index: 10000;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        animation: slideDown 0.3s ease;
    `;
    notif.textContent = message;
    document.body.appendChild(notif);

    setTimeout(() => {
        notif.style.opacity = '0';
        notif.style.transition = 'opacity 0.3s';
        setTimeout(() => notif.remove(), 300);
    }, 3000);
}

// ============================================================
// MODAL HELPER
// ============================================================

function createModal(title) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.7);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.2s ease;
    `;

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.cssText = `
        background: var(--bg-panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 24px;
        max-width: 560px;
        width: 90%;
        max-height: 85vh;
        overflow-y: auto;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    `;

    const header = document.createElement('div');
    header.style.cssText = `
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    `;

    const h3 = document.createElement('h3');
    h3.textContent = title;
    h3.style.cssText = 'font-size:16px;color:var(--text-bright);';

    const closeBtn = document.createElement('button');
    closeBtn.textContent = '\u00d7';
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: var(--text-dim);
        font-size: 24px;
        cursor: pointer;
        padding: 0 4px;
        line-height: 1;
    `;
    closeBtn.addEventListener('click', () => overlay.remove());

    header.appendChild(h3);
    header.appendChild(closeBtn);
    modal.appendChild(header);

    const body = document.createElement('div');
    body.className = 'modal-body';
    modal.appendChild(body);

    overlay.appendChild(modal);

    // Close on background click
    overlay.addEventListener('click', e => {
        if (e.target === overlay) overlay.remove();
    });

    return overlay;
}

// ============================================================
// CSS ANIMATIONS (injected)
// ============================================================

const styleSheet = document.createElement('style');
styleSheet.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes slideDown {
        from { transform: translateX(-50%) translateY(-20px); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
`;
document.head.appendChild(styleSheet);

// ============================================================
// START
// ============================================================

window.addEventListener('DOMContentLoaded', init);
