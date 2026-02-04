"""
Scene Management API endpoints.

Provides scene store, recall, and management for the show builder.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.scene import Scene
from app.models.channel import Channel

router = APIRouter()


# ========== Pydantic Models ==========

class SceneCreate(BaseModel):
    scene_number: int = Field(ge=1, le=200)
    name: str = Field(max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    fade_time: float = Field(ge=0, le=60, default=0)


class SceneUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    fade_time: Optional[float] = Field(None, ge=0, le=60)
    eink_labels: Optional[Dict[str, str]] = None


class SceneResponse(BaseModel):
    id: int
    scene_number: int
    name: str
    description: Optional[str]
    fade_time: float
    eink_labels: Dict[str, Any]

    class Config:
        from_attributes = True


class SceneRecallOptions(BaseModel):
    fade_override: Optional[float] = None  # Override scene fade time
    channels_only: bool = False  # Only recall channel settings, not routing
    update_eink: bool = True  # Update e-ink displays with scene labels


class EInkLabelUpdate(BaseModel):
    labels: Dict[int, str]  # channel number -> label text


# ========== API Endpoints ==========

@router.get("/", response_model=List[SceneResponse])
async def get_scenes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all scenes."""
    query = select(Scene).order_by(Scene.scene_number).offset(skip).limit(limit)
    result = await db.execute(query)
    scenes = result.scalars().all()
    return scenes


@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific scene by ID."""
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.get("/number/{scene_number}", response_model=SceneResponse)
async def get_scene_by_number(scene_number: int, db: AsyncSession = Depends(get_db)):
    """Get a scene by its scene number."""
    result = await db.execute(select(Scene).where(Scene.scene_number == scene_number))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.post("/", response_model=SceneResponse)
async def create_scene(
    scene: SceneCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new scene."""
    # Check if scene number already exists
    existing = await db.execute(
        select(Scene).where(Scene.scene_number == scene.scene_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Scene number already exists")

    db_scene = Scene(**scene.model_dump())
    db.add(db_scene)
    await db.commit()
    await db.refresh(db_scene)
    return db_scene


@router.put("/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: int,
    scene_update: SceneUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a scene."""
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    update_data = scene_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(scene, field, value)

    await db.commit()
    await db.refresh(scene)
    return scene


@router.delete("/{scene_id}")
async def delete_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a scene."""
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    await db.delete(scene)
    await db.commit()
    return {"status": "ok", "deleted": scene_id}


@router.post("/{scene_id}/store")
async def store_scene(
    scene_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Store current mixer state to a scene.

    Captures all channel settings and optionally e-ink labels.
    """
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Get all channels
    channels_result = await db.execute(select(Channel))
    channels = channels_result.scalars().all()

    # Build mixer state snapshot
    mixer_state = {}
    eink_labels = {}

    for channel in channels:
        ch_key = f"{channel.channel_type.value}_{channel.channel_number}"
        mixer_state[ch_key] = {
            "name": channel.name,
            "color": channel.color,
            "fader_level": channel.fader_level,
            "pan": channel.pan,
            "mute": channel.mute,
            "on": channel.on,
            "phantom_power": channel.phantom_power,
            "gain": channel.gain,
            "eq_enabled": channel.eq_enabled,
            "eq_settings": channel.eq_settings,
            "comp_enabled": channel.comp_enabled,
            "comp_settings": channel.comp_settings,
            "gate_enabled": channel.gate_enabled,
            "gate_settings": channel.gate_settings,
            "aux_sends": channel.aux_sends
        }

        # Store channel name as e-ink label
        if channel.name:
            eink_labels[str(channel.channel_number)] = channel.name

    scene.mixer_state = mixer_state
    scene.eink_labels = eink_labels

    await db.commit()

    # Also store to TF-Rack if connected
    tf_rack = getattr(request.app.state, 'tf_rack', None)
    if tf_rack and tf_rack.is_connected:
        tf_rack.store_scene(scene.scene_number, scene.name)

    return {
        "status": "ok",
        "scene_id": scene_id,
        "scene_number": scene.scene_number,
        "channels_stored": len(mixer_state)
    }


@router.post("/{scene_id}/recall")
async def recall_scene(
    scene_id: int,
    options: SceneRecallOptions = SceneRecallOptions(),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Recall a scene to the mixer.

    Restores all channel settings and optionally updates e-ink displays.
    Sends individual channel values to TF-Rack via OSC.
    """
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    if not scene.mixer_state:
        raise HTTPException(status_code=400, detail="Scene has no stored state")

    # Determine fade time
    fade_time = options.fade_override if options.fade_override is not None else scene.fade_time

    # Get TF-Rack connection
    tf_rack = getattr(request.app.state, 'tf_rack', None) if request else None
    channels_sent = 0

    # Update database channels and send to TF-Rack
    for ch_key, ch_state in scene.mixer_state.items():
        # Parse channel key (format: "channeltype_channelnumber")
        parts = ch_key.rsplit('_', 1)
        if len(parts) == 2:
            ch_type_str, ch_num = parts[0], int(parts[1])

            # Find channel by type and number
            result = await db.execute(
                select(Channel).where(
                    Channel.channel_number == ch_num,
                    Channel.channel_type == ch_type_str
                )
            )
            channel = result.scalar_one_or_none()

            if channel:
                # Update channel state in database
                for field, value in ch_state.items():
                    if hasattr(channel, field):
                        setattr(channel, field, value)

                # Send to TF-Rack
                if tf_rack and tf_rack.is_connected:
                    if "fader_level" in ch_state:
                        tf_rack.set_fader(ch_num, ch_state["fader_level"])
                    if "mute" in ch_state:
                        tf_rack.set_mute(ch_num, ch_state["mute"])
                    if "on" in ch_state:
                        tf_rack.set_channel_on(ch_num, ch_state["on"])
                    if "name" in ch_state:
                        tf_rack.set_name(ch_num, ch_state["name"])
                    if "pan" in ch_state:
                        tf_rack.set_pan(ch_num, ch_state["pan"])
                    if "gain" in ch_state:
                        tf_rack.set_gain(ch_num, ch_state["gain"])
                    channels_sent += 1

    await db.commit()

    # Update e-ink displays
    if options.update_eink and scene.eink_labels:
        eink = getattr(request.app.state, 'eink', None) if request else None
        if eink:
            labels = {int(k): (v, "") for k, v in scene.eink_labels.items()}
            await eink.update_all_labels(labels)

    return {
        "status": "ok",
        "scene_id": scene_id,
        "scene_number": scene.scene_number,
        "fade_time": fade_time,
        "channels_sent": channels_sent
    }


@router.put("/{scene_id}/eink-labels")
async def update_scene_eink_labels(
    scene_id: int,
    labels: EInkLabelUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update e-ink display labels for a scene."""
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Merge new labels with existing
    if not scene.eink_labels:
        scene.eink_labels = {}

    for channel, label in labels.labels.items():
        scene.eink_labels[str(channel)] = label

    await db.commit()

    return {"status": "ok", "labels": scene.eink_labels}


@router.post("/copy/{source_id}/to/{dest_number}")
async def copy_scene(
    source_id: int,
    dest_number: int,
    db: AsyncSession = Depends(get_db)
):
    """Copy a scene to a new scene number."""
    result = await db.execute(select(Scene).where(Scene.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source scene not found")

    # Check if destination exists
    existing = await db.execute(
        select(Scene).where(Scene.scene_number == dest_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Destination scene number exists")

    # Create copy
    new_scene = Scene(
        scene_number=dest_number,
        name=f"{source.name} (copy)",
        description=source.description,
        fade_time=source.fade_time,
        mixer_state=source.mixer_state.copy() if source.mixer_state else {},
        eink_labels=source.eink_labels.copy() if source.eink_labels else {}
    )

    db.add(new_scene)
    await db.commit()
    await db.refresh(new_scene)

    return {
        "status": "ok",
        "new_scene_id": new_scene.id,
        "scene_number": new_scene.scene_number
    }


@router.get("/{scene_id}/preview")
async def preview_scene(scene_id: int, db: AsyncSession = Depends(get_db)):
    """
    Preview scene contents without recalling.

    Returns full mixer state stored in the scene.
    """
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    scene = result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    return {
        "scene_number": scene.scene_number,
        "name": scene.name,
        "description": scene.description,
        "fade_time": scene.fade_time,
        "mixer_state": scene.mixer_state,
        "eink_labels": scene.eink_labels
    }


@router.post("/sync-from-tf")
async def sync_from_tf_rack(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync channel data from TF-Rack to database.

    Requests current channel info from the mixer and updates the database.
    Note: TF-Rack OSC doesn't support bulk state queries, so this triggers
    a request for each channel. Changes will be received asynchronously.
    """
    tf_rack = getattr(request.app.state, 'tf_rack', None)
    if not tf_rack or not tf_rack.is_connected:
        raise HTTPException(status_code=503, detail="TF-Rack not connected")

    # Request all channel info - this sends OSC queries
    # The responses will be handled by the TF-Rack service callbacks
    tf_rack.request_all_channels()

    # Update database channels with current TF-Rack state
    # (This uses cached state from any received OSC messages)
    channels_updated = 0
    for ch_num in range(1, 33):
        ch_state = tf_rack.get_channel_state(ch_num)
        if ch_state:
            result = await db.execute(
                select(Channel).where(Channel.channel_number == ch_num)
            )
            channel = result.scalar_one_or_none()
            if channel:
                if ch_state.name:
                    channel.name = ch_state.name
                if ch_state.fader != -90.0:
                    channel.fader_level = ch_state.fader
                channel.mute = ch_state.mute
                channel.on = ch_state.on
                channel.color = ch_state.color
                channels_updated += 1

    await db.commit()

    return {
        "status": "ok",
        "message": "Sync request sent to TF-Rack",
        "channels_updated": channels_updated
    }
