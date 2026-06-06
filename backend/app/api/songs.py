"""
Songs API endpoints.

Provides song management, setlist building, chord chart transposition,
and integration with external song databases.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.song import Song, ChordChart, artist_songs, setlist_songs
from app.models.show import Show, Artist, Band
from app.models.scene import Scene
from app.services.chord_utils import (
    transpose_to_key, parse_chordpro, chordpro_to_text,
    get_all_keys, suggest_capo_position
)

router = APIRouter()


# ========== Pydantic Models ==========

class SongCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    artist_name: str = Field(..., min_length=1, max_length=128)
    album: Optional[str] = Field(None, max_length=128)
    year: Optional[int] = None
    original_key: str = Field("C", max_length=8)
    tempo: Optional[int] = None
    time_signature: str = Field("4/4", max_length=8)
    duration_seconds: Optional[int] = None
    chord_chart: Optional[str] = None
    lyrics: Optional[str] = None
    genre: Optional[str] = Field(None, max_length=64)
    tags: List[str] = []
    notes: Optional[str] = None


class SongUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=128)
    artist_name: Optional[str] = Field(None, max_length=128)
    album: Optional[str] = Field(None, max_length=128)
    year: Optional[int] = None
    original_key: Optional[str] = Field(None, max_length=8)
    tempo: Optional[int] = None
    time_signature: Optional[str] = Field(None, max_length=8)
    duration_seconds: Optional[int] = None
    chord_chart: Optional[str] = None
    lyrics: Optional[str] = None
    genre: Optional[str] = Field(None, max_length=64)
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    default_scene_id: Optional[int] = None


class SongResponse(BaseModel):
    id: int
    title: str
    artist_name: str
    album: Optional[str]
    year: Optional[int]
    original_key: str
    tempo: Optional[int]
    time_signature: str
    duration_seconds: Optional[int]
    genre: Optional[str]
    tags: List[str]
    default_scene_id: Optional[int]
    source: Optional[str]

    class Config:
        from_attributes = True


class SongDetailResponse(SongResponse):
    chord_chart: Optional[str]
    lyrics: Optional[str]
    notes: Optional[str]
    source_url: Optional[str]
    scene_settings: Dict[str, Any]


class ArtistSongLink(BaseModel):
    artist_id: int
    song_id: int
    enabled: bool = True
    is_lead_vocal: bool = False
    notes: Optional[str] = None


class SetlistEntry(BaseModel):
    song_id: int
    position: int
    scene_id: Optional[int] = None
    notes: Optional[str] = None


class TransposeRequest(BaseModel):
    target_key: str = Field(..., max_length=8)


class SongImport(BaseModel):
    source: str  # "chordify", "ultimate_guitar", "manual"
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    title: str
    artist_name: str
    original_key: str = "C"
    chord_chart: Optional[str] = None
    lyrics: Optional[str] = None
    tempo: Optional[int] = None


# ========== Song CRUD Endpoints ==========

@router.get("/", response_model=List[SongResponse])
async def list_songs(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    genre: Optional[str] = None,
    artist_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all songs with optional filtering."""
    query = select(Song)

    if search:
        query = query.where(
            Song.title.ilike(f"%{search}%") |
            Song.artist_name.ilike(f"%{search}%")
        )

    if genre:
        query = query.where(Song.genre == genre)

    query = query.order_by(Song.title).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/genres")
async def list_genres(db: AsyncSession = Depends(get_db)):
    """Get list of all genres in the database."""
    result = await db.execute(
        select(Song.genre).where(Song.genre.isnot(None)).distinct()
    )
    genres = [r[0] for r in result.all() if r[0]]
    return {"genres": sorted(genres)}


@router.get("/keys")
async def list_available_keys():
    """Get list of all available musical keys for transposition."""
    return {"keys": get_all_keys()}


@router.get("/{song_id}", response_model=SongDetailResponse)
async def get_song(song_id: int, db: AsyncSession = Depends(get_db)):
    """Get a song by ID with full details."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song


@router.post("/", response_model=SongResponse)
async def create_song(song: SongCreate, db: AsyncSession = Depends(get_db)):
    """Create a new song."""
    db_song = Song(**song.model_dump())
    db.add(db_song)
    await db.commit()
    await db.refresh(db_song)
    return db_song


@router.put("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: int,
    song_update: SongUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a song."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    update_data = song_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(song, field, value)

    await db.commit()
    await db.refresh(song)
    return song


@router.delete("/{song_id}")
async def delete_song(song_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a song."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    await db.delete(song)
    await db.commit()
    return {"status": "ok", "deleted": song_id}


# ========== Chord Chart & Transposition ==========

@router.get("/{song_id}/chart")
async def get_chord_chart(
    song_id: int,
    key: Optional[str] = None,
    format: str = Query("chordpro", regex="^(chordpro|text)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get chord chart for a song, optionally transposed to a different key.

    Args:
        key: Target key for transposition (optional)
        format: Output format - "chordpro" or "text"
    """
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    if not song.chord_chart:
        raise HTTPException(status_code=404, detail="Song has no chord chart")

    chart = song.chord_chart
    original_key = song.original_key

    # Transpose if requested
    if key and key != original_key:
        chart = transpose_to_key(chart, original_key, key)

    # Convert format if requested
    if format == "text":
        chart = chordpro_to_text(chart)

    return {
        "song_id": song_id,
        "title": song.title,
        "original_key": original_key,
        "display_key": key or original_key,
        "format": format,
        "chart": chart,
        "capo_suggestion": suggest_capo_position(original_key, key) if key else None
    }


@router.post("/{song_id}/transpose")
async def transpose_song(
    song_id: int,
    request: TransposeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Transpose a song's chord chart to a new key and save it.

    This updates the song's original_key and chord_chart.
    """
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    if not song.chord_chart:
        raise HTTPException(status_code=400, detail="Song has no chord chart")

    target_key = request.target_key
    original_key = song.original_key

    # Transpose the chart
    new_chart = transpose_to_key(song.chord_chart, original_key, target_key)

    # Update song
    song.chord_chart = new_chart
    song.original_key = target_key

    await db.commit()

    return {
        "status": "ok",
        "song_id": song_id,
        "original_key": original_key,
        "new_key": target_key
    }


@router.get("/{song_id}/print")
async def get_printable_chart(
    song_id: int,
    key: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a print-ready version of the chord chart.

    Returns HTML formatted for printing.
    """
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    chart = song.chord_chart or ""
    display_key = key or song.original_key

    if key and key != song.original_key:
        chart = transpose_to_key(chart, song.original_key, key)

    # Parse for metadata
    parsed = parse_chordpro(chart)
    text_chart = chordpro_to_text(chart)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{song.title} - {song.artist_name}</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            font-size: 14px;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{ font-size: 24px; margin-bottom: 5px; }}
        h2 {{ font-size: 18px; color: #666; margin-top: 0; }}
        .meta {{ color: #888; margin-bottom: 20px; }}
        .chart {{
            white-space: pre-wrap;
            line-height: 1.6;
        }}
        .chord {{ font-weight: bold; color: #0066cc; }}
        @media print {{
            body {{ font-size: 12px; }}
        }}
    </style>
</head>
<body>
    <h1>{song.title}</h1>
    <h2>{song.artist_name}</h2>
    <div class="meta">
        Key: {display_key} | Tempo: {song.tempo or 'N/A'} BPM | Time: {song.time_signature}
    </div>
    <div class="chart">{text_chart}</div>
</body>
</html>"""

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


# ========== Artist-Song Relationships ==========

@router.post("/artists/{artist_id}/songs/{song_id}")
async def link_artist_to_song(
    artist_id: int,
    song_id: int,
    is_lead_vocal: bool = False,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Link an artist to a song (artist knows/can play this song).
    """
    # Verify artist exists
    artist_result = await db.execute(select(Artist).where(Artist.id == artist_id))
    if not artist_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Artist not found")

    # Verify song exists
    song_result = await db.execute(select(Song).where(Song.id == song_id))
    if not song_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Song not found")

    # Create link
    await db.execute(
        artist_songs.insert().values(
            artist_id=artist_id,
            song_id=song_id,
            enabled=True,
            is_lead_vocal=is_lead_vocal,
            notes=notes
        ).prefix_with("OR REPLACE")
    )
    await db.commit()

    return {"status": "ok", "artist_id": artist_id, "song_id": song_id}


@router.delete("/artists/{artist_id}/songs/{song_id}")
async def unlink_artist_from_song(
    artist_id: int,
    song_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove song from artist's repertoire."""
    await db.execute(
        artist_songs.delete().where(
            and_(
                artist_songs.c.artist_id == artist_id,
                artist_songs.c.song_id == song_id
            )
        )
    )
    await db.commit()
    return {"status": "ok"}


@router.get("/artists/{artist_id}/songs")
async def get_artist_songs(
    artist_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all songs an artist can perform."""
    result = await db.execute(
        select(Song, artist_songs.c.is_lead_vocal, artist_songs.c.enabled)
        .join(artist_songs, Song.id == artist_songs.c.song_id)
        .where(artist_songs.c.artist_id == artist_id)
    )

    songs = []
    for row in result.all():
        song, is_lead, enabled = row
        songs.append({
            "id": song.id,
            "title": song.title,
            "artist_name": song.artist_name,
            "original_key": song.original_key,
            "is_lead_vocal": is_lead,
            "enabled": enabled
        })

    return {"artist_id": artist_id, "songs": songs}


@router.put("/artists/{artist_id}/songs/{song_id}/lead")
async def set_lead_vocalist(
    artist_id: int,
    song_id: int,
    is_lead: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Set/unset an artist as lead vocalist for a song."""
    await db.execute(
        artist_songs.update()
        .where(and_(
            artist_songs.c.artist_id == artist_id,
            artist_songs.c.song_id == song_id
        ))
        .values(is_lead_vocal=is_lead)
    )
    await db.commit()
    return {"status": "ok", "artist_id": artist_id, "song_id": song_id, "is_lead": is_lead}


# ========== Band Song Availability ==========

@router.get("/bands/{band_id}/available")
async def get_band_available_songs(
    band_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get songs available for a band's setlist.

    A song is available when ALL artists in the band have enabled it.
    """
    # Get band with artists
    band_result = await db.execute(
        select(Band).options(selectinload(Band.artists)).where(Band.id == band_id)
    )
    band = band_result.scalar_one_or_none()
    if not band:
        raise HTTPException(status_code=404, detail="Band not found")

    if not band.artists:
        return {"band_id": band_id, "available_songs": [], "message": "Band has no artists"}

    artist_ids = [a.id for a in band.artists]
    num_artists = len(artist_ids)

    # Find songs where ALL band members have enabled it
    # Get all songs linked to these artists

    # Query songs with count of how many of the band's artists have them enabled
    subquery = (
        select(
            artist_songs.c.song_id,
            func.count(artist_songs.c.artist_id).label('artist_count')
        )
        .where(artist_songs.c.artist_id.in_(artist_ids))
        .where(artist_songs.c.enabled == True)
        .group_by(artist_songs.c.song_id)
        .having(func.count(artist_songs.c.artist_id) == num_artists)
        .subquery()
    )

    # Join with songs to get full song details
    result = await db.execute(
        select(Song)
        .join(subquery, Song.id == subquery.c.song_id)
        .order_by(Song.title)
    )
    songs = result.scalars().all()

    # Get lead vocalist info for each song
    available_songs = []
    for song in songs:
        # Find who sings lead on this song from the band
        lead_result = await db.execute(
            select(Artist.name)
            .join(artist_songs, Artist.id == artist_songs.c.artist_id)
            .where(artist_songs.c.song_id == song.id)
            .where(artist_songs.c.artist_id.in_(artist_ids))
            .where(artist_songs.c.is_lead_vocal == True)
        )
        lead_vocals = [r[0] for r in lead_result.all()]

        available_songs.append({
            "id": song.id,
            "title": song.title,
            "artist_name": song.artist_name,
            "original_key": song.original_key,
            "tempo": song.tempo,
            "lead_vocals": lead_vocals
        })

    return {
        "band_id": band_id,
        "band_name": band.name,
        "artist_count": num_artists,
        "available_songs": available_songs
    }


# ========== Show Setlist ==========

@router.get("/shows/{show_id}/setlist")
async def get_show_setlist(
    show_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get the setlist for a show."""
    # Verify show exists
    show_result = await db.execute(select(Show).where(Show.id == show_id))
    show = show_result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    result = await db.execute(
        select(Song, setlist_songs.c.position, setlist_songs.c.scene_id, setlist_songs.c.notes)
        .join(setlist_songs, Song.id == setlist_songs.c.song_id)
        .where(setlist_songs.c.show_id == show_id)
        .order_by(setlist_songs.c.position)
    )

    setlist = []
    for row in result.all():
        song, position, scene_id, notes = row
        setlist.append({
            "position": position,
            "song": {
                "id": song.id,
                "title": song.title,
                "artist_name": song.artist_name,
                "original_key": song.original_key,
                "tempo": song.tempo,
                "duration_seconds": song.duration_seconds
            },
            "scene_id": scene_id,
            "notes": notes
        })

    return {
        "show_id": show_id,
        "show_name": show.name,
        "setlist": setlist,
        "total_duration": sum(s["song"]["duration_seconds"] or 0 for s in setlist)
    }


class SetlistReorder(BaseModel):
    song_ids: List[int]


@router.put("/shows/{show_id}/setlist/reorder")
async def reorder_setlist(
    show_id: int,
    reorder: SetlistReorder,
    db: AsyncSession = Depends(get_db)
):
    """Reorder songs in a setlist."""
    for position, song_id in enumerate(reorder.song_ids, start=1):
        await db.execute(
            setlist_songs.update()
            .where(and_(
                setlist_songs.c.show_id == show_id,
                setlist_songs.c.song_id == song_id
            ))
            .values(position=position)
        )
    await db.commit()
    return {"status": "ok", "new_order": reorder.song_ids}


@router.post("/shows/{show_id}/setlist")
async def add_to_setlist(
    show_id: int,
    entry: SetlistEntry,
    db: AsyncSession = Depends(get_db)
):
    """Add a song to a show's setlist."""
    # Verify show exists
    show_result = await db.execute(select(Show).where(Show.id == show_id))
    if not show_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Show not found")

    # Verify song exists
    song_result = await db.execute(select(Song).where(Song.id == entry.song_id))
    if not song_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Song not found")

    # Add to setlist
    await db.execute(
        setlist_songs.insert().values(
            show_id=show_id,
            song_id=entry.song_id,
            position=entry.position,
            scene_id=entry.scene_id,
            notes=entry.notes
        )
    )
    await db.commit()

    return {"status": "ok", "show_id": show_id, "song_id": entry.song_id}


@router.put("/shows/{show_id}/setlist/{song_id}")
async def update_setlist_entry(
    show_id: int,
    song_id: int,
    entry: SetlistEntry,
    db: AsyncSession = Depends(get_db)
):
    """Update a song's position or scene in the setlist."""
    await db.execute(
        setlist_songs.update()
        .where(and_(
            setlist_songs.c.show_id == show_id,
            setlist_songs.c.song_id == song_id
        ))
        .values(
            position=entry.position,
            scene_id=entry.scene_id,
            notes=entry.notes
        )
    )
    await db.commit()
    return {"status": "ok"}


@router.delete("/shows/{show_id}/setlist/{song_id}")
async def remove_from_setlist(
    show_id: int,
    song_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove a song from a show's setlist."""
    await db.execute(
        setlist_songs.delete().where(and_(
            setlist_songs.c.show_id == show_id,
            setlist_songs.c.song_id == song_id
        ))
    )
    await db.commit()
    return {"status": "ok"}


# ========== Scene Integration ==========

@router.put("/{song_id}/scene/{scene_id}")
async def set_song_scene(
    song_id: int,
    scene_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Set the default TF scene for a song."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    scene_result = await db.execute(select(Scene).where(Scene.id == scene_id))
    if not scene_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Scene not found")

    song.default_scene_id = scene_id
    await db.commit()

    return {"status": "ok", "song_id": song_id, "scene_id": scene_id}


@router.post("/{song_id}/scene/save", tags=["Quick Actions"])
async def quick_save_scene(
    song_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Quick button to save current mixer state to the song's scene.

    This stores the current TF-Rack state to the song's associated scene.
    """
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    if not song.default_scene_id:
        raise HTTPException(status_code=400, detail="Song has no associated scene")

    # Get the scene
    scene_result = await db.execute(
        select(Scene).where(Scene.id == song.default_scene_id)
    )
    scene = scene_result.scalar_one_or_none()
    if not scene:
        raise HTTPException(status_code=404, detail="Associated scene not found")

    # Store current mixer state to scene (reusing scene store logic)
    from app.models.channel import Channel
    channels_result = await db.execute(select(Channel))
    channels = channels_result.scalars().all()

    mixer_state = {}
    for channel in channels:
        ch_key = f"{channel.channel_type}_{channel.channel_number}"
        mixer_state[ch_key] = {
            "name": channel.name,
            "fader_level": channel.fader_level,
            "pan": channel.pan,
            "mute": channel.mute,
            "eq_enabled": channel.eq_enabled,
            "eq_settings": channel.eq_settings,
            "comp_enabled": channel.comp_enabled,
            "comp_settings": channel.comp_settings,
            "gate_enabled": channel.gate_enabled,
            "gate_settings": channel.gate_settings
        }

    scene.mixer_state = mixer_state
    await db.commit()

    # Also store to TF-Rack if connected
    tf_rack = getattr(request.app.state, 'tf_rack', None)
    if tf_rack and tf_rack.is_connected:
        tf_rack.store_scene(scene.scene_number, scene.name)

    return {
        "status": "ok",
        "song_id": song_id,
        "scene_id": scene.id,
        "scene_number": scene.scene_number,
        "message": f"Scene '{scene.name}' saved for song '{song.title}'"
    }


# ========== Import from External Sources ==========

@router.post("/import")
async def import_song(
    song_import: SongImport,
    db: AsyncSession = Depends(get_db)
):
    """
    Import a song from external source into local database.

    Supported sources: manual, chordify, ultimate_guitar
    """
    # Create song from import data
    db_song = Song(
        title=song_import.title,
        artist_name=song_import.artist_name,
        original_key=song_import.original_key,
        chord_chart=song_import.chord_chart,
        lyrics=song_import.lyrics,
        tempo=song_import.tempo,
        source=song_import.source,
        source_url=song_import.source_url,
        source_id=song_import.source_id
    )

    db.add(db_song)
    await db.commit()
    await db.refresh(db_song)

    return {
        "status": "ok",
        "song_id": db_song.id,
        "title": db_song.title,
        "source": db_song.source
    }


@router.get("/search/external")
async def search_external_songs(
    q: str = Query(..., min_length=2),
    source: str = Query("all", regex="^(all|chordify|ultimate_guitar)$")
):
    """
    Search for songs from external open source databases.

    Note: This endpoint provides search URLs/guidance as direct API access
    to these services may require API keys or have usage restrictions.

    Results should be imported using the /import endpoint.
    """
    search_urls = {
        "chordify": f"https://chordify.net/search/{q.replace(' ', '%20')}",
        "ultimate_guitar": f"https://www.ultimate-guitar.com/search.php?search_type=title&value={q.replace(' ', '%20')}",
        "songsterr": f"https://www.songsterr.com/?pattern={q.replace(' ', '%20')}",
        "e_chords": f"https://www.e-chords.com/search/{q.replace(' ', '%20')}"
    }

    return {
        "query": q,
        "message": "Use these URLs to find songs, then import manually with chord chart data",
        "search_urls": search_urls if source == "all" else {source: search_urls.get(source)},
        "import_endpoint": "/api/songs/import",
        "import_format": {
            "source": "chordify|ultimate_guitar|manual",
            "source_url": "URL where song was found (optional)",
            "title": "Song title (required)",
            "artist_name": "Artist name (required)",
            "original_key": "Key (default: C)",
            "chord_chart": "ChordPro format chord chart",
            "lyrics": "Plain text lyrics",
            "tempo": "BPM (optional)"
        }
    }
