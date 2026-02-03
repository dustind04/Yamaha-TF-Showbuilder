"""
Show, Band, and Artist models for organizing mixer configurations.
"""

from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# Association table for shows and bands (many-to-many)
show_bands = Table(
    'show_bands',
    Base.metadata,
    Column('show_id', Integer, ForeignKey('shows.id'), primary_key=True),
    Column('band_id', Integer, ForeignKey('bands.id'), primary_key=True),
    Column('set_order', Integer, default=0),  # Order in the show
    Column('set_time', String(32), nullable=True),  # e.g., "21:00"
)

# Association table for bands and artists (many-to-many)
band_artists = Table(
    'band_artists',
    Base.metadata,
    Column('band_id', Integer, ForeignKey('bands.id'), primary_key=True),
    Column('artist_id', Integer, ForeignKey('artists.id'), primary_key=True),
    Column('role', String(64), nullable=True),  # e.g., "Lead Vocals", "Drums"
)


class Show(Base):
    """
    A show/event containing multiple bands and their scenes.

    Represents a complete event like a concert, festival day, or venue night.
    """
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)

    # Event details
    venue = Column(String(128), nullable=True)
    date = Column(DateTime, nullable=True)
    load_in_time = Column(String(32), nullable=True)
    soundcheck_time = Column(String(32), nullable=True)
    doors_time = Column(String(32), nullable=True)
    show_time = Column(String(32), nullable=True)

    # Technical notes
    technical_notes = Column(Text, nullable=True)
    stage_plot_url = Column(String(512), nullable=True)

    # Global settings for the show
    house_eq_preset = Column(JSON, default=dict)  # House EQ settings
    default_aux_config = Column(JSON, default=dict)  # Default monitor configuration

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    bands = relationship("Band", secondary=show_bands, back_populates="shows")

    def __repr__(self):
        return f"<Show {self.name} at {self.venue}>"


class Band(Base):
    """
    A band/group with their preferred mixer settings.

    Contains channel assignments and scene configurations for a band.
    """
    __tablename__ = "bands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    genre = Column(String(64), nullable=True)

    # Contact info
    contact_name = Column(String(128), nullable=True)
    contact_email = Column(String(256), nullable=True)
    contact_phone = Column(String(32), nullable=True)

    # Technical requirements
    input_list = Column(JSON, default=list)  # List of required inputs
    monitor_requirements = Column(Text, nullable=True)
    stage_plot = Column(Text, nullable=True)  # Base64 or URL
    technical_rider = Column(Text, nullable=True)

    # Preferred settings
    channel_preset = Column(JSON, default=dict)  # Channel assignments and settings
    aux_preset = Column(JSON, default=dict)  # Monitor mix presets
    fx_preset = Column(JSON, default=dict)  # Effects settings

    # Scene references
    scene_ids = Column(JSON, default=list)  # List of associated scene IDs

    # E-ink labels for this band's setup
    eink_labels = Column(JSON, default=dict)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    shows = relationship("Show", secondary=show_bands, back_populates="bands")
    artists = relationship("Artist", secondary=band_artists, back_populates="bands")

    def __repr__(self):
        return f"<Band {self.name}>"


class Artist(Base):
    """
    An individual artist/performer with their preferred channel settings.

    Stores personal preferences for instruments, microphones, and monitor mixes.
    """
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)

    # Contact info
    email = Column(String(256), nullable=True)
    phone = Column(String(32), nullable=True)

    # Instrument/Role
    primary_instrument = Column(String(64), nullable=True)  # e.g., "Vocals", "Guitar"
    secondary_instruments = Column(JSON, default=list)

    # Preferred equipment
    preferred_mic = Column(String(64), nullable=True)  # e.g., "SM58", "Beta 87A"
    preferred_di = Column(String(64), nullable=True)  # e.g., "Radial J48"
    in_ear_model = Column(String(64), nullable=True)  # e.g., "Shure PSM300"

    # Channel presets
    channel_preset = Column(JSON, default=dict)  # EQ, comp, gate settings
    monitor_preset = Column(JSON, default=dict)  # Personal monitor mix preferences

    # E-ink label text
    label_text = Column(String(32), nullable=True)  # What to display on e-ink

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    bands = relationship("Band", secondary=band_artists, back_populates="artists")

    def __repr__(self):
        return f"<Artist {self.name} ({self.primary_instrument})>"


class InputList(Base):
    """
    Input list template for a band or show.

    Defines the channel-by-channel requirements for a performance.
    """
    __tablename__ = "input_lists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    band_id = Column(Integer, ForeignKey('bands.id'), nullable=True)

    # Input definitions as JSON array
    # Each entry: {channel, source, mic, stand, notes, artist_id}
    inputs = Column(JSON, default=list)

    # Example inputs format:
    # [
    #   {"channel": 1, "source": "Kick", "mic": "Beta 52", "stand": "Short boom", "notes": "Inside kick"},
    #   {"channel": 2, "source": "Snare Top", "mic": "SM57", "stand": "Clip", "notes": ""},
    #   {"channel": 3, "source": "Lead Vocal", "mic": "SM58", "stand": "Straight", "artist_id": 1},
    # ]

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<InputList {self.name}>"
