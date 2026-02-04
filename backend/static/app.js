// TF Showbuilder - Static UI Application
const API_BASE = '/api';

// State
let state = {
    channels: [],
    scenes: [],
    shows: [],
    bands: [],
    artists: [],
    songs: [],
    patches: [],
    devices: [],
    einkDisplays: [],
    selectedScene: null,
    selectedShow: null,
    selectedSong: null,
    selectedArtist: null,
    channelView: 'inputs-1-16',
    meters: {}
};

// Navigation
function showPage(pageName) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    document.getElementById(`page-${pageName}`).classList.add('active');
    document.querySelector(`[data-page="${pageName}"]`).classList.add('active');

    // Load page data
    switch(pageName) {
        case 'home': loadDashboard(); break;
        case 'mixer': loadChannels(); break;
        case 'scenes': loadScenes(); break;
        case 'shows': loadShows(); break;
        case 'artists': loadArtists(); break;
        case 'songs': loadSongs(); break;
        case 'patches': loadPatches(); break;
        case 'devices': loadDevices(); break;
        case 'backstage': loadBackstage(); break;
        case 'eink': loadEinkDisplays(); break;
        case 'settings': loadSettings(); break;
    }
}

// Initialize navigation
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => showPage(btn.dataset.page));
});

// API Helper
async function api(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API Error: ${endpoint}`, error);
        throw error;
    }
}

// ============== DASHBOARD ==============
async function loadDashboard() {
    // TF-Rack Status
    try {
        const tfStatus = await api('/devices/tf-rack/status');
        document.getElementById('home-tf-status').textContent = tfStatus.connected ? 'Connected' : 'Disconnected';
        document.getElementById('home-tf-status').className = `status-value ${tfStatus.connected ? 'online' : 'offline'}`;
        document.getElementById('home-tf-details').textContent = tfStatus.connected ?
            `TF-Rack @ ${tfStatus.ip_address || 'Unknown'}:${tfStatus.port || 49280}` : 'Not connected';
        document.getElementById('tf-status').className = `status-dot ${tfStatus.connected ? 'online' : 'offline'}`;
    } catch (e) {
        document.getElementById('home-tf-status').textContent = 'Disconnected';
        document.getElementById('home-tf-status').className = 'status-value offline';
    }

    // Dante Devices
    try {
        const devices = await api('/devices/dante');
        const count = devices.length || 0;
        document.getElementById('home-dante-status').textContent = `${count} Device${count !== 1 ? 's' : ''}`;
        document.getElementById('home-dante-status').className = `status-value ${count > 0 ? 'online' : ''}`;

        const grid = document.getElementById('home-dante-devices');
        grid.innerHTML = devices.map(d => `
            <div class="device-card">
                <h4>${d.name || 'Unknown'}</h4>
                <div class="device-info">
                    <div>Model: ${d.model || 'N/A'}</div>
                    <div>IP: ${d.ip || 'N/A'}</div>
                    <div>Channels: ${d.input_channels || 0}in / ${d.output_channels || 0}out</div>
                </div>
            </div>
        `).join('') || '<p class="placeholder-text">No Dante devices found</p>';
    } catch (e) {
        document.getElementById('home-dante-status').textContent = 'Unavailable';
    }

    // E-Ink Status
    try {
        const eink = await api('/eink/status');
        const connected = eink.displays?.filter(d => d.connected).length || 0;
        const total = eink.displays?.length || 16;
        document.getElementById('home-eink-status').textContent = `${connected}/${total} Connected`;
        document.getElementById('home-eink-status').className = `status-value ${connected > 0 ? 'online' : ''}`;
    } catch (e) {
        document.getElementById('home-eink-status').textContent = 'Unavailable';
    }
}

// ============== MIXER ==============
async function loadChannels() {
    try {
        const channels = await api('/channels/');
        state.channels = channels;
        renderInputsOutputs();
    } catch (e) {
        document.getElementById('inputs-grid').innerHTML = '<p class="placeholder-text">Failed to load channels</p>';
    }
}

function renderInputsOutputs() {
    // Render Input Channels
    const inputsContainer = document.getElementById('inputs-grid');
    if (inputsContainer) {
        const inputs = state.channels.filter(c => (c.channel_number || c.number) <= 32);

        if (inputs.length === 0) {
            // Create placeholder inputs if none exist
            let html = '';
            for (let i = 1; i <= 32; i++) {
                html += `
                    <div class="input-item unused">
                        <div class="ch-number">CH ${i}</div>
                        <div class="ch-name">---</div>
                    </div>
                `;
            }
            inputsContainer.innerHTML = html;
        } else {
            inputsContainer.innerHTML = inputs.map(ch => {
                const chNum = ch.channel_number || ch.number;
                const hasName = ch.name && ch.name !== `CH ${chNum}`;
                return `
                    <div class="input-item ${hasName ? 'has-signal' : 'unused'}">
                        <div class="ch-number">CH ${chNum}</div>
                        <div class="ch-name">${ch.name || '---'}</div>
                    </div>
                `;
            }).join('');
        }
    }

    // Render Output Buses
    const outputsContainer = document.getElementById('outputs-grid');
    if (outputsContainer) {
        // TF-Rack has: Stereo Out, 20 Aux buses, 4 Matrix outputs
        const outputs = [
            { name: 'STEREO L/R', type: 'main' },
            { name: 'AUX 1', type: 'aux' },
            { name: 'AUX 2', type: 'aux' },
            { name: 'AUX 3', type: 'aux' },
            { name: 'AUX 4', type: 'aux' },
            { name: 'AUX 5', type: 'aux' },
            { name: 'AUX 6', type: 'aux' },
            { name: 'AUX 7', type: 'aux' },
            { name: 'AUX 8', type: 'aux' },
            { name: 'AUX 9/10', type: 'aux' },
            { name: 'AUX 11/12', type: 'aux' },
            { name: 'AUX 13/14', type: 'aux' },
            { name: 'AUX 15/16', type: 'aux' },
            { name: 'AUX 17/18', type: 'aux' },
            { name: 'AUX 19/20', type: 'aux' },
            { name: 'MATRIX 1', type: 'matrix' },
            { name: 'MATRIX 2', type: 'matrix' },
            { name: 'MATRIX 3', type: 'matrix' },
            { name: 'MATRIX 4', type: 'matrix' },
        ];

        outputsContainer.innerHTML = outputs.map(out => `
            <div class="output-item">
                <div class="ch-number">${out.type.toUpperCase()}</div>
                <div class="ch-name">${out.name}</div>
            </div>
        `).join('');
    }
}

async function syncInputsFromTF() {
    try {
        const result = await api('/scenes/sync-from-tf', { method: 'POST' });
        alert(`Sync complete! ${result.channels_updated} channels updated from TF-Rack.`);
        loadChannels();
    } catch (e) {
        alert('Failed to sync from TF-Rack: ' + e.message);
    }
}

// Legacy function stub for compatibility
function renderChannelStrips() { renderInputsOutputs(); }

// ============== SCENES ==============
async function loadScenes() {
    try {
        state.scenes = await api('/scenes/');
        renderScenesList();
    } catch (e) {
        document.getElementById('scenes-list').innerHTML = '<p class="placeholder-text">Failed to load scenes</p>';
    }
}

async function syncFromTFRack() {
    try {
        const result = await api('/scenes/sync-from-tf', { method: 'POST' });
        alert(`Sync complete! ${result.channels_updated} channels updated from TF-Rack.`);
        loadChannels(); // Refresh channel data
    } catch (e) {
        alert('Failed to sync from TF-Rack: ' + e.message);
    }
}

async function pushToTFRack() {
    if (!confirm('Push all current channel settings to TF-Rack?')) return;
    try {
        const result = await api('/channels/push-to-tf', { method: 'POST' });
        alert(`Push complete! ${result.channels_pushed} channels sent to TF-Rack.`);
    } catch (e) {
        alert('Failed to push to TF-Rack: ' + e.message);
    }
}

// ========== TF-Rack Scene Recall ==========

async function recallTFScene() {
    const bank = document.getElementById('tf-scene-bank').value;
    const scene = parseInt(document.getElementById('tf-scene-number').value);
    await recallTFSceneQuick(bank, scene);
}

async function recallTFSceneQuick(bank, scene) {
    const statusEl = document.getElementById('tf-scene-status');
    statusEl.textContent = `Recalling ${bank.toUpperCase()}-${scene}...`;
    statusEl.style.color = 'var(--text-muted)';

    try {
        const result = await api('/devices/tf-rack/recall-scene', {
            method: 'POST',
            body: JSON.stringify({ bank: bank, scene: scene })
        });
        statusEl.textContent = `✓ Recalled ${bank.toUpperCase()}-${scene}`;
        statusEl.style.color = 'var(--accent-green)';
        setTimeout(() => { statusEl.textContent = ''; }, 3000);
    } catch (e) {
        statusEl.textContent = `✗ Failed: ${e.message}`;
        statusEl.style.color = 'var(--accent-red)';
    }
}

function renderScenesList() {
    const container = document.getElementById('scenes-list');
    container.innerHTML = state.scenes.map(s => `
        <div class="scene-item ${state.selectedScene?.id === s.id ? 'selected' : ''}"
             onclick="selectScene(${s.id})">
            <h4>${s.name || `Scene ${s.scene_number}`}</h4>
            <div class="scene-num">Scene ${s.scene_number} • Fade: ${s.fade_time || 0}s</div>
        </div>
    `).join('') || '<p class="placeholder-text">No scenes created</p>';
}

async function selectScene(id) {
    state.selectedScene = state.scenes.find(s => s.id === id);
    renderScenesList();
    renderSceneDetails();
}

function renderSceneDetails() {
    const container = document.getElementById('scene-details');
    const s = state.selectedScene;
    if (!s) {
        container.innerHTML = '<p class="placeholder-text">Select a scene to view details</p>';
        return;
    }
    container.innerHTML = `
        <h3>${s.name || `Scene ${s.scene_number}`}</h3>
        <div class="form-group">
            <label>Scene Number</label>
            <div>${s.scene_number}</div>
        </div>
        <div class="form-group">
            <label>Fade Time</label>
            <div>${s.fade_time || 0} seconds</div>
        </div>
        <div class="form-group">
            <label>Description</label>
            <div>${s.description || 'No description'}</div>
        </div>
        <div class="form-actions">
            <button class="btn btn-success" onclick="recallScene(${s.id})">Recall</button>
            <button class="btn btn-primary" onclick="storeScene(${s.id})">Store</button>
            <button class="btn btn-danger" onclick="deleteScene(${s.id})">Delete</button>
        </div>
    `;
}

async function recallScene(id) {
    try {
        await api(`/scenes/${id}/recall`, { method: 'POST' });
        alert('Scene recalled successfully');
    } catch (e) {
        alert('Failed to recall scene: ' + e.message);
    }
}

async function storeScene(id) {
    try {
        await api(`/scenes/${id}/store`, { method: 'POST' });
        alert('Scene stored successfully');
    } catch (e) {
        alert('Failed to store scene: ' + e.message);
    }
}

async function deleteScene(id) {
    if (!confirm('Delete this scene?')) return;
    try {
        await api(`/scenes/${id}`, { method: 'DELETE' });
        state.selectedScene = null;
        loadScenes();
    } catch (e) {
        alert('Failed to delete scene: ' + e.message);
    }
}

function showCreateSceneModal() {
    const nextNum = (state.scenes.length > 0 ? Math.max(...state.scenes.map(s => s.scene_number)) : 0) + 1;
    showModal('Create Scene', `
        <div class="form-group">
            <label>Scene Number</label>
            <input type="number" id="scene-number" class="input" value="${nextNum}" min="1" max="200">
        </div>
        <div class="form-group">
            <label>Name</label>
            <input type="text" id="scene-name" class="input" placeholder="Scene name">
        </div>
        <div class="form-group">
            <label>Fade Time (seconds)</label>
            <input type="number" id="scene-fade" class="input" value="0" min="0" max="60" step="0.5">
        </div>
        <div class="form-group">
            <label>Description</label>
            <textarea id="scene-desc" class="input" placeholder="Optional description"></textarea>
        </div>
        <div class="form-actions">
            <button class="btn btn-primary" onclick="createScene()">Create</button>
            <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        </div>
    `);
}

async function createScene() {
    const data = {
        scene_number: parseInt(document.getElementById('scene-number').value),
        name: document.getElementById('scene-name').value,
        fade_time: parseFloat(document.getElementById('scene-fade').value),
        description: document.getElementById('scene-desc').value
    };
    try {
        await api('/scenes/', { method: 'POST', body: JSON.stringify(data) });
        closeModal();
        loadScenes();
    } catch (e) {
        alert('Failed to create scene: ' + e.message);
    }
}

// ============== SHOWS ==============
async function loadShows() {
    try {
        const [shows, bands] = await Promise.all([
            api('/shows/'),
            api('/shows/bands').catch(() => [])
        ]);
        state.shows = shows;
        state.bands = bands;
        renderShowsList();
    } catch (e) {
        document.getElementById('shows-list').innerHTML = '<p class="placeholder-text">Failed to load shows</p>';
    }
}

function renderShowsList() {
    const container = document.getElementById('shows-list');
    container.innerHTML = state.shows.map(s => `
        <div class="show-item ${state.selectedShow?.id === s.id ? 'selected' : ''}"
             onclick="selectShow(${s.id})">
            <h4>${s.name}</h4>
            <div class="venue">${s.venue || 'No venue'}</div>
        </div>
    `).join('') || '<p class="placeholder-text">No shows created</p>';
}

async function selectShow(id) {
    state.selectedShow = state.shows.find(s => s.id === id);
    renderShowsList();
    await renderShowDetails();
}

async function renderShowDetails() {
    const container = document.getElementById('show-details');
    const s = state.selectedShow;
    if (!s) {
        container.innerHTML = '<p class="placeholder-text">Select a show to view details</p>';
        return;
    }

    let showBands = [];
    try {
        showBands = await api(`/shows/${s.id}/bands`);
    } catch (e) {}

    container.innerHTML = `
        <h3>${s.name}</h3>
        <div class="form-group">
            <label>Venue</label>
            <div>${s.venue || 'Not set'}</div>
        </div>
        <div class="form-group">
            <label>Date</label>
            <div>${s.date || 'Not set'}</div>
        </div>
        <h4>Bands</h4>
        <div class="bands-list">
            ${showBands.map(b => `
                <div class="device-item">
                    <div>
                        <div class="device-name">${b.name}</div>
                        <div class="device-ip">${b.genre || 'No genre'}</div>
                    </div>
                    <button class="btn btn-sm btn-danger" onclick="removeBandFromShow(${s.id}, ${b.id})">Remove</button>
                </div>
            `).join('') || '<p class="placeholder-text">No bands assigned</p>'}
        </div>
        <div class="form-actions">
            <button class="btn btn-primary" onclick="showAddBandModal(${s.id})">Add Band</button>
            <button class="btn btn-danger" onclick="deleteShow(${s.id})">Delete Show</button>
        </div>
    `;
}

async function deleteShow(id) {
    if (!confirm('Delete this show?')) return;
    try {
        await api(`/shows/${id}`, { method: 'DELETE' });
        state.selectedShow = null;
        loadShows();
    } catch (e) {
        alert('Failed to delete show: ' + e.message);
    }
}

function showCreateShowModal() {
    showModal('Create Show', `
        <div class="form-group">
            <label>Name</label>
            <input type="text" id="show-name" class="input" placeholder="Show name">
        </div>
        <div class="form-group">
            <label>Venue</label>
            <input type="text" id="show-venue" class="input" placeholder="Venue name">
        </div>
        <div class="form-group">
            <label>Date</label>
            <input type="date" id="show-date" class="input">
        </div>
        <div class="form-actions">
            <button class="btn btn-primary" onclick="createShow()">Create</button>
            <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        </div>
    `);
}

async function createShow() {
    const data = {
        name: document.getElementById('show-name').value,
        venue: document.getElementById('show-venue').value,
        date: document.getElementById('show-date').value || null
    };
    try {
        await api('/shows/', { method: 'POST', body: JSON.stringify(data) });
        closeModal();
        loadShows();
    } catch (e) {
        alert('Failed to create show: ' + e.message);
    }
}

// ============== ARTISTS ==============
async function loadArtists() {
    try {
        state.artists = await api('/shows/artists');
        renderArtistsGrid();
    } catch (e) {
        document.getElementById('artists-grid').innerHTML = '<p class="placeholder-text">Failed to load artists</p>';
    }
}

function renderArtistsGrid() {
    const container = document.getElementById('artists-grid');
    container.innerHTML = state.artists.map(a => `
        <div class="artist-card">
            <div class="artist-avatar">
                ${a.image_url ? `<img src="${a.image_url}" alt="${a.name}">` : a.name?.charAt(0) || '?'}
            </div>
            <div class="artist-info">
                <h4>${a.name}</h4>
                <div class="instrument">${a.instrument || 'No instrument'}</div>
                <div class="artist-details">
                    ${a.microphone ? `Mic: ${a.microphone}` : ''}<br>
                    ${a.iem_system ? `IEM: ${a.iem_system}` : ''}
                </div>
                <div class="form-actions" style="margin-top: 0.5rem;">
                    <button class="btn btn-sm btn-secondary" onclick="editArtist(${a.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteArtist(${a.id})">Delete</button>
                </div>
            </div>
        </div>
    `).join('') || '<p class="placeholder-text">No artists created</p>';
}

async function deleteArtist(id) {
    if (!confirm('Delete this artist?')) return;
    try {
        await api(`/shows/artists/${id}`, { method: 'DELETE' });
        loadArtists();
    } catch (e) {
        alert('Failed to delete artist: ' + e.message);
    }
}

function showCreateArtistModal() {
    showModal('Create Artist', `
        <div class="form-group">
            <label>Name</label>
            <input type="text" id="artist-name" class="input" placeholder="Artist name">
        </div>
        <div class="form-group">
            <label>Instrument</label>
            <select id="artist-instrument" class="input">
                <option value="">Select instrument</option>
                <option value="Lead Vocals">Lead Vocals</option>
                <option value="Backup Vocals">Backup Vocals</option>
                <option value="Electric Guitar">Electric Guitar</option>
                <option value="Acoustic Guitar">Acoustic Guitar</option>
                <option value="Bass">Bass</option>
                <option value="Drums">Drums</option>
                <option value="Keyboards">Keyboards</option>
                <option value="Saxophone">Saxophone</option>
                <option value="Trumpet">Trumpet</option>
                <option value="Violin">Violin</option>
                <option value="Other">Other</option>
            </select>
        </div>
        <div class="form-group">
            <label>Microphone</label>
            <select id="artist-mic" class="input">
                <option value="">Select microphone</option>
                <option value="Shure SM58">Shure SM58</option>
                <option value="Shure Beta 58A">Shure Beta 58A</option>
                <option value="Shure SM7B">Shure SM7B</option>
                <option value="Sennheiser e935">Sennheiser e935</option>
                <option value="Sennheiser e945">Sennheiser e945</option>
                <option value="Audio-Technica AE6100">Audio-Technica AE6100</option>
            </select>
        </div>
        <div class="form-group">
            <label>IEM System</label>
            <select id="artist-iem" class="input">
                <option value="">Select IEM</option>
                <option value="Shure PSM300">Shure PSM300</option>
                <option value="Shure PSM900">Shure PSM900</option>
                <option value="Shure PSM1000">Shure PSM1000</option>
                <option value="Sennheiser EW IEM G4">Sennheiser EW IEM G4</option>
                <option value="Audio-Technica M3">Audio-Technica M3</option>
            </select>
        </div>
        <div class="form-group">
            <label>E-Ink Label (max 12 chars)</label>
            <input type="text" id="artist-eink" class="input" maxlength="12" placeholder="Label text">
        </div>
        <div class="form-actions">
            <button class="btn btn-primary" onclick="createArtist()">Create</button>
            <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        </div>
    `);
}

async function createArtist() {
    const data = {
        name: document.getElementById('artist-name').value,
        instrument: document.getElementById('artist-instrument').value,
        microphone: document.getElementById('artist-mic').value,
        iem_system: document.getElementById('artist-iem').value,
        eink_label: document.getElementById('artist-eink').value
    };
    try {
        await api('/shows/artists', { method: 'POST', body: JSON.stringify(data) });
        closeModal();
        loadArtists();
    } catch (e) {
        alert('Failed to create artist: ' + e.message);
    }
}

// ============== SONGS ==============
async function loadSongs() {
    try {
        state.songs = await api('/songs/');
        renderSongsList();
    } catch (e) {
        document.getElementById('songs-list').innerHTML = '<p class="placeholder-text">Failed to load songs</p>';
    }
}

function renderSongsList() {
    const container = document.getElementById('songs-list');
    const search = document.getElementById('song-search')?.value?.toLowerCase() || '';
    const filtered = state.songs.filter(s =>
        s.title?.toLowerCase().includes(search) ||
        s.artist?.toLowerCase().includes(search)
    );

    container.innerHTML = filtered.map(s => `
        <div class="song-item ${state.selectedSong?.id === s.id ? 'selected' : ''}"
             onclick="selectSong(${s.id})">
            <h4>${s.title}</h4>
            <div class="artist">${s.artist || 'Unknown artist'} • ${s.key || 'No key'}</div>
        </div>
    `).join('') || '<p class="placeholder-text">No songs found</p>';
}

async function selectSong(id) {
    state.selectedSong = state.songs.find(s => s.id === id);
    renderSongsList();
    await renderSongDetails();
}

async function renderSongDetails() {
    const container = document.getElementById('song-details');
    const s = state.selectedSong;
    if (!s) {
        container.innerHTML = '<p class="placeholder-text">Select a song to view details</p>';
        return;
    }

    let chart = '';
    try {
        const chartData = await api(`/songs/${s.id}/chart`);
        chart = chartData.chart || chartData.content || 'No chord chart';
    } catch (e) {
        chart = 'No chord chart available';
    }

    container.innerHTML = `
        <h3>${s.title}</h3>
        <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
            <div><strong>Artist:</strong> ${s.artist || 'Unknown'}</div>
            <div><strong>Key:</strong> ${s.key || 'N/A'}</div>
            <div><strong>Tempo:</strong> ${s.tempo || 'N/A'} BPM</div>
        </div>
        <h4>Chord Chart</h4>
        <div class="chord-chart">${formatChordChart(chart)}</div>
        <div class="form-actions">
            <button class="btn btn-secondary" onclick="transposeSong(${s.id})">Transpose</button>
            <button class="btn btn-secondary" onclick="printSong(${s.id})">Print</button>
            <button class="btn btn-danger" onclick="deleteSong(${s.id})">Delete</button>
        </div>
    `;
}

function formatChordChart(text) {
    return text
        .replace(/\[([A-G][#b]?m?(?:maj|min|dim|aug|sus|add|7|9|11|13)?(?:\/[A-G][#b]?)?)\]/g, '<span class="chord">[$1]</span>')
        .replace(/^\{([^}]+)\}/gm, '<span class="section">{$1}</span>')
        .replace(/\n/g, '<br>');
}

async function deleteSong(id) {
    if (!confirm('Delete this song?')) return;
    try {
        await api(`/songs/${id}`, { method: 'DELETE' });
        state.selectedSong = null;
        loadSongs();
    } catch (e) {
        alert('Failed to delete song: ' + e.message);
    }
}

function showCreateSongModal() {
    showModal('Create Song', `
        <div class="form-group">
            <label>Title</label>
            <input type="text" id="song-title" class="input" placeholder="Song title">
        </div>
        <div class="form-group">
            <label>Artist</label>
            <input type="text" id="song-artist" class="input" placeholder="Artist name">
        </div>
        <div class="form-group">
            <label>Key</label>
            <select id="song-key" class="input">
                <option value="">Select key</option>
                <option value="C">C Major</option>
                <option value="G">G Major</option>
                <option value="D">D Major</option>
                <option value="A">A Major</option>
                <option value="E">E Major</option>
                <option value="F">F Major</option>
                <option value="Bb">Bb Major</option>
                <option value="Am">A Minor</option>
                <option value="Em">E Minor</option>
                <option value="Dm">D Minor</option>
            </select>
        </div>
        <div class="form-group">
            <label>Tempo (BPM)</label>
            <input type="number" id="song-tempo" class="input" placeholder="120">
        </div>
        <div class="form-group">
            <label>Chord Chart (ChordPro format)</label>
            <textarea id="song-chart" class="input" rows="6" placeholder="{Verse 1}
[G]Amazing [D]grace, how [G]sweet the sound"></textarea>
        </div>
        <div class="form-actions">
            <button class="btn btn-primary" onclick="createSong()">Create</button>
            <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        </div>
    `);
}

async function createSong() {
    const data = {
        title: document.getElementById('song-title').value,
        artist: document.getElementById('song-artist').value,
        key: document.getElementById('song-key').value,
        tempo: parseInt(document.getElementById('song-tempo').value) || null,
        chord_chart: document.getElementById('song-chart').value
    };
    try {
        await api('/songs/', { method: 'POST', body: JSON.stringify(data) });
        closeModal();
        loadSongs();
    } catch (e) {
        alert('Failed to create song: ' + e.message);
    }
}

// Song search
document.getElementById('song-search')?.addEventListener('input', renderSongsList);

// ============== PATCHES ==============
async function loadPatches() {
    try {
        const matrix = await api('/patches/matrix');
        state.patches = matrix.patches || matrix;
        renderPatchMatrix();
    } catch (e) {
        document.getElementById('patch-matrix').innerHTML = '<p class="placeholder-text">Failed to load patches</p>';
    }
}

function renderPatchMatrix() {
    const container = document.getElementById('patch-matrix');
    const cells = [];

    for (let i = 1; i <= 32; i++) {
        const patch = state.patches.find(p => p.destination_channel === i);
        const type = patch?.source_type || 'none';
        cells.push(`
            <div class="patch-cell ${type}">
                <div class="channel-num">IN ${i}</div>
                <div class="source">${patch?.source_name || 'Unpatched'}</div>
                <div class="source-type">${type !== 'none' ? type.toUpperCase() : ''}</div>
            </div>
        `);
    }

    container.innerHTML = cells.join('');
}

function showQuickPatchModal() {
    showModal('Quick Patch', `
        <div class="form-group">
            <label>Source Type</label>
            <select id="patch-type" class="input">
                <option value="analog">Analog (Local)</option>
                <option value="dante">Dante (Network)</option>
            </select>
        </div>
        <div class="form-group">
            <label>Source Input</label>
            <input type="number" id="patch-source" class="input" min="1" max="32" value="1">
        </div>
        <div class="form-group">
            <label>Destination Channel</label>
            <input type="number" id="patch-dest" class="input" min="1" max="32" value="1">
        </div>
        <div class="form-actions">
            <button class="btn btn-primary" onclick="createPatch()">Create Patch</button>
            <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        </div>
    `);
}

async function createPatch() {
    const data = {
        source_type: document.getElementById('patch-type').value,
        source_input: parseInt(document.getElementById('patch-source').value),
        destination_channel: parseInt(document.getElementById('patch-dest').value)
    };
    try {
        await api('/patches/quick-patch', { method: 'POST', body: JSON.stringify(data) });
        closeModal();
        loadPatches();
    } catch (e) {
        alert('Failed to create patch: ' + e.message);
    }
}

async function autoPatcTIO() {
    try {
        await api('/patches/auto-patch-tio', { method: 'POST' });
        loadPatches();
        alert('TIO auto-patched successfully');
    } catch (e) {
        alert('Failed to auto-patch TIO: ' + e.message);
    }
}

// ============== DEVICES ==============
async function loadDevices() {
    try {
        const [tfStatus, danteDevices] = await Promise.all([
            api('/devices/tf-rack/status'),
            api('/devices/dante')
        ]);

        document.getElementById('tf-rack-info').innerHTML = tfStatus.connected ? `
            <div class="device-item">
                <div>
                    <div class="device-name">${tfStatus.model || 'TF-Rack'}</div>
                    <div class="device-ip">${tfStatus.ip}:${tfStatus.port}</div>
                </div>
                <div class="device-status online">Connected</div>
            </div>
        ` : '<p>Not connected</p>';

        document.getElementById('dante-devices-list').innerHTML = danteDevices.map(d => `
            <div class="device-item">
                <div>
                    <div class="device-name">${d.name}</div>
                    <div class="device-ip">${d.model || 'Unknown'} • ${d.ip_address || 'manual'} • ${d.input_channels || 0}in/${d.output_channels || 0}out</div>
                </div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <div class="device-status ${d.is_online ? 'online' : 'offline'}">${d.is_online ? 'Online' : 'Offline'}</div>
                    <button class="btn btn-sm btn-danger" onclick="removeDanteDevice('${d.name.replace(/'/g, "\\'")}')">×</button>
                </div>
            </div>
        `).join('') || '<p class="placeholder-text">No Dante devices found. Click "Add Device" to manually add devices.</p>';
    } catch (e) {
        console.error('Failed to load devices', e);
    }
}

async function connectTFRack() {
    const ip = document.getElementById('tf-ip').value;
    const port = parseInt(document.getElementById('tf-port').value);
    try {
        await api(`/devices/tf-rack/connect?ip_address=${encodeURIComponent(ip)}&port=${port}`, {
            method: 'POST'
        });
        loadDevices();
        loadDashboard();
    } catch (e) {
        alert('Failed to connect: ' + e.message);
    }
}

async function disconnectTFRack() {
    try {
        await api('/devices/tf-rack/disconnect', { method: 'POST' });
        loadDevices();
        loadDashboard();
    } catch (e) {
        alert('Failed to disconnect: ' + e.message);
    }
}

async function refreshDevices() {
    try {
        await api('/devices/dante/refresh', { method: 'POST' });
        loadDevices();
    } catch (e) {
        console.error('Failed to refresh', e);
    }
}

function showAddDanteDeviceModal() {
    showModal('Add Dante Device', `
        <p style="margin-bottom: 1rem; color: #888;">Manually add Dante devices when auto-discovery doesn't work (e.g., devices on a separate network adapter).</p>
        <div class="form-group">
            <label>Device Name</label>
            <input type="text" id="dante-name" class="input" placeholder="e.g., Y001-Yamaha-Tio1608-D-28f094">
        </div>
        <div class="form-group">
            <label>Model</label>
            <select id="dante-model" class="input">
                <option value="TIO-1608-D">Yamaha TIO-1608-D</option>
                <option value="NY64-D">Yamaha NY64-D</option>
                <option value="Rio3224-D2">Yamaha Rio3224-D2</option>
                <option value="Rio1608-D2">Yamaha Rio1608-D2</option>
                <option value="Other">Other</option>
            </select>
        </div>
        <div class="form-group">
            <label>Input Channels</label>
            <input type="number" id="dante-inputs" class="input" value="16" min="0" max="64">
        </div>
        <div class="form-group">
            <label>Output Channels</label>
            <input type="number" id="dante-outputs" class="input" value="8" min="0" max="64">
        </div>
        <div class="form-actions">
            <button class="btn btn-primary" onclick="addManualDanteDevice()">Add Device</button>
            <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        </div>
    `);
}

async function addManualDanteDevice() {
    const data = {
        name: document.getElementById('dante-name').value,
        model: document.getElementById('dante-model').value,
        input_channels: parseInt(document.getElementById('dante-inputs').value),
        output_channels: parseInt(document.getElementById('dante-outputs').value)
    };

    if (!data.name) {
        alert('Please enter a device name');
        return;
    }

    try {
        await api('/devices/dante/manual', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        closeModal();
        loadDevices();
        loadDashboard();
    } catch (e) {
        alert('Failed to add device: ' + e.message);
    }
}

async function removeDanteDevice(deviceName) {
    if (!confirm(`Remove device "${deviceName}"?`)) return;
    try {
        await api(`/devices/dante/${encodeURIComponent(deviceName)}`, { method: 'DELETE' });
        loadDevices();
        loadDashboard();
    } catch (e) {
        alert('Failed to remove device: ' + e.message);
    }
}

// ============== BACKSTAGE ==============
async function loadBackstage() {
    try {
        const [backstage, wireless] = await Promise.all([
            api('/backstage/current'),
            api('/backstage/wireless-overview')
        ]);

        const grid = document.getElementById('backstage-grid');
        grid.innerHTML = (backstage.artists || []).map(a => `
            <div class="backstage-card">
                <div class="artist-photo">${a.image_url ? `<img src="${a.image_url}">` : a.name?.charAt(0) || '?'}</div>
                <h4>${a.name}</h4>
                <div class="instrument">${a.instrument || ''}</div>
                <div class="wireless-info">
                    <div class="battery-indicator ${getBatteryClass(a.battery)}">${a.battery || '?'}%</div>
                    <div class="rf-bars">
                        ${[1,2,3,4,5].map(i => `<div class="rf-bar ${i <= (a.rf_level || 0) ? 'active' : ''}"></div>`).join('')}
                    </div>
                </div>
            </div>
        `).join('') || '<p class="placeholder-text">No artists in current show</p>';

        const tbody = document.querySelector('#wireless-table tbody');
        tbody.innerHTML = (wireless.devices || []).map(d => `
            <tr>
                <td>${d.channel || 'N/A'}</td>
                <td>${d.artist || 'Unassigned'}</td>
                <td>${d.device || 'Unknown'}</td>
                <td class="${getBatteryClass(d.battery)}">${d.battery || '?'}%</td>
                <td>
                    <div class="rf-bars">
                        ${[1,2,3,4,5].map(i => `<div class="rf-bar ${i <= (d.rf_level || 0) ? 'active' : ''}"></div>`).join('')}
                    </div>
                </td>
            </tr>
        `).join('') || '<tr><td colspan="5" class="placeholder-text">No wireless devices</td></tr>';
    } catch (e) {
        console.error('Failed to load backstage', e);
    }
}

function getBatteryClass(level) {
    if (level > 50) return 'high';
    if (level > 20) return 'medium';
    return 'low';
}

function toggleFullscreen() {
    if (document.fullscreenElement) {
        document.exitFullscreen();
    } else {
        document.getElementById('page-backstage').requestFullscreen();
    }
}

// ============== E-INK ==============
async function loadEinkDisplays() {
    try {
        const status = await api('/eink/status');
        state.einkDisplays = status.displays || [];
        renderEinkGrid();
    } catch (e) {
        document.getElementById('eink-grid').innerHTML = '<p class="placeholder-text">Failed to load E-Ink displays</p>';
    }
}

function renderEinkGrid() {
    const container = document.getElementById('eink-grid');
    const displays = state.einkDisplays.length > 0 ? state.einkDisplays :
        Array.from({length: 16}, (_, i) => ({ index: i, text: '', connected: false }));

    container.innerHTML = displays.map((d, i) => `
        <div class="eink-display">
            <div class="channel-num">CH ${i + 1}</div>
            <div class="eink-screen">${d.text || '---'}</div>
            <div class="status ${d.connected ? 'connected' : 'disconnected'}">
                ${d.connected ? 'Connected' : 'Not connected'}
            </div>
            <input type="text" class="input" maxlength="12" value="${d.text || ''}"
                   onchange="updateEinkDisplay(${i}, this.value)" placeholder="Label">
        </div>
    `).join('');
}

async function updateEinkDisplay(index, text) {
    try {
        await api(`/eink/${index}/update`, {
            method: 'POST',
            body: JSON.stringify({ text })
        });
    } catch (e) {
        console.error('Failed to update E-Ink', e);
    }
}

async function syncFromChannels() {
    try {
        const channels = await api('/channels/');
        const updates = channels.slice(0, 16).map((ch, i) => ({
            index: i,
            text: (ch.name || `CH ${ch.number}`).substring(0, 12)
        }));
        await api('/eink/bulk-update', {
            method: 'POST',
            body: JSON.stringify({ displays: updates })
        });
        loadEinkDisplays();
    } catch (e) {
        alert('Failed to sync: ' + e.message);
    }
}

async function refreshEink() {
    try {
        await api('/eink/refresh', { method: 'POST' });
        loadEinkDisplays();
    } catch (e) {
        alert('Failed to refresh: ' + e.message);
    }
}

async function testPatternEink() {
    try {
        await api('/eink/test-pattern', { method: 'POST' });
    } catch (e) {
        alert('Failed to show test pattern: ' + e.message);
    }
}

// ============== SETTINGS ==============
async function loadSettings() {
    try {
        const health = await api('/health');
        document.getElementById('system-info').innerHTML = `
            <div>Version <span>${health.version || '1.0.0'}</span></div>
            <div>API Status <span>${health.status || 'running'}</span></div>
            <div>TF-Rack <span>${health.tf_rack_connected ? 'Connected' : 'Disconnected'}</span></div>
            <div>Database <span>${health.database || 'SQLite'}</span></div>
        `;
    } catch (e) {
        document.getElementById('system-info').innerHTML = '<p>Failed to load system info</p>';
    }
}

// ============== MODAL ==============
function showModal(title, content) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = content;
    document.getElementById('modal-overlay').classList.add('active');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
}

// Close modal on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// ============== INITIALIZATION ==============
document.addEventListener('DOMContentLoaded', () => {
    showPage('home');

    // Refresh dashboard periodically
    setInterval(() => {
        const activePage = document.querySelector('.page.active')?.id;
        if (activePage === 'page-home') loadDashboard();
        if (activePage === 'page-backstage') loadBackstage();
    }, 5000);
});
