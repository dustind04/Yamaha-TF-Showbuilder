"""
Song model for setlist management.

Hierarchy: Show -> Band -> Artists -> Songs
Songs are enabled per artist, and become available for a band's setlist
when all required artists have enabled that song.
Each song can have associated TF scenes.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Table, JSON, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


# Association table for Artist <-> Song (many-to-many with enable status)
artist_songs = Table(
    'artist_songs',
    Base.metadata,
    Column('artist_id', Integer, ForeignKey('artists.id', ondelete='CASCADE'), primary_key=True),
    Column('song_id', Integer, ForeignKey('songs.id', ondelete='CASCADE'), primary_key=True),
    Column('enabled', Boolean, default=True),  # Artist can enable/disable songs they know
    Column('is_lead_vocal', Boolean, default=False),  # This artist sings lead on this song
    Column('notes', String(256), nullable=True)  # Artist-specific notes for the song
)

# Association table for Show Setlist (ordered songs)
setlist_songs = Table(
    'setlist_songs',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('show_id', Integer, ForeignKey('shows.id', ondelete='CASCADE')),
    Column('song_id', Integer, ForeignKey('songs.id', ondelete='CASCADE')),
    Column('position', Integer, nullable=False),  # Order in setlist
    Column('scene_id', Integer, ForeignKey('scenes.id', ondelete='SET NULL'), nullable=True),
    Column('notes', String(256), nullable=True)  # Show-specific notes
)


class Song(Base):
    """
    Song model for setlist management.

    Songs are sourced from external databases and stored locally.
    Each song can have chord charts, lyrics, and associated TF scenes.
    """
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    title = Column(String(128), nullable=False, index=True)
    artist_name = Column(String(128), nullable=False, index=True)  # Original artist
    album = Column(String(128), nullable=True)
    year = Column(Integer, nullable=True)

    # Musical info
    original_key = Column(String(8), default="C")  # Original key of the song
    tempo = Column(Integer, nullable=True)  # BPM
    time_signature = Column(String(8), default="4/4")
    duration_seconds = Column(Integer, nullable=True)

    # Chord chart and lyrics
    chord_chart = Column(Text, nullable=True)  # Chord chart in ChordPro format
    lyrics = Column(Text, nullable=True)

    # Source info
    source = Column(String(64), nullable=True)  # Where the song was imported from
    source_url = Column(String(512), nullable=True)  # Original URL
    source_id = Column(String(128), nullable=True)  # ID in source database

    # TF Integration
    default_scene_id = Column(Integer, ForeignKey('scenes.id', ondelete='SET NULL'), nullable=True)
    scene_settings = Column(JSON, default=dict)  # Additional scene tweaks for this song

    # Metadata
    genre = Column(String(64), nullable=True)
    tags = Column(JSON, default=list)  # Tags for filtering
    notes = Column(Text, nullable=True)  # General notes

    # Relationships
    artists = relationship("Artist", secondary=artist_songs, back_populates="songs")
    default_scene = relationship("Scene", foreign_keys=[default_scene_id])


class ChordChart(Base):
    """
    Stores transposed versions of chord charts for songs.
    """
    __tablename__ = "chord_charts"

    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey('songs.id', ondelete='CASCADE'), nullable=False)
    key = Column(String(8), nullable=False)  # The key this chart is in
    chart_data = Column(Text, nullable=False)  # ChordPro format chart

    # Relationships
    song = relationship("Song", backref="transposed_charts")
