"""
Yamaha TF Showbuilder - Main Application Entry Point

This application provides API control for:
- Yamaha TF-Rack digital mixer
- Dante/TIO devices
- E-ink display labels
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import channels, patches, scenes, devices, eink, websocket, shows, presets, backstage, songs
from app.core.config import settings
from app.core.database import init_db
from app.services.tf_rack import TFRackService
from app.services.dante_discovery import DanteDiscoveryService
from app.services.eink_manager import EInkManager
from app.services.wireless_monitor import wireless_monitor


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Note: Strict-Transport-Security should only be added when running HTTPS
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting Yamaha TF Showbuilder...")

    # Initialize database
    await init_db()

    # Initialize TF-Rack connection
    app.state.tf_rack = TFRackService(
        host=settings.TF_RACK_IP,
        port=settings.TF_RACK_PORT
    )
    await app.state.tf_rack.connect()

    # Initialize Dante discovery
    if settings.DANTE_DISCOVERY_ENABLED:
        app.state.dante = DanteDiscoveryService()
        await app.state.dante.start_discovery()

    # Initialize E-ink display manager
    if settings.EINK_ENABLED:
        app.state.eink = EInkManager()
        await app.state.eink.initialize()

    # Initialize wireless monitoring service
    app.state.wireless = wireless_monitor
    await wireless_monitor.start()

    print("Yamaha TF Showbuilder started successfully!")

    yield

    # Shutdown
    print("Shutting down Yamaha TF Showbuilder...")

    if hasattr(app.state, 'tf_rack'):
        await app.state.tf_rack.disconnect()

    if hasattr(app.state, 'dante'):
        await app.state.dante.stop_discovery()

    if hasattr(app.state, 'eink'):
        await app.state.eink.shutdown()

    if hasattr(app.state, 'wireless'):
        await app.state.wireless.stop()

    print("Shutdown complete.")


app = FastAPI(
    title="Yamaha TF Showbuilder",
    description="Control interface for Yamaha TF-Rack, Dante devices, and E-ink display labels",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers
app.add_middleware(SecurityHeadersMiddleware)

# Include API routers
app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
app.include_router(patches.router, prefix="/api/patches", tags=["Patches"])
app.include_router(scenes.router, prefix="/api/scenes", tags=["Scenes"])
app.include_router(devices.router, prefix="/api/devices", tags=["Devices"])
app.include_router(eink.router, prefix="/api/eink", tags=["E-Ink Displays"])
app.include_router(shows.router, prefix="/api", tags=["Shows, Bands, Artists"])
app.include_router(presets.router, prefix="/api/presets", tags=["Input Presets"])
app.include_router(backstage.router, prefix="/api/backstage", tags=["Backstage Monitor"])
app.include_router(songs.router, prefix="/api/songs", tags=["Songs & Setlists"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Yamaha TF Showbuilder",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "tf_rack_connected": hasattr(app.state, 'tf_rack') and app.state.tf_rack.is_connected,
        "dante_enabled": settings.DANTE_DISCOVERY_ENABLED,
        "eink_enabled": settings.EINK_ENABLED
    }


@app.get("/display")
async def backstage_display():
    """
    Standalone backstage display page.

    This is a read-only display that can be accessed from any device
    on the network. It shows artist assignments, mic/IEM info, and
    auto-refreshes every 5 seconds.

    Access at: http://<server-ip>:8000/display
    """
    static_dir = Path(__file__).parent.parent / "static"
    display_file = static_dir / "display.html"
    if display_file.exists():
        return FileResponse(display_file, media_type="text/html")
    return {"error": "Display page not found"}


@app.get("/display/wireless")
async def wireless_display():
    """
    Standalone wireless monitoring display (Micboard-style).

    Shows all wireless devices with battery/RF levels.
    """
    static_dir = Path(__file__).parent.parent / "static"
    display_file = static_dir / "wireless.html"
    if display_file.exists():
        return FileResponse(display_file, media_type="text/html")
    # Fallback to main display
    display_file = static_dir / "display.html"
    if display_file.exists():
        return FileResponse(display_file, media_type="text/html")
    return {"error": "Display page not found"}
