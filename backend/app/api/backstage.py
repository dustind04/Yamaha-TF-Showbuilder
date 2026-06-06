"""
Backstage Monitor API endpoints.

Provides information displays for artists including:
- Personal mic/IEM pack assignments
- Monitor mix information
- Channel assignments
- Show schedule

Inspired by Micboard project for wireless microphone monitoring.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import os
import uuid
from pathlib import Path

from app.core.database import get_db
from app.models.show import Show, Band, Artist

router = APIRouter()

# Image upload directory
UPLOAD_DIR = Path("/app/data/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ========== Pydantic Models ==========

class ArtistAssignment(BaseModel):
    """Artist assignment info for backstage display."""
    artist_id: int
    name: str
    image_url: Optional[str]
    primary_instrument: Optional[str]
    channel_number: Optional[int]
    mic_type: Optional[str]
    mic_number: Optional[str]  # e.g., "HH1", "BP2"
    iem_pack: Optional[str]  # e.g., "IEM 1", "PSM300-2"
    iem_frequency: Optional[str]
    monitor_mix: Optional[str]  # e.g., "AUX 1"
    notes: Optional[str]


class BackstageDisplay(BaseModel):
    """Full backstage display data for current show."""
    show_name: str
    band_name: str
    set_time: Optional[str]
    artists: List[ArtistAssignment]


class WirelessPackAssignment(BaseModel):
    """Wireless pack assignment for an artist."""
    artist_id: int
    mic_type: str  # "handheld", "bodypack", "iem"
    pack_number: str  # e.g., "HH1", "BP2", "IEM3"
    frequency: Optional[str]
    channel: Optional[int]
    notes: Optional[str]


# ========== API Endpoints ==========

@router.get("/current")
async def get_current_backstage_display(
    db: AsyncSession = Depends(get_db)
):
    """Get the current backstage display data."""
    # In a real implementation, this would track the current show/band
    # For now, return the most recent show
    result = await db.execute(
        select(Show)
        .options(selectinload(Show.bands).selectinload(Band.artists))
        .order_by(Show.date.desc())
        .limit(1)
    )
    show = result.scalar_one_or_none()

    if not show or not show.bands:
        return {"message": "No current show configured"}

    # Get the first band (would be the current set in production)
    band = show.bands[0] if show.bands else None

    if not band:
        return {"message": "No bands in current show"}

    artists = []
    for artist in band.artists:
        artists.append({
            "artist_id": artist.id,
            "name": artist.name,
            "image_url": f"/api/backstage/artists/{artist.id}/image" if artist.notes and "has_image" in artist.notes else None,
            "primary_instrument": artist.primary_instrument,
            "channel_number": artist.channel_preset.get("channel") if artist.channel_preset else None,
            "mic_type": artist.preferred_mic,
            "iem_pack": artist.in_ear_model,
            "monitor_mix": artist.monitor_preset.get("aux") if artist.monitor_preset else None,
            "notes": artist.notes
        })

    return {
        "show_name": show.name,
        "band_name": band.name,
        "venue": show.venue,
        "set_time": None,  # Would come from show_bands association
        "artists": artists
    }


@router.get("/shows/{show_id}/bands/{band_id}")
async def get_band_backstage_display(
    show_id: int,
    band_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get backstage display for a specific band in a show."""
    result = await db.execute(
        select(Band)
        .options(selectinload(Band.artists))
        .where(Band.id == band_id)
    )
    band = result.scalar_one_or_none()

    if not band:
        raise HTTPException(status_code=404, detail="Band not found")

    show_result = await db.execute(select(Show).where(Show.id == show_id))
    show = show_result.scalar_one_or_none()

    artists = []
    for i, artist in enumerate(band.artists):
        # Get wireless assignments from channel_preset
        wireless_info = artist.channel_preset.get("wireless", {}) if artist.channel_preset else {}
        monitor_info = artist.monitor_preset or {}

        artists.append({
            "artist_id": artist.id,
            "name": artist.name,
            "image_url": f"/api/backstage/artists/{artist.id}/image",
            "primary_instrument": artist.primary_instrument,
            "channel_number": artist.channel_preset.get("channel") if artist.channel_preset else i + 1,
            "mic_type": artist.preferred_mic,
            "mic_number": wireless_info.get("mic_number", f"CH{i+1}"),
            "iem_pack": artist.in_ear_model,
            "iem_frequency": wireless_info.get("iem_frequency"),
            "monitor_mix": f"AUX {monitor_info.get('aux_number', i+1)}",
            "notes": wireless_info.get("notes")
        })

    return {
        "show_name": show.name if show else "Unknown Show",
        "band_name": band.name,
        "artists": artists
    }


@router.post("/artists/{artist_id}/image")
async def upload_artist_image(
    artist_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload an image for an artist."""
    # Verify artist exists
    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Use JPEG, PNG, or WebP")

    # Generate unique filename
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"artist_{artist_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = UPLOAD_DIR / filename

    # Save file
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Update artist notes to indicate image exists (or add image_path field)
    if not artist.notes:
        artist.notes = ""
    if "has_image" not in artist.notes:
        artist.notes += " [has_image]"

    # Store image path in channel_preset
    if not artist.channel_preset:
        artist.channel_preset = {}
    artist.channel_preset["image_path"] = str(filename)

    await db.commit()

    return {
        "status": "ok",
        "artist_id": artist_id,
        "image_url": f"/api/backstage/artists/{artist_id}/image"
    }


@router.get("/artists/{artist_id}/image")
async def get_artist_image(artist_id: int, db: AsyncSession = Depends(get_db)):
    """Get an artist's image."""
    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Get image path from channel_preset
    image_path = None
    if artist.channel_preset:
        image_path = artist.channel_preset.get("image_path")

    if not image_path:
        # Return default placeholder
        raise HTTPException(status_code=404, detail="No image for this artist")

    filepath = UPLOAD_DIR / image_path
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(filepath)


@router.delete("/artists/{artist_id}/image")
async def delete_artist_image(artist_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an artist's image."""
    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    if artist.channel_preset and "image_path" in artist.channel_preset:
        image_path = artist.channel_preset["image_path"]
        filepath = UPLOAD_DIR / image_path

        if filepath.exists():
            os.remove(filepath)

        del artist.channel_preset["image_path"]
        if artist.notes:
            artist.notes = artist.notes.replace("[has_image]", "")

        await db.commit()

    return {"status": "ok"}


@router.put("/artists/{artist_id}/wireless")
async def update_artist_wireless_assignment(
    artist_id: int,
    assignment: WirelessPackAssignment,
    db: AsyncSession = Depends(get_db)
):
    """Update wireless pack assignment for an artist."""
    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    if not artist.channel_preset:
        artist.channel_preset = {}

    artist.channel_preset["wireless"] = {
        "mic_type": assignment.mic_type,
        "mic_number": assignment.pack_number,
        "frequency": assignment.frequency,
        "channel": assignment.channel,
        "notes": assignment.notes
    }

    await db.commit()

    return {"status": "ok", "artist_id": artist_id}


@router.put("/artists/{artist_id}/iem")
async def update_artist_iem_assignment(
    artist_id: int,
    iem_pack: str,
    iem_frequency: Optional[str] = None,
    aux_number: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update IEM assignment for an artist."""
    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    artist.in_ear_model = iem_pack

    if not artist.channel_preset:
        artist.channel_preset = {}
    if not artist.channel_preset.get("wireless"):
        artist.channel_preset["wireless"] = {}

    artist.channel_preset["wireless"]["iem_pack"] = iem_pack
    artist.channel_preset["wireless"]["iem_frequency"] = iem_frequency

    if not artist.monitor_preset:
        artist.monitor_preset = {}
    if aux_number:
        artist.monitor_preset["aux_number"] = aux_number

    await db.commit()

    return {"status": "ok", "artist_id": artist_id}


@router.get("/wireless-overview")
async def get_wireless_overview(db: AsyncSession = Depends(get_db)):
    """Get overview of all wireless assignments (like Micboard)."""
    result = await db.execute(
        select(Artist)
        .options(selectinload(Artist.bands))
    )
    artists = result.scalars().all()

    wireless_devices = []
    for artist in artists:
        if artist.channel_preset and artist.channel_preset.get("wireless"):
            wireless = artist.channel_preset["wireless"]
            wireless_devices.append({
                "artist_id": artist.id,
                "artist_name": artist.name,
                "bands": [b.name for b in artist.bands],
                "image_url": f"/api/backstage/artists/{artist.id}/image" if "image_path" in (artist.channel_preset or {}) else None,
                "mic_type": wireless.get("mic_type"),
                "mic_number": wireless.get("mic_number"),
                "mic_model": artist.preferred_mic,
                "frequency": wireless.get("frequency"),
                "channel": wireless.get("channel"),
                "iem_pack": wireless.get("iem_pack") or artist.in_ear_model,
                "iem_frequency": wireless.get("iem_frequency"),
                "status": "online"  # Would come from actual wireless monitoring
            })

    return {
        "devices": wireless_devices,
        "total_mics": len([d for d in wireless_devices if d["mic_type"] in ["handheld", "bodypack"]]),
        "total_iems": len([d for d in wireless_devices if d["iem_pack"]])
    }


@router.get("/display-config")
async def get_display_config():
    """Get configuration for backstage display screens."""
    return {
        "refresh_interval": 5,  # seconds
        "show_images": True,
        "show_frequencies": True,
        "show_channel_numbers": True,
        "show_monitor_mixes": True,
        "theme": "dark",
        "logo_url": None,
        "screens": [
            {"id": "main", "name": "Main Backstage", "layout": "grid"},
            {"id": "stage_left", "name": "Stage Left", "layout": "list"},
            {"id": "stage_right", "name": "Stage Right", "layout": "list"},
        ]
    }
