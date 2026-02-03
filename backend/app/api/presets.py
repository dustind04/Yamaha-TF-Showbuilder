"""
Input Preset API endpoints.

Manages input presets (microphone/instrument configurations) for channels.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.preset import InputPreset, FACTORY_PRESETS
from app.models.channel import Channel

router = APIRouter()


# ========== Pydantic Models ==========

class PresetResponse(BaseModel):
    id: int
    name: str
    category: str
    subcategory: Optional[str]
    microphone: Optional[str]
    mic_manufacturer: Optional[str]
    mic_type: Optional[str]
    requires_phantom: bool
    di_box: Optional[str]
    is_direct: bool
    default_label: Optional[str]
    suggested_color: str
    is_factory: bool

    class Config:
        from_attributes = True


class PresetCreate(BaseModel):
    name: str = Field(max_length=128)
    category: str = Field(max_length=64)
    subcategory: Optional[str] = None
    microphone: Optional[str] = None
    mic_manufacturer: Optional[str] = None
    mic_model: Optional[str] = None
    mic_type: Optional[str] = None
    requires_phantom: bool = False
    di_box: Optional[str] = None
    is_direct: bool = False
    stand_type: Optional[str] = None
    notes: Optional[str] = None
    gain_preset: int = 0
    hpf_enabled: bool = True
    hpf_frequency: int = 80
    eq_enabled: bool = True
    eq_settings: Optional[dict] = None
    comp_enabled: bool = False
    comp_settings: Optional[dict] = None
    gate_enabled: bool = False
    gate_settings: Optional[dict] = None
    default_label: Optional[str] = Field(None, max_length=32)
    suggested_color: str = "white"


class PresetApply(BaseModel):
    channel_id: int
    update_eink: bool = True


# ========== API Endpoints ==========

@router.get("/", response_model=List[PresetResponse])
async def get_presets(
    category: Optional[str] = None,
    include_factory: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get all input presets, optionally filtered by category."""
    query = select(InputPreset)
    if category:
        query = query.where(InputPreset.category == category)
    if not include_factory:
        query = query.where(InputPreset.is_factory == False)
    query = query.order_by(InputPreset.category, InputPreset.name)

    result = await db.execute(query)
    presets = result.scalars().all()
    return presets


@router.get("/categories")
async def get_preset_categories(db: AsyncSession = Depends(get_db)):
    """Get all available preset categories."""
    result = await db.execute(
        select(InputPreset.category).distinct().order_by(InputPreset.category)
    )
    categories = result.scalars().all()
    return {"categories": categories}


@router.get("/{preset_id}")
async def get_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific preset with full details."""
    result = await db.execute(select(InputPreset).where(InputPreset.id == preset_id))
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    return {
        "id": preset.id,
        "name": preset.name,
        "category": preset.category,
        "subcategory": preset.subcategory,
        "microphone": preset.microphone,
        "mic_manufacturer": preset.mic_manufacturer,
        "mic_model": preset.mic_model,
        "mic_type": preset.mic_type,
        "requires_phantom": preset.requires_phantom,
        "di_box": preset.di_box,
        "is_direct": preset.is_direct,
        "stand_type": preset.stand_type,
        "notes": preset.notes,
        "gain_preset": preset.gain_preset,
        "hpf_enabled": preset.hpf_enabled,
        "hpf_frequency": preset.hpf_frequency,
        "eq_enabled": preset.eq_enabled,
        "eq_settings": preset.eq_settings,
        "comp_enabled": preset.comp_enabled,
        "comp_settings": preset.comp_settings,
        "gate_enabled": preset.gate_enabled,
        "gate_settings": preset.gate_settings,
        "default_label": preset.default_label,
        "suggested_color": preset.suggested_color,
        "is_factory": preset.is_factory
    }


@router.post("/", response_model=PresetResponse)
async def create_preset(preset: PresetCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user preset."""
    db_preset = InputPreset(**preset.model_dump(), is_factory=False)
    db.add(db_preset)
    await db.commit()
    await db.refresh(db_preset)
    return db_preset


@router.put("/{preset_id}", response_model=PresetResponse)
async def update_preset(
    preset_id: int,
    preset_update: PresetCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update a preset (user presets only)."""
    result = await db.execute(select(InputPreset).where(InputPreset.id == preset_id))
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    if preset.is_factory:
        raise HTTPException(status_code=400, detail="Cannot modify factory presets")

    update_data = preset_update.model_dump()
    for field, value in update_data.items():
        if value is not None:
            setattr(preset, field, value)

    await db.commit()
    await db.refresh(preset)
    return preset


@router.delete("/{preset_id}")
async def delete_preset(preset_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a preset (user presets only)."""
    result = await db.execute(select(InputPreset).where(InputPreset.id == preset_id))
    preset = result.scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    if preset.is_factory:
        raise HTTPException(status_code=400, detail="Cannot delete factory presets")

    await db.delete(preset)
    await db.commit()
    return {"status": "ok", "deleted": preset_id}


@router.post("/{preset_id}/apply")
async def apply_preset_to_channel(
    preset_id: int,
    apply: PresetApply,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Apply a preset to a channel."""
    # Get preset
    preset_result = await db.execute(select(InputPreset).where(InputPreset.id == preset_id))
    preset = preset_result.scalar_one_or_none()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    # Get channel
    channel_result = await db.execute(select(Channel).where(Channel.id == apply.channel_id))
    channel = channel_result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Apply preset settings to channel
    channel.name = preset.default_label or preset.name[:8]
    channel.color = preset.suggested_color
    channel.phantom_power = preset.requires_phantom
    channel.eq_enabled = preset.eq_enabled
    channel.comp_enabled = preset.comp_enabled
    channel.gate_enabled = preset.gate_enabled

    if preset.eq_settings:
        channel.eq_settings = {
            "hpf_enabled": preset.hpf_enabled,
            "hpf_frequency": preset.hpf_frequency,
            **preset.eq_settings
        }

    if preset.comp_settings:
        channel.comp_settings = preset.comp_settings

    if preset.gate_settings:
        channel.gate_settings = preset.gate_settings

    # Send to TF-Rack
    tf_rack = getattr(request.app.state, 'tf_rack', None)
    if tf_rack and tf_rack.is_connected:
        ch = channel.channel_number
        tf_rack.set_name(ch, channel.name)
        tf_rack.set_color(ch, channel.color)
        tf_rack.set_phantom(ch, channel.phantom_power)
        tf_rack.set_eq_enabled(ch, channel.eq_enabled)
        tf_rack.set_comp_enabled(ch, channel.comp_enabled)
        tf_rack.set_gate_enabled(ch, channel.gate_enabled)

        if preset.hpf_enabled:
            tf_rack.set_eq_hpf(ch, True, preset.hpf_frequency)

        # Apply EQ bands
        if preset.eq_settings:
            eq = preset.eq_settings
            tf_rack.set_eq_band(ch, 1, eq['low']['frequency'], eq['low']['gain'], eq['low']['q'])
            tf_rack.set_eq_band(ch, 2, eq['low_mid']['frequency'], eq['low_mid']['gain'], eq['low_mid']['q'])
            tf_rack.set_eq_band(ch, 3, eq['high_mid']['frequency'], eq['high_mid']['gain'], eq['high_mid']['q'])
            tf_rack.set_eq_band(ch, 4, eq['high']['frequency'], eq['high']['gain'], eq['high']['q'])

        # Apply compressor
        if preset.comp_enabled and preset.comp_settings:
            comp = preset.comp_settings
            tf_rack.set_comp_params(ch, comp['threshold'], comp['ratio'],
                                     comp['attack'], comp['release'], comp['gain'], comp['knee'])

        # Apply gate
        if preset.gate_enabled and preset.gate_settings:
            gate = preset.gate_settings
            tf_rack.set_gate_params(ch, gate['threshold'], gate['range'],
                                     gate['attack'], gate['hold'], gate['release'])

    # Update e-ink display
    if apply.update_eink and preset.default_label:
        eink = getattr(request.app.state, 'eink', None)
        if eink:
            await eink.update_channel_label(channel.channel_number, preset.default_label)

    await db.commit()

    return {
        "status": "ok",
        "channel_id": channel.id,
        "channel_number": channel.channel_number,
        "preset_applied": preset.name,
        "microphone": preset.microphone
    }


@router.post("/init-factory")
async def init_factory_presets(db: AsyncSession = Depends(get_db)):
    """Initialize factory presets in the database."""
    # Check if factory presets already exist
    result = await db.execute(
        select(InputPreset).where(InputPreset.is_factory == True).limit(1)
    )
    if result.scalar_one_or_none():
        return {"status": "already_initialized", "message": "Factory presets already exist"}

    # Add all factory presets
    for preset_data in FACTORY_PRESETS:
        preset = InputPreset(**preset_data)
        db.add(preset)

    await db.commit()

    return {"status": "ok", "presets_added": len(FACTORY_PRESETS)}


@router.get("/search")
async def search_presets(
    q: str,
    db: AsyncSession = Depends(get_db)
):
    """Search presets by name, microphone, or category."""
    query = select(InputPreset).where(
        (InputPreset.name.ilike(f"%{q}%")) |
        (InputPreset.microphone.ilike(f"%{q}%")) |
        (InputPreset.category.ilike(f"%{q}%")) |
        (InputPreset.mic_manufacturer.ilike(f"%{q}%"))
    ).order_by(InputPreset.category, InputPreset.name)

    result = await db.execute(query)
    presets = result.scalars().all()

    return {"results": [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "microphone": p.microphone,
            "is_factory": p.is_factory
        }
        for p in presets
    ]}
