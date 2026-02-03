"""
Device Management API endpoints.

Manages TF-Rack and Dante device discovery and status.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.device import Device, DeviceType

router = APIRouter()


# ========== Pydantic Models ==========

class DeviceResponse(BaseModel):
    id: int
    device_type: DeviceType
    name: str
    ip_address: Optional[str]
    dante_name: Optional[str]
    dante_model: Optional[str]
    is_online: bool
    input_count: int
    output_count: int
    sample_rate: int

    class Config:
        from_attributes = True


class TFRackStatus(BaseModel):
    connected: bool
    ip_address: str
    port: int
    firmware_version: Optional[str] = None
    sample_rate: int = 48000


class DanteDeviceInfo(BaseModel):
    name: str
    ip_address: str
    model: str
    manufacturer: str
    is_online: bool
    input_channels: int
    output_channels: int
    sample_rate: int


# ========== API Endpoints ==========

@router.get("/", response_model=List[DeviceResponse])
async def get_devices(
    device_type: Optional[DeviceType] = None,
    online_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get all registered devices."""
    query = select(Device)
    if device_type:
        query = query.where(Device.device_type == device_type)
    if online_only:
        query = query.where(Device.is_online == True)

    result = await db.execute(query)
    devices = result.scalars().all()
    return devices


@router.get("/tf-rack/status")
async def get_tf_rack_status(request: Request):
    """Get TF-Rack connection status."""
    tf_rack = getattr(request.app.state, 'tf_rack', None)

    if not tf_rack:
        return TFRackStatus(
            connected=False,
            ip_address="",
            port=0
        )

    return TFRackStatus(
        connected=tf_rack.is_connected,
        ip_address=tf_rack.host,
        port=tf_rack.port
    )


@router.post("/tf-rack/connect")
async def connect_tf_rack(
    ip_address: str,
    port: int = 49280,
    request: Request = None
):
    """Connect to TF-Rack at specified address."""
    tf_rack = getattr(request.app.state, 'tf_rack', None)

    if tf_rack:
        # Disconnect existing
        await tf_rack.disconnect()
        # Update settings
        tf_rack.host = ip_address
        tf_rack.port = port
        # Reconnect
        success = await tf_rack.connect()

        return {
            "status": "connected" if success else "failed",
            "ip_address": ip_address,
            "port": port
        }

    raise HTTPException(status_code=500, detail="TF-Rack service not available")


@router.post("/tf-rack/disconnect")
async def disconnect_tf_rack(request: Request):
    """Disconnect from TF-Rack."""
    tf_rack = getattr(request.app.state, 'tf_rack', None)

    if tf_rack:
        await tf_rack.disconnect()
        return {"status": "disconnected"}

    raise HTTPException(status_code=500, detail="TF-Rack service not available")


@router.get("/tf-rack/channels")
async def get_tf_rack_channels(request: Request):
    """Get current channel states from TF-Rack."""
    tf_rack = getattr(request.app.state, 'tf_rack', None)

    if not tf_rack or not tf_rack.is_connected:
        raise HTTPException(status_code=503, detail="TF-Rack not connected")

    # Request fresh data
    tf_rack.request_all_channels()

    # Return cached states
    channels = []
    for ch_num in range(1, tf_rack.INPUT_CHANNELS + 1):
        state = tf_rack.get_channel_state(ch_num)
        if state:
            channels.append({
                "channel": ch_num,
                "name": state.name,
                "color": state.color,
                "fader": state.fader,
                "pan": state.pan,
                "mute": state.mute,
                "on": state.on
            })

    return {"channels": channels}


@router.get("/dante", response_model=List[DanteDeviceInfo])
async def get_dante_devices(request: Request):
    """Get all discovered Dante devices."""
    dante = getattr(request.app.state, 'dante', None)

    if not dante:
        return []

    devices = dante.get_devices()
    return [
        DanteDeviceInfo(
            name=d.name,
            ip_address=d.ip_address,
            model=d.model,
            manufacturer=d.manufacturer,
            is_online=d.is_online,
            input_channels=d.input_channels,
            output_channels=d.output_channels,
            sample_rate=d.sample_rate
        )
        for d in devices
    ]


@router.get("/dante/tio", response_model=List[DanteDeviceInfo])
async def get_tio_devices(request: Request):
    """Get discovered TIO stage box devices."""
    dante = getattr(request.app.state, 'dante', None)

    if not dante:
        return []

    devices = dante.get_tio_devices()
    return [
        DanteDeviceInfo(
            name=d.name,
            ip_address=d.ip_address,
            model=d.model,
            manufacturer=d.manufacturer,
            is_online=d.is_online,
            input_channels=d.input_channels,
            output_channels=d.output_channels,
            sample_rate=d.sample_rate
        )
        for d in devices
    ]


@router.post("/dante/refresh")
async def refresh_dante_discovery(request: Request):
    """Trigger a refresh of Dante device discovery."""
    dante = getattr(request.app.state, 'dante', None)

    if not dante:
        raise HTTPException(status_code=503, detail="Dante discovery not available")

    # Restart discovery
    await dante.stop_discovery()
    await dante.start_discovery()

    return {"status": "ok", "message": "Discovery restarted"}


class ManualDanteDevice(BaseModel):
    name: str
    model: str = ""
    input_channels: int = 16
    output_channels: int = 8


@router.post("/dante/manual")
async def add_manual_dante_device(device: ManualDanteDevice, request: Request):
    """Manually add a Dante device (for separate network scenarios)."""
    from app.services.dante_discovery import DanteDevice
    from datetime import datetime

    dante = getattr(request.app.state, 'dante', None)

    if not dante:
        # Create a simple device store if dante discovery isn't running
        if not hasattr(request.app.state, 'manual_dante_devices'):
            request.app.state.manual_dante_devices = {}

        manual_device = DanteDevice(
            name=device.name,
            ip_address="manual",
            model=device.model,
            manufacturer="Yamaha",
            input_channels=device.input_channels,
            output_channels=device.output_channels,
            is_online=True,
            last_seen=datetime.now()
        )
        request.app.state.manual_dante_devices[device.name] = manual_device
    else:
        # Add to dante discovery service
        manual_device = DanteDevice(
            name=device.name,
            ip_address="manual",
            model=device.model,
            manufacturer="Yamaha",
            input_channels=device.input_channels,
            output_channels=device.output_channels,
            is_online=True,
            last_seen=datetime.now()
        )
        dante.devices[device.name] = manual_device

    return {"status": "ok", "message": f"Added {device.name}"}


@router.delete("/dante/{device_name}")
async def remove_dante_device(device_name: str, request: Request):
    """Remove a manually added Dante device."""
    dante = getattr(request.app.state, 'dante', None)

    if dante and device_name in dante.devices:
        del dante.devices[device_name]
        return {"status": "ok", "message": f"Removed {device_name}"}

    manual_devices = getattr(request.app.state, 'manual_dante_devices', {})
    if device_name in manual_devices:
        del manual_devices[device_name]
        return {"status": "ok", "message": f"Removed {device_name}"}

    raise HTTPException(status_code=404, detail="Device not found")


@router.get("/dante/{device_name}")
async def get_dante_device_details(device_name: str, request: Request):
    """Get detailed information about a specific Dante device."""
    dante = getattr(request.app.state, 'dante', None)

    if not dante:
        raise HTTPException(status_code=503, detail="Dante discovery not available")

    device = dante.get_device(device_name)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "name": device.name,
        "ip_address": device.ip_address,
        "port": device.port,
        "model": device.model,
        "manufacturer": device.manufacturer,
        "mac_address": device.mac_address,
        "is_online": device.is_online,
        "input_channels": device.input_channels,
        "output_channels": device.output_channels,
        "sample_rate": device.sample_rate,
        "dante_version": device.dante_version,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "properties": device.properties
    }


@router.post("/register")
async def register_device(
    name: str,
    device_type: DeviceType,
    ip_address: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Manually register a device."""
    device = Device(
        device_type=device_type,
        name=name,
        ip_address=ip_address,
        is_online=False
    )

    if device_type == DeviceType.TF_RACK:
        device.input_count = 32
        device.output_count = 34
    elif device_type == DeviceType.TIO_1608_D:
        device.input_count = 16
        device.output_count = 8

    db.add(device)
    await db.commit()
    await db.refresh(device)

    return {
        "status": "ok",
        "device_id": device.id
    }
