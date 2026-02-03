"""
E-Ink Display API endpoints.

Manages e-ink display labels for physical input identification.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.eink_display import EInkDisplay

router = APIRouter()


# ========== Pydantic Models ==========

class DisplayUpdate(BaseModel):
    text: str = Field(max_length=32)
    subtext: str = Field(default="", max_length=32)
    color: str = "black"
    inverted: bool = False


class DisplayMapping(BaseModel):
    display_index: int = Field(ge=0)
    channel_number: int = Field(ge=1)
    channel_type: str = "input"


class DisplayStatus(BaseModel):
    index: int
    connected: bool
    current_text: str
    channel_number: Optional[int] = None
    last_update: Optional[str] = None


class BulkLabelUpdate(BaseModel):
    labels: Dict[int, str]  # channel_number -> text


# ========== API Endpoints ==========

@router.get("/status", response_model=List[DisplayStatus])
async def get_display_status(request: Request):
    """Get status of all e-ink displays."""
    eink = getattr(request.app.state, 'eink', None)

    if not eink:
        return []

    status = eink.get_display_status()
    return [DisplayStatus(**s) for s in status]


@router.get("/{display_index}")
async def get_display(display_index: int, request: Request):
    """Get information about a specific display."""
    eink = getattr(request.app.state, 'eink', None)

    if not eink:
        raise HTTPException(status_code=503, detail="E-ink service not available")

    display = eink.displays.get(display_index)
    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    return {
        "index": display_index,
        "connected": display.is_connected,
        "current_text": display.current_content.text if display.current_content else "",
        "current_subtext": display.current_content.subtext if display.current_content else "",
        "width": display.config.width,
        "height": display.config.height,
        "last_update": display.last_update.isoformat() if display.last_update else None
    }


@router.post("/{display_index}/update")
async def update_display(
    display_index: int,
    update: DisplayUpdate,
    request: Request
):
    """Update a specific e-ink display."""
    eink = getattr(request.app.state, 'eink', None)

    if not eink:
        raise HTTPException(status_code=503, detail="E-ink service not available")

    display = eink.displays.get(display_index)
    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    from app.services.eink_manager import DisplayContent
    content = DisplayContent(
        text=update.text,
        subtext=update.subtext,
        color=update.color,
        background="black" if update.inverted else "white"
    )

    success = await display.update(content)

    return {
        "status": "ok" if success else "failed",
        "display": display_index,
        "text": update.text
    }


@router.post("/channel/{channel_number}")
async def update_channel_label(
    channel_number: int,
    update: DisplayUpdate,
    request: Request
):
    """Update the e-ink display for a specific channel."""
    eink = getattr(request.app.state, 'eink', None)

    if not eink:
        raise HTTPException(status_code=503, detail="E-ink service not available")

    success = await eink.update_channel_label(
        channel_number,
        update.text,
        update.subtext,
        update.color
    )

    return {
        "status": "ok" if success else "failed",
        "channel": channel_number,
        "text": update.text
    }


@router.post("/bulk-update")
async def bulk_update_labels(
    update: BulkLabelUpdate,
    request: Request
):
    """Update multiple e-ink displays at once."""
    eink = getattr(request.app.state, 'eink', None)

    if not eink:
        raise HTTPException(status_code=503, detail="E-ink service not available")

    # Convert to expected format
    labels = {ch: (text, "") for ch, text in update.labels.items()}

    count = await eink.update_all_labels(labels)

    return {
        "status": "ok",
        "updated": count,
        "total": len(update.labels)
    }


@router.post("/clear-all")
async def clear_all_displays(request: Request):
    """Clear all e-ink displays to white."""
    eink = getattr(request.app.state, 'eink', None)

    if not eink:
        raise HTTPException(status_code=503, detail="E-ink service not available")

    await eink.clear_all()

    return {"status": "ok"}


@router.post("/mapping")
async def set_display_mapping(
    mapping: DisplayMapping,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Map a display to a specific channel."""
    eink = getattr(request.app.state, 'eink', None)

    if eink:
        eink.set_channel_mapping(mapping.channel_number, mapping.display_index)

    # Also store in database
    result = await db.execute(
        select(EInkDisplay).where(EInkDisplay.display_index == mapping.display_index)
    )
    display = result.scalar_one_or_none()

    if display:
        display.channel_number = mapping.channel_number
        display.channel_type = mapping.channel_type
    else:
        display = EInkDisplay(
            display_index=mapping.display_index,
            channel_number=mapping.channel_number,
            channel_type=mapping.channel_type
        )
        db.add(display)

    await db.commit()

    return {
        "status": "ok",
        "display": mapping.display_index,
        "channel": mapping.channel_number
    }


@router.get("/mapping/all")
async def get_all_mappings(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all display-to-channel mappings."""
    result = await db.execute(select(EInkDisplay))
    displays = result.scalars().all()

    return {
        "mappings": [
            {
                "display_index": d.display_index,
                "channel_number": d.channel_number,
                "channel_type": d.channel_type
            }
            for d in displays
        ]
    }


@router.post("/refresh")
async def refresh_all_displays(request: Request, db: AsyncSession = Depends(get_db)):
    """Refresh all displays with current channel names."""
    eink = getattr(request.app.state, 'eink', None)

    if not eink:
        raise HTTPException(status_code=503, detail="E-ink service not available")

    # Get all channels
    from app.models.channel import Channel
    result = await db.execute(select(Channel))
    channels = result.scalars().all()

    # Build label dict
    labels = {ch.channel_number: (ch.name, "") for ch in channels if ch.name}

    count = await eink.update_all_labels(labels)

    return {
        "status": "ok",
        "updated": count
    }


@router.post("/test-pattern")
async def display_test_pattern(request: Request):
    """Display a test pattern on all connected displays."""
    eink = getattr(request.app.state, 'eink', None)

    if not eink:
        raise HTTPException(status_code=503, detail="E-ink service not available")

    # Update each display with its index number
    for i, display in eink.displays.items():
        from app.services.eink_manager import DisplayContent
        content = DisplayContent(
            text=f"CH {i + 1}",
            subtext="TEST",
            color="black"
        )
        await display.update(content)

    return {"status": "ok", "displays_tested": len(eink.displays)}
