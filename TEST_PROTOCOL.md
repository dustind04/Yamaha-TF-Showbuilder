# Yamaha TF Showbuilder - Test Protocol & Release Matrix

## Test Environment Checklist

### Prerequisites
- [ ] Docker & Docker Compose installed
- [ ] Node.js 18+ (for local frontend dev)
- [ ] Python 3.11+ (for local backend dev)
- [ ] Network access to TF-Rack (if available)
- [ ] Dante network configured (if testing TIO devices)

---

## Phase 1: Infrastructure Tests

### 1.1 Docker Build
| Test | Command | Expected Result | Status |
|------|---------|-----------------|--------|
| Backend builds | `docker-compose build backend` | Image created, no errors | ⬜ |
| Frontend builds | `docker-compose build frontend` | Image created, no errors | ⬜ |
| Full stack starts | `docker-compose up -d` | All containers running | ⬜ |

### 1.2 Service Health
| Test | Endpoint/Command | Expected Result | Status |
|------|------------------|-----------------|--------|
| Backend responds | `curl http://localhost:8000/` | JSON with name/version | ⬜ |
| Health check | `curl http://localhost:8000/health` | status: healthy | ⬜ |
| Frontend loads | `curl http://localhost:3000/` | HTML page | ⬜ |
| API docs | `curl http://localhost:8000/docs` | Swagger UI | ⬜ |

---

## Phase 2: Backend API Tests

### 2.1 Channel API
| Test | Method | Endpoint | Expected | Status |
|------|--------|----------|----------|--------|
| List channels | GET | `/api/channels/` | Array of channels | ⬜ |
| Get channel | GET | `/api/channels/1` | Channel object | ⬜ |
| Update fader | PUT | `/api/channels/1/fader` | Updated level | ⬜ |
| Toggle mute | POST | `/api/channels/1/mute` | Mute toggled | ⬜ |

### 2.2 Scene API
| Test | Method | Endpoint | Expected | Status |
|------|--------|----------|----------|--------|
| List scenes | GET | `/api/scenes/` | Array of scenes | ⬜ |
| Create scene | POST | `/api/scenes/` | New scene created | ⬜ |
| Store scene | POST | `/api/scenes/{id}/store` | Scene stored | ⬜ |
| Recall scene | POST | `/api/scenes/{id}/recall` | Scene recalled | ⬜ |

### 2.3 Show Management API
| Test | Method | Endpoint | Expected | Status |
|------|--------|----------|----------|--------|
| List shows | GET | `/api/shows/` | Array of shows | ⬜ |
| Create show | POST | `/api/shows/` | New show | ⬜ |
| List bands | GET | `/api/bands/` | Array of bands | ⬜ |
| Create band | POST | `/api/bands/` | New band | ⬜ |
| List artists | GET | `/api/artists/` | Array of artists | ⬜ |
| Create artist | POST | `/api/artists/` | New artist | ⬜ |
| Add artist to band | POST | `/api/bands/{id}/artists/{id}` | Association created | ⬜ |

### 2.4 Preset API
| Test | Method | Endpoint | Expected | Status |
|------|--------|----------|----------|--------|
| List presets | GET | `/api/presets/` | Array of presets | ⬜ |
| Init factory | POST | `/api/presets/init-factory` | Presets created | ⬜ |
| Get categories | GET | `/api/presets/categories` | Category list | ⬜ |
| Apply preset | POST | `/api/presets/{id}/apply` | Applied to channel | ⬜ |

### 2.5 Device API
| Test | Method | Endpoint | Expected | Status |
|------|--------|----------|----------|--------|
| List devices | GET | `/api/devices/` | Array of devices | ⬜ |
| TF-Rack status | GET | `/api/devices/tf-rack/status` | Connection status | ⬜ |
| Dante devices | GET | `/api/devices/dante` | Dante device list | ⬜ |

### 2.6 E-Ink API
| Test | Method | Endpoint | Expected | Status |
|------|--------|----------|----------|--------|
| List displays | GET | `/api/eink/` | Array of displays | ⬜ |
| Update label | PUT | `/api/eink/{id}` | Label updated | ⬜ |
| Sync all | POST | `/api/eink/sync` | All displays synced | ⬜ |

### 2.7 WebSocket
| Test | Action | Expected | Status |
|------|--------|----------|--------|
| Connect | ws://localhost:8000/ws/live | Connection accepted | ⬜ |
| Subscribe meters | Send: `{"type":"subscribe","topic":"meters"}` | Meter data stream | ⬜ |
| Get state | Send: `{"type":"get_state"}` | Full state object | ⬜ |

---

## Phase 3: Frontend UI Tests

### 3.1 Navigation
| Page | Route | Components Load | Status |
|------|-------|-----------------|--------|
| Home | `/` | Dashboard cards | ⬜ |
| Mixer | `/mixer` | Channel strips | ⬜ |
| Patch | `/patch` | Patch matrix | ⬜ |
| Scenes | `/scenes` | Scene list | ⬜ |
| Shows | `/shows` | Show management | ⬜ |
| Artists | `/artists` | Artist cards | ⬜ |
| Backstage | `/backstage` | Monitor display | ⬜ |
| Devices | `/devices` | Device status | ⬜ |
| E-Ink | `/eink` | Display grid | ⬜ |
| Settings | `/settings` | Config forms | ⬜ |

### 3.2 Interactive Features
| Feature | Action | Expected | Status |
|---------|--------|----------|--------|
| Fader drag | Drag channel fader | Level updates | ⬜ |
| Mute toggle | Click mute button | Channel mutes | ⬜ |
| Scene recall | Click recall button | Scene loads | ⬜ |
| Create show | Fill form, submit | Show created | ⬜ |
| Create band | Fill form, submit | Band created | ⬜ |
| Add artist | Fill form, submit | Artist created | ⬜ |
| Apply preset | Select preset, apply | Channel configured | ⬜ |

---

## Phase 4: Integration Tests

### 4.1 TF-Rack Integration (requires hardware)
| Test | Action | Expected | Status |
|------|--------|----------|--------|
| Connection | Configure IP, connect | Connected status | ⬜ |
| Fader sync | Move fader in app | TF-Rack fader moves | ⬜ |
| Mute sync | Mute in app | TF-Rack channel mutes | ⬜ |
| Scene recall | Recall scene | TF-Rack loads scene | ⬜ |
| Bidirectional | Move fader on TF-Rack | App updates | ⬜ |

### 4.2 Dante Integration (requires hardware)
| Test | Action | Expected | Status |
|------|--------|----------|--------|
| Discovery | Start service | Devices discovered | ⬜ |
| TIO-1608-D | Connect TIO box | Device appears | ⬜ |
| Routing | Create patch | Audio routes | ⬜ |

### 4.3 E-Ink Integration (requires hardware)
| Test | Action | Expected | Status |
|------|--------|----------|--------|
| Detection | Connect displays | Displays found | ⬜ |
| Update label | Change channel name | Display updates | ⬜ |
| Scene sync | Recall scene | Labels update | ⬜ |

---

## Phase 5: End-to-End Workflows

### 5.1 Show Setup Workflow
| Step | Action | Verify | Status |
|------|--------|--------|--------|
| 1 | Create new show | Show in list | ⬜ |
| 2 | Create band | Band in list | ⬜ |
| 3 | Add artists to band | Artists linked | ⬜ |
| 4 | Assign input presets | Channels configured | ⬜ |
| 5 | Store scene | Scene saved | ⬜ |
| 6 | Add band to show | Association exists | ⬜ |

### 5.2 Live Show Workflow
| Step | Action | Verify | Status |
|------|--------|--------|--------|
| 1 | Recall band preset | Channels load | ⬜ |
| 2 | E-ink labels update | Names on displays | ⬜ |
| 3 | Adjust monitor mix | AUX sends change | ⬜ |
| 4 | Store updated scene | Changes saved | ⬜ |

---

## Release Checklist

### Pre-Release
- [ ] All Phase 1-3 tests pass
- [ ] No console errors in browser
- [ ] No Python exceptions in logs
- [ ] Database migrations complete
- [ ] Environment variables documented

### Release Candidate
- [ ] Phase 4 tests pass (with hardware)
- [ ] Phase 5 workflows complete
- [ ] Performance acceptable (< 100ms API response)
- [ ] Memory usage stable over 1 hour

### Production Release
- [ ] Security review complete
- [ ] Backup/restore tested
- [ ] Documentation complete
- [ ] Version tagged in git

---

## Issue Tracking

| Issue # | Description | Severity | Status |
|---------|-------------|----------|--------|
| | | | |

---

## Notes

_Add notes during testing here_
