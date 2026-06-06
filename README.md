# Yamaha TF Showbuilder

A comprehensive control system for Yamaha TF-Rack digital mixers with Dante networking, e-ink display labeling, and backstage monitoring capabilities.

## Features

### Mixer Control
- **Full TF-Rack control** via OSC protocol
- Real-time fader, mute, pan control
- 4-band parametric EQ per channel
- Compressor and gate processing
- Aux send management for monitor mixes
- Scene store/recall with fade times

### Dante Integration
- **Automatic device discovery** via mDNS
- TIO-1608-D stage box support
- Audio routing/patching between Dante devices
- Real-time device status monitoring

### E-Ink Display Labels
- Channel labels displayed above physical inputs
- Automatic sync with channel names
- Scene-based label recall
- Support for Waveshare e-paper displays

### Show Management
- **Shows** - Organize events with venue, date, times
- **Bands** - Store channel presets, input lists, technical requirements
- **Artists** - Individual performer preferences, mic/IEM assignments
- **Scenes** - Mixer snapshots with e-ink labels

### Input Presets
- Factory presets for common input types:
  - Vocals (SM58, Beta 87A, ULX-D wireless)
  - Drums (kick, snare, toms, overheads)
  - Guitars (electric, acoustic, DI)
  - Bass (DI, amp)
  - Keys (stereo)
- Custom user presets
- One-click channel configuration

### Backstage Monitor (Micboard-inspired)
- Artist photos and assignments display
- Wireless mic/IEM pack assignments
- Battery level monitoring
- RF signal strength
- Full-screen display mode for green rooms

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Frontend  │────▶│  FastAPI Server │────▶│   TF-Rack       │
│   (React/TS)    │     │   (Python)      │     │   (OSC)         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  Dante Devices  │   │  E-Ink Displays │   │  Database       │
│  (mDNS/AES67)   │   │  (USB)          │   │  (SQLite)       │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Network access to TF-Rack (port 49280)
- Dante devices on same network subnet

### Running with Docker

```bash
# Clone the repository
git clone <repository-url>
cd Yamaha-TF-Showbuilder

# Configure environment
cp .env.example .env
# Edit .env with your TF-Rack IP address

# Start services
docker-compose up -d

# Access the web interface
open http://localhost:3000
```

### Environment Variables

```env
TF_RACK_IP=192.168.1.100      # IP of your TF-Rack
TF_RACK_PORT=49280            # OSC port (default 49280)
DANTE_DISCOVERY_ENABLED=true  # Enable Dante mDNS discovery
EINK_ENABLED=true             # Enable e-ink display support
```

## API Documentation

Once running, access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/channels` | Channel control (faders, EQ, comp, gate) |
| `/api/patches` | Audio routing/patching |
| `/api/scenes` | Scene store/recall |
| `/api/shows` | Show management |
| `/api/bands` | Band presets |
| `/api/artists` | Artist configurations |
| `/api/presets` | Input presets library |
| `/api/eink` | E-ink display control |
| `/api/backstage` | Backstage monitor data |
| `/ws/live` | WebSocket for real-time updates |

## Development

### Backend (Python/FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend (React/TypeScript)

```bash
cd frontend
npm install
npm run dev
```

## Hardware Setup

### TF-Rack Connection
1. Connect TF-Rack to your network
2. Note the IP address (Settings > Network)
3. Configure the IP in `.env` or settings page

### Dante Network
1. Ensure TIO boxes and TF-Rack on same subnet
2. Use Dante Controller to configure sample rates
3. Devices auto-discovered via mDNS

### E-Ink Displays
- Connect Waveshare e-paper displays via USB
- Displays are mapped to channels 1-16
- Supports 2.9" 296x128 displays
- Requires USB access (privileged Docker mode)

## Input Preset Categories

| Category | Example Presets |
|----------|-----------------|
| Vocals | Lead Vocal SM58, Beta 87A, ULX-D Wireless |
| Drums | Kick (Beta 52), Snare (SM57), Toms, Overheads |
| Guitars | Electric (SM57), Acoustic (C414), DI |
| Bass | DI (Radial JDI), Amp (MD421) |
| Keys | Stereo L/R |

## License

MIT License - see LICENSE file

## Credits

- Inspired by [Micboard](https://github.com/karlcswanson/micboard) for wireless monitoring UI
- Yamaha TF series OSC protocol documentation
- Dante networking by Audinate
