"""
Channel API endpoints.

Provides CRUD operations and control for mixer channels.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.channel import Channel, ChannelType

router = APIRouter()


# ========== Pydantic Models ==========

class EQBandSettings(BaseModel):
    frequency: float = Field(ge=20, le=20000)
    gain: float = Field(ge=-18, le=18)
    q: float = Field(ge=0.1, le=10)
    type: str = "peak"


class EQSettings(BaseModel):
    hpf_enabled: bool = False
    hpf_frequency: float = 80
    low: EQBandSettings = EQBandSettings(frequency=100, gain=0, q=1.0, type="shelf")
    low_mid: EQBandSettings = EQBandSettings(frequency=400, gain=0, q=1.0)
    high_mid: EQBandSettings = EQBandSettings(frequency=2000, gain=0, q=1.0)
    high: EQBandSettings = EQBandSettings(frequency=8000, gain=0, q=1.0, type="shelf")


class CompSettings(BaseModel):
    threshold: float = Field(ge=-60, le=0, default=-10)
    ratio: float = Field(ge=1, le=20, default=4.0)
    attack: float = Field(ge=0.1, le=200, default=25)
    release: float = Field(ge=10, le=2000, default=200)
    gain: float = Field(ge=-20, le=20, default=0)
    knee: str = "medium"


class GateSettings(BaseModel):
    threshold: float = Field(ge=-80, le=0, default=-60)
    range: float = Field(ge=-80, le=0, default=-80)
    attack: float = Field(ge=0.05, le=120, default=1)
    hold: float = Field(ge=0.5, le=2000, default=100)
    release: float = Field(ge=5, le=5000, default=200)


class ChannelCreate(BaseModel):
    channel_number: int = Field(ge=1, le=40)
    channel_type: ChannelType = ChannelType.INPUT
    name: str = Field(max_length=32, default="")


class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=32)
    color: Optional[str] = None
    icon: Optional[str] = None
    fader_level: Optional[float] = Field(None, ge=-90, le=10)
    pan: Optional[float] = Field(None, ge=-100, le=100)
    mute: Optional[bool] = None
    on: Optional[bool] = None
    phantom_power: Optional[bool] = None
    gain: Optional[float] = Field(None, ge=-12, le=60)
    phase_invert: Optional[bool] = None
    eq_enabled: Optional[bool] = None
    eq_settings: Optional[EQSettings] = None
    comp_enabled: Optional[bool] = None
    comp_settings: Optional[CompSettings] = None
    gate_enabled: Optional[bool] = None
    gate_settings: Optional[GateSettings] = None


class ChannelResponse(BaseModel):
    id: int
    channel_number: int
    channel_type: ChannelType
    name: str
    color: str
    icon: str
    fader_level: float
    pan: float
    mute: bool
    on: bool
    phantom_power: bool
    gain: float
    phase_invert: bool
    eq_enabled: bool
    comp_enabled: bool
    gate_enabled: bool

    class Config:
        from_attributes = True


class FaderUpdate(BaseModel):
    level: float = Field(ge=-90, le=10)


class AuxSendUpdate(BaseModel):
    aux_number: int = Field(ge=1, le=20)
    level: float = Field(ge=-90, le=10)
    on: bool = True


# ========== API Endpoints ==========

@router.get("/", response_model=List[ChannelResponse])
async def get_channels(
    channel_type: Optional[ChannelType] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all channels, optionally filtered by type."""
    query = select(Channel)
    if channel_type:
        query = query.where(Channel.channel_type == channel_type)
    query = query.order_by(Channel.channel_number)

    result = await db.execute(query)
    channels = result.scalars().all()
    return channels


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific channel by ID."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.post("/", response_model=ChannelResponse)
async def create_channel(
    channel: ChannelCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new channel."""
    db_channel = Channel(**channel.model_dump())
    db.add(db_channel)
    await db.commit()
    await db.refresh(db_channel)
    return db_channel


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a channel."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    await db.delete(channel)
    await db.commit()
    return {"status": "ok", "deleted": channel_id}


@router.put("/{channel_id}", response_model=ChannelResponse)
@router.patch("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    channel_update: ChannelUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update a channel's settings."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Update database record
    update_data = channel_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(channel, field, value)

    # Send updates to TF-Rack
    tf_rack = request.app.state.tf_rack
    if tf_rack and tf_rack.is_connected:
        ch_num = channel.channel_number
        if "fader_level" in update_data:
            tf_rack.set_fader(ch_num, update_data["fader_level"])
        if "pan" in update_data:
            tf_rack.set_pan(ch_num, update_data["pan"])
        if "mute" in update_data:
            tf_rack.set_mute(ch_num, update_data["mute"])
        if "on" in update_data:
            tf_rack.set_channel_on(ch_num, update_data["on"])
        if "name" in update_data:
            tf_rack.set_name(ch_num, update_data["name"])
            # Also update e-ink display
            if hasattr(request.app.state, 'eink'):
                await request.app.state.eink.update_channel_label(
                    ch_num, update_data["name"]
                )
        if "color" in update_data:
            tf_rack.set_color(ch_num, update_data["color"])
        if "gain" in update_data:
            tf_rack.set_gain(ch_num, update_data["gain"])
        if "phantom_power" in update_data:
            tf_rack.set_phantom(ch_num, update_data["phantom_power"])
        if "eq_enabled" in update_data:
            tf_rack.set_eq_enabled(ch_num, update_data["eq_enabled"])
        if "comp_enabled" in update_data:
            tf_rack.set_comp_enabled(ch_num, update_data["comp_enabled"])
        if "gate_enabled" in update_data:
            tf_rack.set_gate_enabled(ch_num, update_data["gate_enabled"])

    await db.commit()
    await db.refresh(channel)
    return channel


@router.put("/{channel_id}/fader")
@router.post("/{channel_id}/fader")
async def set_channel_fader(
    channel_id: int,
    fader: FaderUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Set channel fader level."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.fader_level = fader.level

    tf_rack = request.app.state.tf_rack
    if tf_rack and tf_rack.is_connected:
        tf_rack.set_fader(channel.channel_number, fader.level)

    await db.commit()
    return {"status": "ok", "level": fader.level}


@router.post("/{channel_id}/mute")
async def toggle_channel_mute(
    channel_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Toggle channel mute state."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.mute = not channel.mute

    tf_rack = request.app.state.tf_rack
    if tf_rack and tf_rack.is_connected:
        tf_rack.set_mute(channel.channel_number, channel.mute)

    await db.commit()
    return {"status": "ok", "mute": channel.mute}


@router.post("/{channel_id}/aux-send")
async def set_aux_send(
    channel_id: int,
    send: AuxSendUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Set aux send level for a channel."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Update aux sends in database
    if not channel.aux_sends:
        channel.aux_sends = {}
    channel.aux_sends[str(send.aux_number)] = {"level": send.level, "on": send.on}

    tf_rack = request.app.state.tf_rack
    if tf_rack and tf_rack.is_connected:
        tf_rack.set_aux_send(channel.channel_number, send.aux_number, send.level)
        tf_rack.set_aux_send_on(channel.channel_number, send.aux_number, send.on)

    await db.commit()
    return {"status": "ok", "aux": send.aux_number, "level": send.level}


@router.put("/{channel_id}/eq")
async def update_channel_eq(
    channel_id: int,
    eq: EQSettings,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update channel EQ settings."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.eq_settings = eq.model_dump()

    tf_rack = request.app.state.tf_rack
    if tf_rack and tf_rack.is_connected:
        ch = channel.channel_number
        tf_rack.set_eq_hpf(ch, eq.hpf_enabled, eq.hpf_frequency)
        tf_rack.set_eq_band(ch, 1, eq.low.frequency, eq.low.gain, eq.low.q)
        tf_rack.set_eq_band(ch, 2, eq.low_mid.frequency, eq.low_mid.gain, eq.low_mid.q)
        tf_rack.set_eq_band(ch, 3, eq.high_mid.frequency, eq.high_mid.gain, eq.high_mid.q)
        tf_rack.set_eq_band(ch, 4, eq.high.frequency, eq.high.gain, eq.high.q)

    await db.commit()
    return {"status": "ok"}


@router.put("/{channel_id}/compressor")
async def update_channel_comp(
    channel_id: int,
    comp: CompSettings,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update channel compressor settings."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.comp_settings = comp.model_dump()

    tf_rack = request.app.state.tf_rack
    if tf_rack and tf_rack.is_connected:
        tf_rack.set_comp_params(
            channel.channel_number,
            comp.threshold, comp.ratio, comp.attack,
            comp.release, comp.gain, comp.knee
        )

    await db.commit()
    return {"status": "ok"}


@router.put("/{channel_id}/gate")
async def update_channel_gate(
    channel_id: int,
    gate: GateSettings,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Update channel gate settings."""
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.gate_settings = gate.model_dump()

    tf_rack = request.app.state.tf_rack
    if tf_rack and tf_rack.is_connected:
        tf_rack.set_gate_params(
            channel.channel_number,
            gate.threshold, gate.range, gate.attack,
            gate.hold, gate.release
        )

    await db.commit()
    return {"status": "ok"}


@router.post("/push-to-tf")
async def push_channels_to_tf(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Push all channel settings from database to TF-Rack."""
    tf_rack = request.app.state.tf_rack
    if not tf_rack or not tf_rack.is_connected:
        raise HTTPException(status_code=503, detail="TF-Rack not connected")

    result = await db.execute(select(Channel).order_by(Channel.channel_number))
    channels = result.scalars().all()

    pushed = 0
    for channel in channels:
        ch_num = channel.channel_number
        if ch_num < 1 or ch_num > 32:
            continue

        # Push fader level
        if channel.fader_level is not None:
            tf_rack.set_fader(ch_num, channel.fader_level)

        # Push on/mute state
        if channel.on is not None:
            tf_rack.set_channel_on(ch_num, channel.on)

        # Push name
        if channel.name:
            tf_rack.set_name(ch_num, channel.name)

        pushed += 1

    return {"status": "ok", "channels_pushed": pushed}
