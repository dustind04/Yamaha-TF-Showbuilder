"""
Input Preset models for microphone and instrument configurations.

Like Yamaha's QuickPro presets, these define channel settings for common
input sources (vocals, drums, guitars, etc.) with specific microphone models.
"""

from sqlalchemy import Column, Integer, String, Text, JSON, Boolean
from app.core.database import Base


class InputPreset(Base):
    """
    Input preset defining settings for a specific input type and microphone.

    Examples:
    - Lead Vocal (Shure SM58)
    - Lead Vocal (Shure Beta 87A)
    - Kick Drum (Shure Beta 52)
    - Electric Guitar (Shure SM57)
    - Acoustic Guitar DI (Radial J48)
    """
    __tablename__ = "input_presets"

    id = Column(Integer, primary_key=True, index=True)

    # Preset identification
    name = Column(String(128), nullable=False)  # e.g., "Lead Vocal"
    category = Column(String(64), nullable=False)  # e.g., "Vocals", "Drums", "Guitars"
    subcategory = Column(String(64), nullable=True)  # e.g., "Kick", "Snare" for drums

    # Equipment
    microphone = Column(String(64), nullable=True)  # e.g., "Shure SM58"
    mic_manufacturer = Column(String(64), nullable=True)  # e.g., "Shure"
    mic_model = Column(String(64), nullable=True)  # e.g., "SM58"
    mic_type = Column(String(32), nullable=True)  # dynamic, condenser, ribbon
    requires_phantom = Column(Boolean, default=False)

    # DI/Direct info
    di_box = Column(String(64), nullable=True)  # e.g., "Radial J48"
    is_direct = Column(Boolean, default=False)  # True for DI inputs

    # Stand/mount info
    stand_type = Column(String(64), nullable=True)  # straight, boom, short boom, clip
    notes = Column(Text, nullable=True)

    # Channel processing presets
    gain_preset = Column(Integer, default=0)  # Suggested starting gain in dB
    phantom_power = Column(Boolean, default=False)
    phase_invert = Column(Boolean, default=False)

    # HPF
    hpf_enabled = Column(Boolean, default=True)
    hpf_frequency = Column(Integer, default=80)

    # EQ preset
    eq_enabled = Column(Boolean, default=True)
    eq_settings = Column(JSON, default=lambda: {
        "low": {"frequency": 100, "gain": 0, "q": 1.0, "type": "shelf"},
        "low_mid": {"frequency": 400, "gain": 0, "q": 1.0, "type": "peak"},
        "high_mid": {"frequency": 2500, "gain": 0, "q": 1.0, "type": "peak"},
        "high": {"frequency": 8000, "gain": 0, "q": 1.0, "type": "shelf"}
    })

    # Compressor preset
    comp_enabled = Column(Boolean, default=False)
    comp_settings = Column(JSON, default=lambda: {
        "threshold": -10,
        "ratio": 4.0,
        "attack": 10,
        "release": 100,
        "gain": 0,
        "knee": "medium"
    })

    # Gate preset
    gate_enabled = Column(Boolean, default=False)
    gate_settings = Column(JSON, default=lambda: {
        "threshold": -50,
        "range": -80,
        "attack": 1,
        "hold": 50,
        "release": 100
    })

    # E-ink display
    default_label = Column(String(32), nullable=True)  # Default label for this input type
    icon = Column(String(32), nullable=True)  # Icon identifier

    # Color coding
    suggested_color = Column(String(16), default="white")

    # Is this a factory preset or user-created?
    is_factory = Column(Boolean, default=False)

    def __repr__(self):
        mic_info = f" ({self.microphone})" if self.microphone else ""
        return f"<InputPreset {self.name}{mic_info}>"


# Factory preset data for initial database population
FACTORY_PRESETS = [
    # ========== VOCALS ==========
    {
        "name": "Lead Vocal",
        "category": "Vocals",
        "microphone": "Shure SM58",
        "mic_manufacturer": "Shure",
        "mic_model": "SM58",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "stand_type": "straight",
        "hpf_enabled": True,
        "hpf_frequency": 100,
        "eq_settings": {
            "low": {"frequency": 200, "gain": -3, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 400, "gain": -2, "q": 1.5, "type": "peak"},
            "high_mid": {"frequency": 3000, "gain": 3, "q": 1.0, "type": "peak"},
            "high": {"frequency": 10000, "gain": 2, "q": 1.0, "type": "shelf"}
        },
        "comp_enabled": True,
        "comp_settings": {"threshold": -15, "ratio": 3.0, "attack": 10, "release": 150, "gain": 3, "knee": "medium"},
        "default_label": "LEAD VOX",
        "suggested_color": "red",
        "is_factory": True
    },
    {
        "name": "Lead Vocal",
        "category": "Vocals",
        "microphone": "Shure Beta 58A",
        "mic_manufacturer": "Shure",
        "mic_model": "Beta 58A",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "stand_type": "straight",
        "hpf_enabled": True,
        "hpf_frequency": 100,
        "eq_settings": {
            "low": {"frequency": 200, "gain": -2, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 350, "gain": -2, "q": 1.5, "type": "peak"},
            "high_mid": {"frequency": 4000, "gain": 2, "q": 1.0, "type": "peak"},
            "high": {"frequency": 12000, "gain": 1, "q": 1.0, "type": "shelf"}
        },
        "comp_enabled": True,
        "comp_settings": {"threshold": -15, "ratio": 3.0, "attack": 10, "release": 150, "gain": 3, "knee": "medium"},
        "default_label": "LEAD VOX",
        "suggested_color": "red",
        "is_factory": True
    },
    {
        "name": "Lead Vocal",
        "category": "Vocals",
        "microphone": "Shure Beta 87A",
        "mic_manufacturer": "Shure",
        "mic_model": "Beta 87A",
        "mic_type": "condenser",
        "requires_phantom": True,
        "stand_type": "straight",
        "hpf_enabled": True,
        "hpf_frequency": 80,
        "eq_settings": {
            "low": {"frequency": 150, "gain": -2, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 300, "gain": -1, "q": 1.5, "type": "peak"},
            "high_mid": {"frequency": 5000, "gain": 2, "q": 1.0, "type": "peak"},
            "high": {"frequency": 12000, "gain": 1, "q": 1.0, "type": "shelf"}
        },
        "comp_enabled": True,
        "comp_settings": {"threshold": -18, "ratio": 3.5, "attack": 8, "release": 120, "gain": 4, "knee": "medium"},
        "default_label": "LEAD VOX",
        "suggested_color": "red",
        "is_factory": True
    },
    {
        "name": "Lead Vocal Wireless",
        "category": "Vocals",
        "microphone": "Shure ULX-D Beta 58",
        "mic_manufacturer": "Shure",
        "mic_model": "ULX-D",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "notes": "Wireless handheld with Beta 58 capsule",
        "hpf_enabled": True,
        "hpf_frequency": 100,
        "comp_enabled": True,
        "comp_settings": {"threshold": -15, "ratio": 3.0, "attack": 10, "release": 150, "gain": 3, "knee": "medium"},
        "default_label": "LEAD VOX",
        "suggested_color": "red",
        "is_factory": True
    },
    {
        "name": "Backup Vocal",
        "category": "Vocals",
        "microphone": "Shure SM58",
        "mic_manufacturer": "Shure",
        "mic_model": "SM58",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "stand_type": "straight",
        "hpf_enabled": True,
        "hpf_frequency": 120,
        "comp_enabled": True,
        "comp_settings": {"threshold": -12, "ratio": 3.0, "attack": 15, "release": 150, "gain": 2, "knee": "medium"},
        "default_label": "BV",
        "suggested_color": "magenta",
        "is_factory": True
    },

    # ========== DRUMS ==========
    {
        "name": "Kick Drum Inside",
        "category": "Drums",
        "subcategory": "Kick",
        "microphone": "Shure Beta 52A",
        "mic_manufacturer": "Shure",
        "mic_model": "Beta 52A",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "stand_type": "short boom",
        "notes": "Inside kick drum, near beater",
        "hpf_enabled": False,
        "eq_settings": {
            "low": {"frequency": 60, "gain": 4, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 400, "gain": -4, "q": 2.0, "type": "peak"},
            "high_mid": {"frequency": 3500, "gain": 3, "q": 1.5, "type": "peak"},
            "high": {"frequency": 8000, "gain": 2, "q": 1.0, "type": "shelf"}
        },
        "gate_enabled": True,
        "gate_settings": {"threshold": -40, "range": -60, "attack": 0.5, "hold": 50, "release": 100},
        "comp_enabled": True,
        "comp_settings": {"threshold": -10, "ratio": 4.0, "attack": 5, "release": 80, "gain": 3, "knee": "hard"},
        "default_label": "KICK",
        "suggested_color": "blue",
        "is_factory": True
    },
    {
        "name": "Kick Drum Outside",
        "category": "Drums",
        "subcategory": "Kick",
        "microphone": "AKG D112",
        "mic_manufacturer": "AKG",
        "mic_model": "D112",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "stand_type": "short boom",
        "notes": "Outside kick drum for sub",
        "hpf_enabled": False,
        "eq_settings": {
            "low": {"frequency": 50, "gain": 3, "q": 0.8, "type": "shelf"},
            "low_mid": {"frequency": 300, "gain": -3, "q": 2.0, "type": "peak"},
            "high_mid": {"frequency": 2000, "gain": 0, "q": 1.0, "type": "peak"},
            "high": {"frequency": 6000, "gain": -2, "q": 1.0, "type": "shelf"}
        },
        "gate_enabled": True,
        "gate_settings": {"threshold": -45, "range": -60, "attack": 1, "hold": 80, "release": 150},
        "default_label": "KICK OUT",
        "suggested_color": "blue",
        "is_factory": True
    },
    {
        "name": "Snare Top",
        "category": "Drums",
        "subcategory": "Snare",
        "microphone": "Shure SM57",
        "mic_manufacturer": "Shure",
        "mic_model": "SM57",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "stand_type": "short boom",
        "hpf_enabled": True,
        "hpf_frequency": 100,
        "eq_settings": {
            "low": {"frequency": 200, "gain": -2, "q": 1.5, "type": "peak"},
            "low_mid": {"frequency": 400, "gain": -3, "q": 2.0, "type": "peak"},
            "high_mid": {"frequency": 5000, "gain": 4, "q": 1.0, "type": "peak"},
            "high": {"frequency": 10000, "gain": 2, "q": 1.0, "type": "shelf"}
        },
        "gate_enabled": True,
        "gate_settings": {"threshold": -35, "range": -40, "attack": 0.5, "hold": 30, "release": 80},
        "comp_enabled": True,
        "comp_settings": {"threshold": -8, "ratio": 4.0, "attack": 3, "release": 60, "gain": 2, "knee": "hard"},
        "default_label": "SNARE",
        "suggested_color": "blue",
        "is_factory": True
    },
    {
        "name": "Hi-Hat",
        "category": "Drums",
        "subcategory": "Cymbals",
        "microphone": "AKG C451",
        "mic_manufacturer": "AKG",
        "mic_model": "C451",
        "mic_type": "condenser",
        "requires_phantom": True,
        "stand_type": "short boom",
        "hpf_enabled": True,
        "hpf_frequency": 400,
        "eq_settings": {
            "low": {"frequency": 500, "gain": -4, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 1000, "gain": 0, "q": 1.0, "type": "peak"},
            "high_mid": {"frequency": 6000, "gain": 2, "q": 1.0, "type": "peak"},
            "high": {"frequency": 12000, "gain": 1, "q": 1.0, "type": "shelf"}
        },
        "gate_enabled": True,
        "gate_settings": {"threshold": -30, "range": -20, "attack": 0.5, "hold": 20, "release": 50},
        "default_label": "HI-HAT",
        "suggested_color": "cyan",
        "is_factory": True
    },
    {
        "name": "Tom",
        "category": "Drums",
        "subcategory": "Toms",
        "microphone": "Sennheiser MD421",
        "mic_manufacturer": "Sennheiser",
        "mic_model": "MD421",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "stand_type": "clip",
        "hpf_enabled": True,
        "hpf_frequency": 80,
        "eq_settings": {
            "low": {"frequency": 100, "gain": 3, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 400, "gain": -4, "q": 2.0, "type": "peak"},
            "high_mid": {"frequency": 3000, "gain": 3, "q": 1.5, "type": "peak"},
            "high": {"frequency": 8000, "gain": 1, "q": 1.0, "type": "shelf"}
        },
        "gate_enabled": True,
        "gate_settings": {"threshold": -35, "range": -50, "attack": 1, "hold": 40, "release": 100},
        "default_label": "TOM",
        "suggested_color": "blue",
        "is_factory": True
    },
    {
        "name": "Overhead L",
        "category": "Drums",
        "subcategory": "Overheads",
        "microphone": "AKG C414",
        "mic_manufacturer": "AKG",
        "mic_model": "C414",
        "mic_type": "condenser",
        "requires_phantom": True,
        "stand_type": "tall boom",
        "hpf_enabled": True,
        "hpf_frequency": 200,
        "eq_settings": {
            "low": {"frequency": 300, "gain": -3, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 800, "gain": 0, "q": 1.0, "type": "peak"},
            "high_mid": {"frequency": 4000, "gain": 2, "q": 1.0, "type": "peak"},
            "high": {"frequency": 12000, "gain": 2, "q": 1.0, "type": "shelf"}
        },
        "default_label": "OH L",
        "suggested_color": "cyan",
        "is_factory": True
    },
    {
        "name": "Overhead R",
        "category": "Drums",
        "subcategory": "Overheads",
        "microphone": "AKG C414",
        "mic_manufacturer": "AKG",
        "mic_model": "C414",
        "mic_type": "condenser",
        "requires_phantom": True,
        "stand_type": "tall boom",
        "hpf_enabled": True,
        "hpf_frequency": 200,
        "eq_settings": {
            "low": {"frequency": 300, "gain": -3, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 800, "gain": 0, "q": 1.0, "type": "peak"},
            "high_mid": {"frequency": 4000, "gain": 2, "q": 1.0, "type": "peak"},
            "high": {"frequency": 12000, "gain": 2, "q": 1.0, "type": "shelf"}
        },
        "default_label": "OH R",
        "suggested_color": "cyan",
        "is_factory": True
    },

    # ========== GUITARS ==========
    {
        "name": "Electric Guitar",
        "category": "Guitars",
        "microphone": "Shure SM57",
        "mic_manufacturer": "Shure",
        "mic_model": "SM57",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "stand_type": "short boom",
        "notes": "On speaker cone, off-axis for less brightness",
        "hpf_enabled": True,
        "hpf_frequency": 80,
        "eq_settings": {
            "low": {"frequency": 150, "gain": -2, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 400, "gain": 0, "q": 1.0, "type": "peak"},
            "high_mid": {"frequency": 3000, "gain": 2, "q": 1.5, "type": "peak"},
            "high": {"frequency": 8000, "gain": -2, "q": 1.0, "type": "shelf"}
        },
        "default_label": "ELEC GTR",
        "suggested_color": "yellow",
        "is_factory": True
    },
    {
        "name": "Acoustic Guitar",
        "category": "Guitars",
        "microphone": "AKG C414",
        "mic_manufacturer": "AKG",
        "mic_model": "C414",
        "mic_type": "condenser",
        "requires_phantom": True,
        "stand_type": "boom",
        "notes": "Aimed at 12th fret",
        "hpf_enabled": True,
        "hpf_frequency": 100,
        "eq_settings": {
            "low": {"frequency": 200, "gain": -2, "q": 1.5, "type": "peak"},
            "low_mid": {"frequency": 500, "gain": 0, "q": 1.0, "type": "peak"},
            "high_mid": {"frequency": 3000, "gain": 2, "q": 1.0, "type": "peak"},
            "high": {"frequency": 10000, "gain": 2, "q": 1.0, "type": "shelf"}
        },
        "comp_enabled": True,
        "comp_settings": {"threshold": -15, "ratio": 3.0, "attack": 15, "release": 150, "gain": 2, "knee": "soft"},
        "default_label": "AC GTR",
        "suggested_color": "yellow",
        "is_factory": True
    },
    {
        "name": "Acoustic Guitar DI",
        "category": "Guitars",
        "di_box": "Radial J48",
        "is_direct": True,
        "hpf_enabled": True,
        "hpf_frequency": 80,
        "eq_settings": {
            "low": {"frequency": 150, "gain": 0, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 400, "gain": -2, "q": 1.5, "type": "peak"},
            "high_mid": {"frequency": 2500, "gain": 2, "q": 1.0, "type": "peak"},
            "high": {"frequency": 8000, "gain": 3, "q": 1.0, "type": "shelf"}
        },
        "comp_enabled": True,
        "comp_settings": {"threshold": -15, "ratio": 3.0, "attack": 15, "release": 150, "gain": 2, "knee": "soft"},
        "default_label": "AC GTR DI",
        "suggested_color": "yellow",
        "is_factory": True
    },

    # ========== BASS ==========
    {
        "name": "Bass Guitar DI",
        "category": "Bass",
        "di_box": "Radial JDI",
        "is_direct": True,
        "hpf_enabled": True,
        "hpf_frequency": 40,
        "eq_settings": {
            "low": {"frequency": 80, "gain": 2, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 250, "gain": -2, "q": 1.5, "type": "peak"},
            "high_mid": {"frequency": 1500, "gain": 2, "q": 1.0, "type": "peak"},
            "high": {"frequency": 4000, "gain": 0, "q": 1.0, "type": "shelf"}
        },
        "comp_enabled": True,
        "comp_settings": {"threshold": -12, "ratio": 4.0, "attack": 20, "release": 200, "gain": 3, "knee": "medium"},
        "default_label": "BASS",
        "suggested_color": "green",
        "is_factory": True
    },
    {
        "name": "Bass Amp",
        "category": "Bass",
        "microphone": "Sennheiser MD421",
        "mic_manufacturer": "Sennheiser",
        "mic_model": "MD421",
        "mic_type": "dynamic",
        "requires_phantom": False,
        "stand_type": "short boom",
        "hpf_enabled": True,
        "hpf_frequency": 50,
        "eq_settings": {
            "low": {"frequency": 100, "gain": 3, "q": 1.0, "type": "shelf"},
            "low_mid": {"frequency": 300, "gain": -2, "q": 1.5, "type": "peak"},
            "high_mid": {"frequency": 2000, "gain": 2, "q": 1.0, "type": "peak"},
            "high": {"frequency": 5000, "gain": 0, "q": 1.0, "type": "shelf"}
        },
        "comp_enabled": True,
        "comp_settings": {"threshold": -12, "ratio": 4.0, "attack": 20, "release": 200, "gain": 3, "knee": "medium"},
        "default_label": "BASS AMP",
        "suggested_color": "green",
        "is_factory": True
    },

    # ========== KEYS ==========
    {
        "name": "Keyboard Stereo L",
        "category": "Keys",
        "is_direct": True,
        "hpf_enabled": True,
        "hpf_frequency": 50,
        "eq_enabled": False,
        "comp_enabled": False,
        "default_label": "KEYS L",
        "suggested_color": "magenta",
        "is_factory": True
    },
    {
        "name": "Keyboard Stereo R",
        "category": "Keys",
        "is_direct": True,
        "hpf_enabled": True,
        "hpf_frequency": 50,
        "eq_enabled": False,
        "comp_enabled": False,
        "default_label": "KEYS R",
        "suggested_color": "magenta",
        "is_factory": True
    },
]
