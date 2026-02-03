"""
Show, Band, and Artist API endpoints.

Manages shows, bands, artists, and input lists for organizing mixer configurations.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.database import get_db
from app.models.show import Show, Band, Artist, InputList

router = APIRouter()


# ========== Pydantic Models ==========

# Show Models
class ShowCreate(BaseModel):
    name: str = Field(max_length=128)
    description: Optional[str] = None
    venue: Optional[str] = Field(None, max_length=128)
    date: Optional[datetime] = None
    load_in_time: Optional[str] = None
    soundcheck_time: Optional[str] = None
    doors_time: Optional[str] = None
    show_time: Optional[str] = None
    technical_notes: Optional[str] = None


class ShowUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    venue: Optional[str] = None
    date: Optional[datetime] = None
    load_in_time: Optional[str] = None
    soundcheck_time: Optional[str] = None
    doors_time: Optional[str] = None
    show_time: Optional[str] = None
    technical_notes: Optional[str] = None
    house_eq_preset: Optional[Dict[str, Any]] = None


class ShowResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    venue: Optional[str]
    date: Optional[datetime]
    load_in_time: Optional[str]
    soundcheck_time: Optional[str]
    doors_time: Optional[str]
    show_time: Optional[str]
    technical_notes: Optional[str]

    class Config:
        from_attributes = True


# Band Models
class BandCreate(BaseModel):
    name: str = Field(max_length=128)
    genre: Optional[str] = Field(None, max_length=64)
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    monitor_requirements: Optional[str] = None
    notes: Optional[str] = None


class BandUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    genre: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    monitor_requirements: Optional[str] = None
    technical_rider: Optional[str] = None
    channel_preset: Optional[Dict[str, Any]] = None
    aux_preset: Optional[Dict[str, Any]] = None
    fx_preset: Optional[Dict[str, Any]] = None
    eink_labels: Optional[Dict[str, str]] = None
    notes: Optional[str] = None


class BandResponse(BaseModel):
    id: int
    name: str
    genre: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


# Artist Models
class ArtistCreate(BaseModel):
    name: str = Field(max_length=128)
    email: Optional[str] = None
    phone: Optional[str] = None
    primary_instrument: Optional[str] = Field(None, max_length=64)
    preferred_mic: Optional[str] = None
    preferred_di: Optional[str] = None
    in_ear_model: Optional[str] = None
    label_text: Optional[str] = Field(None, max_length=32)
    notes: Optional[str] = None


class ArtistUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    email: Optional[str] = None
    phone: Optional[str] = None
    primary_instrument: Optional[str] = None
    secondary_instruments: Optional[List[str]] = None
    preferred_mic: Optional[str] = None
    preferred_di: Optional[str] = None
    in_ear_model: Optional[str] = None
    channel_preset: Optional[Dict[str, Any]] = None
    monitor_preset: Optional[Dict[str, Any]] = None
    label_text: Optional[str] = None
    notes: Optional[str] = None


class ArtistResponse(BaseModel):
    id: int
    name: str
    primary_instrument: Optional[str]
    preferred_mic: Optional[str]
    label_text: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


# Input List Models
class InputEntry(BaseModel):
    channel: int
    source: str
    mic: Optional[str] = None
    stand: Optional[str] = None
    notes: Optional[str] = None
    artist_id: Optional[int] = None


class InputListCreate(BaseModel):
    name: str = Field(max_length=128)
    band_id: Optional[int] = None
    inputs: List[InputEntry] = []


class InputListResponse(BaseModel):
    id: int
    name: str
    band_id: Optional[int]
    inputs: List[Dict[str, Any]]

    class Config:
        from_attributes = True


# ========== Show Endpoints ==========

@router.get("/shows/", response_model=List[ShowResponse])
async def get_shows(db: AsyncSession = Depends(get_db)):
    """Get all shows."""
    result = await db.execute(select(Show).order_by(Show.date.desc()))
    shows = result.scalars().all()
    return shows


@router.get("/shows/{show_id}", response_model=ShowResponse)
async def get_show(show_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific show."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    return show


@router.post("/shows/", response_model=ShowResponse)
async def create_show(show: ShowCreate, db: AsyncSession = Depends(get_db)):
    """Create a new show."""
    db_show = Show(**show.model_dump())
    db.add(db_show)
    await db.commit()
    await db.refresh(db_show)
    return db_show


@router.put("/shows/{show_id}", response_model=ShowResponse)
async def update_show(
    show_id: int,
    show_update: ShowUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a show."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    update_data = show_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(show, field, value)

    await db.commit()
    await db.refresh(show)
    return show


@router.delete("/shows/{show_id}")
async def delete_show(show_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a show."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    await db.delete(show)
    await db.commit()
    return {"status": "ok", "deleted": show_id}


@router.post("/shows/{show_id}/bands/{band_id}")
async def add_band_to_show(
    show_id: int,
    band_id: int,
    set_order: int = 0,
    set_time: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Add a band to a show."""
    result = await db.execute(
        select(Show).options(selectinload(Show.bands)).where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    band_result = await db.execute(select(Band).where(Band.id == band_id))
    band = band_result.scalar_one_or_none()
    if not band:
        raise HTTPException(status_code=404, detail="Band not found")

    if band not in show.bands:
        show.bands.append(band)
        await db.commit()

    return {"status": "ok", "show_id": show_id, "band_id": band_id}


@router.delete("/shows/{show_id}/bands/{band_id}")
async def remove_band_from_show(
    show_id: int,
    band_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove a band from a show."""
    result = await db.execute(
        select(Show).options(selectinload(Show.bands)).where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    band_result = await db.execute(select(Band).where(Band.id == band_id))
    band = band_result.scalar_one_or_none()
    if band and band in show.bands:
        show.bands.remove(band)
        await db.commit()

    return {"status": "ok"}


@router.get("/shows/{show_id}/bands")
async def get_show_bands(show_id: int, db: AsyncSession = Depends(get_db)):
    """Get all bands in a show."""
    result = await db.execute(
        select(Show).options(selectinload(Show.bands)).where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    return {"bands": [{"id": b.id, "name": b.name, "genre": b.genre} for b in show.bands]}


# ========== Band Endpoints ==========

@router.get("/bands/", response_model=List[BandResponse])
async def get_bands(db: AsyncSession = Depends(get_db)):
    """Get all bands."""
    result = await db.execute(select(Band).order_by(Band.name))
    bands = result.scalars().all()
    return bands


@router.get("/bands/{band_id}")
async def get_band(band_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific band with full details."""
    result = await db.execute(
        select(Band).options(selectinload(Band.artists)).where(Band.id == band_id)
    )
    band = result.scalar_one_or_none()
    if not band:
        raise HTTPException(status_code=404, detail="Band not found")

    return {
        "id": band.id,
        "name": band.name,
        "genre": band.genre,
        "contact_name": band.contact_name,
        "contact_email": band.contact_email,
        "contact_phone": band.contact_phone,
        "monitor_requirements": band.monitor_requirements,
        "technical_rider": band.technical_rider,
        "channel_preset": band.channel_preset,
        "aux_preset": band.aux_preset,
        "fx_preset": band.fx_preset,
        "eink_labels": band.eink_labels,
        "notes": band.notes,
        "artists": [{"id": a.id, "name": a.name, "instrument": a.primary_instrument} for a in band.artists]
    }


@router.post("/bands/", response_model=BandResponse)
async def create_band(band: BandCreate, db: AsyncSession = Depends(get_db)):
    """Create a new band."""
    db_band = Band(**band.model_dump())
    db.add(db_band)
    await db.commit()
    await db.refresh(db_band)
    return db_band


@router.put("/bands/{band_id}", response_model=BandResponse)
async def update_band(
    band_id: int,
    band_update: BandUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a band."""
    result = await db.execute(select(Band).where(Band.id == band_id))
    band = result.scalar_one_or_none()
    if not band:
        raise HTTPException(status_code=404, detail="Band not found")

    update_data = band_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(band, field, value)

    await db.commit()
    await db.refresh(band)
    return band


@router.delete("/bands/{band_id}")
async def delete_band(band_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a band."""
    result = await db.execute(select(Band).where(Band.id == band_id))
    band = result.scalar_one_or_none()
    if not band:
        raise HTTPException(status_code=404, detail="Band not found")

    await db.delete(band)
    await db.commit()
    return {"status": "ok", "deleted": band_id}


@router.post("/bands/{band_id}/load")
async def load_band_preset(
    band_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Load a band's channel preset to the mixer and update e-ink displays."""
    result = await db.execute(select(Band).where(Band.id == band_id))
    band = result.scalar_one_or_none()
    if not band:
        raise HTTPException(status_code=404, detail="Band not found")

    # Update e-ink displays with band's labels
    if band.eink_labels and hasattr(request.app.state, 'eink'):
        labels = {int(k): (v, "") for k, v in band.eink_labels.items()}
        await request.app.state.eink.update_all_labels(labels)

    # Apply channel preset to mixer
    # This would iterate through band.channel_preset and apply settings
    # via the TF-Rack service

    return {
        "status": "ok",
        "band": band.name,
        "labels_updated": len(band.eink_labels) if band.eink_labels else 0
    }


# ========== Artist Endpoints ==========

@router.get("/artists/", response_model=List[ArtistResponse])
async def get_artists(db: AsyncSession = Depends(get_db)):
    """Get all artists."""
    result = await db.execute(select(Artist).order_by(Artist.name))
    artists = result.scalars().all()
    return artists


@router.get("/artists/{artist_id}")
async def get_artist(artist_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific artist with full details."""
    result = await db.execute(
        select(Artist).options(selectinload(Artist.bands)).where(Artist.id == artist_id)
    )
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    return {
        "id": artist.id,
        "name": artist.name,
        "email": artist.email,
        "phone": artist.phone,
        "primary_instrument": artist.primary_instrument,
        "secondary_instruments": artist.secondary_instruments,
        "preferred_mic": artist.preferred_mic,
        "preferred_di": artist.preferred_di,
        "in_ear_model": artist.in_ear_model,
        "channel_preset": artist.channel_preset,
        "monitor_preset": artist.monitor_preset,
        "label_text": artist.label_text,
        "notes": artist.notes,
        "bands": [{"id": b.id, "name": b.name} for b in artist.bands]
    }


@router.post("/artists/", response_model=ArtistResponse)
async def create_artist(artist: ArtistCreate, db: AsyncSession = Depends(get_db)):
    """Create a new artist."""
    db_artist = Artist(**artist.model_dump())
    db.add(db_artist)
    await db.commit()
    await db.refresh(db_artist)
    return db_artist


@router.put("/artists/{artist_id}", response_model=ArtistResponse)
async def update_artist(
    artist_id: int,
    artist_update: ArtistUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an artist."""
    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    update_data = artist_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(artist, field, value)

    await db.commit()
    await db.refresh(artist)
    return artist


@router.delete("/artists/{artist_id}")
async def delete_artist(artist_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an artist."""
    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    await db.delete(artist)
    await db.commit()
    return {"status": "ok", "deleted": artist_id}


@router.post("/bands/{band_id}/artists/{artist_id}")
async def add_artist_to_band(
    band_id: int,
    artist_id: int,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Add an artist to a band."""
    result = await db.execute(
        select(Band).options(selectinload(Band.artists)).where(Band.id == band_id)
    )
    band = result.scalar_one_or_none()
    if not band:
        raise HTTPException(status_code=404, detail="Band not found")

    artist_result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = artist_result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    if artist not in band.artists:
        band.artists.append(artist)
        await db.commit()

    return {"status": "ok", "band_id": band_id, "artist_id": artist_id}


# ========== Input List Endpoints ==========

@router.get("/input-lists/", response_model=List[InputListResponse])
async def get_input_lists(
    band_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all input lists, optionally filtered by band."""
    query = select(InputList)
    if band_id:
        query = query.where(InputList.band_id == band_id)
    result = await db.execute(query)
    input_lists = result.scalars().all()
    return input_lists


@router.post("/input-lists/", response_model=InputListResponse)
async def create_input_list(
    input_list: InputListCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new input list."""
    db_input_list = InputList(
        name=input_list.name,
        band_id=input_list.band_id,
        inputs=[entry.model_dump() for entry in input_list.inputs]
    )
    db.add(db_input_list)
    await db.commit()
    await db.refresh(db_input_list)
    return db_input_list


@router.put("/input-lists/{list_id}", response_model=InputListResponse)
async def update_input_list(
    list_id: int,
    inputs: List[InputEntry],
    db: AsyncSession = Depends(get_db)
):
    """Update an input list's inputs."""
    result = await db.execute(select(InputList).where(InputList.id == list_id))
    input_list = result.scalar_one_or_none()
    if not input_list:
        raise HTTPException(status_code=404, detail="Input list not found")

    input_list.inputs = [entry.model_dump() for entry in inputs]
    await db.commit()
    await db.refresh(input_list)
    return input_list


@router.delete("/input-lists/{list_id}")
async def delete_input_list(list_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an input list."""
    result = await db.execute(select(InputList).where(InputList.id == list_id))
    input_list = result.scalar_one_or_none()
    if not input_list:
        raise HTTPException(status_code=404, detail="Input list not found")

    await db.delete(input_list)
    await db.commit()
    return {"status": "ok", "deleted": list_id}
