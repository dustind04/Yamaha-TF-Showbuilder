"""
Yamaha TF-Rack OSC Protocol Service

Implements communication with Yamaha TF series mixers using OSC protocol.
Based on Yamaha TF StageMix protocol documentation.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher

logger = logging.getLogger(__name__)


@dataclass
class ChannelState:
    """Current state of a channel."""
    name: str = ""
    color: str = "white"
    icon: str = ""
    fader: float = -float('inf')
    pan: float = 0.0
    mute: bool = False
    on: bool = True
    phantom: bool = False
    gain: float = 0.0
    eq_enabled: bool = True
    eq: Dict[str, Any] = field(default_factory=dict)
    comp_enabled: bool = False
    comp: Dict[str, Any] = field(default_factory=dict)
    gate_enabled: bool = False
    gate: Dict[str, Any] = field(default_factory=dict)


class TFRackService:
    """
    Service for communicating with Yamaha TF-Rack via OSC.

    OSC Address Reference (TF Series):
    - /ch/{ch}/mix/fader - Channel fader level
    - /ch/{ch}/mix/on - Channel on/off
    - /ch/{ch}/mix/pan - Channel pan
    - /ch/{ch}/config/name - Channel name
    - /ch/{ch}/config/color - Channel color
    - /ch/{ch}/preamp/gain - Input gain
    - /ch/{ch}/preamp/+48v - Phantom power
    - /ch/{ch}/eq/on - EQ on/off
    - /ch/{ch}/eq/{band}/freq - EQ frequency
    - /ch/{ch}/eq/{band}/gain - EQ gain
    - /ch/{ch}/eq/{band}/q - EQ Q
    - /ch/{ch}/dyn/on - Compressor on/off
    - /ch/{ch}/gate/on - Gate on/off
    """

    # Channel count constants for TF-Rack
    INPUT_CHANNELS = 32
    STEREO_INPUTS = 2
    AUX_BUSES = 20
    MATRIX_OUTPUTS = 4
    DCA_GROUPS = 8

    # OSC address patterns
    OSC_PATTERNS = {
        "fader": "/ch/{ch}/mix/fader",
        "on": "/ch/{ch}/mix/on",
        "pan": "/ch/{ch}/mix/pan",
        "mute": "/ch/{ch}/mix/mute",
        "name": "/ch/{ch}/config/name",
        "color": "/ch/{ch}/config/color",
        "icon": "/ch/{ch}/config/icon",
        "gain": "/ch/{ch}/preamp/gain",
        "phantom": "/ch/{ch}/preamp/+48v",
        "phase": "/ch/{ch}/preamp/polarity",
        "eq_on": "/ch/{ch}/eq/on",
        "eq_hpf_on": "/ch/{ch}/eq/hpf/on",
        "eq_hpf_freq": "/ch/{ch}/eq/hpf/freq",
        "eq_low_freq": "/ch/{ch}/eq/1/freq",
        "eq_low_gain": "/ch/{ch}/eq/1/gain",
        "eq_low_q": "/ch/{ch}/eq/1/q",
        "eq_low_type": "/ch/{ch}/eq/1/type",
        "eq_lowmid_freq": "/ch/{ch}/eq/2/freq",
        "eq_lowmid_gain": "/ch/{ch}/eq/2/gain",
        "eq_lowmid_q": "/ch/{ch}/eq/2/q",
        "eq_highmid_freq": "/ch/{ch}/eq/3/freq",
        "eq_highmid_gain": "/ch/{ch}/eq/3/gain",
        "eq_highmid_q": "/ch/{ch}/eq/3/q",
        "eq_high_freq": "/ch/{ch}/eq/4/freq",
        "eq_high_gain": "/ch/{ch}/eq/4/gain",
        "eq_high_q": "/ch/{ch}/eq/4/q",
        "eq_high_type": "/ch/{ch}/eq/4/type",
        "comp_on": "/ch/{ch}/dyn/on",
        "comp_thresh": "/ch/{ch}/dyn/thresh",
        "comp_ratio": "/ch/{ch}/dyn/ratio",
        "comp_attack": "/ch/{ch}/dyn/attack",
        "comp_release": "/ch/{ch}/dyn/release",
        "comp_gain": "/ch/{ch}/dyn/gain",
        "comp_knee": "/ch/{ch}/dyn/knee",
        "gate_on": "/ch/{ch}/gate/on",
        "gate_thresh": "/ch/{ch}/gate/thresh",
        "gate_range": "/ch/{ch}/gate/range",
        "gate_attack": "/ch/{ch}/gate/attack",
        "gate_hold": "/ch/{ch}/gate/hold",
        "gate_release": "/ch/{ch}/gate/release",
        "send": "/ch/{ch}/mix/{aux}/level",
        "send_on": "/ch/{ch}/mix/{aux}/on",
    }

    def __init__(self, host: str, port: int = 49280):
        """
        Initialize TF-Rack service.

        Args:
            host: IP address of TF-Rack
            port: OSC port (default 49280)
        """
        self.host = host
        self.port = port
        self.client: Optional[SimpleUDPClient] = None
        self.server: Optional[AsyncIOOSCUDPServer] = None
        self.dispatcher = Dispatcher()
        self.is_connected = False
        self._callbacks: Dict[str, List[Callable]] = {}
        self._channel_states: Dict[int, ChannelState] = {}

        # Initialize channel states
        for i in range(1, self.INPUT_CHANNELS + 1):
            self._channel_states[i] = ChannelState()

        # Set up OSC message handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up OSC message dispatchers."""
        # Catch-all handler for debugging
        self.dispatcher.set_default_handler(self._handle_message)

        # Specific handlers for channel parameters
        self.dispatcher.map("/ch/*/mix/fader", self._handle_fader)
        self.dispatcher.map("/ch/*/mix/on", self._handle_on)
        self.dispatcher.map("/ch/*/config/name", self._handle_name)
        self.dispatcher.map("/ch/*/config/color", self._handle_color)
        self.dispatcher.map("/meters/*", self._handle_meters)

    def _handle_message(self, address: str, *args):
        """Default message handler."""
        logger.debug(f"OSC received: {address} = {args}")
        # Notify callbacks
        for callback in self._callbacks.get("message", []):
            callback(address, args)

    def _handle_fader(self, address: str, *args):
        """Handle fader level changes."""
        ch = self._extract_channel(address)
        if ch and args:
            self._channel_states[ch].fader = self._osc_to_db(args[0])
            self._notify_change("fader", ch, self._channel_states[ch].fader)

    def _handle_on(self, address: str, *args):
        """Handle channel on/off changes."""
        ch = self._extract_channel(address)
        if ch and args:
            self._channel_states[ch].on = bool(args[0])
            self._notify_change("on", ch, self._channel_states[ch].on)

    def _handle_name(self, address: str, *args):
        """Handle channel name changes."""
        ch = self._extract_channel(address)
        if ch and args:
            self._channel_states[ch].name = str(args[0])
            self._notify_change("name", ch, self._channel_states[ch].name)

    def _handle_color(self, address: str, *args):
        """Handle channel color changes."""
        ch = self._extract_channel(address)
        if ch and args:
            self._channel_states[ch].color = self._color_index_to_name(args[0])
            self._notify_change("color", ch, self._channel_states[ch].color)

    def _handle_meters(self, address: str, *args):
        """Handle meter data."""
        self._notify_change("meters", 0, args)

    def _extract_channel(self, address: str) -> Optional[int]:
        """Extract channel number from OSC address."""
        parts = address.split("/")
        try:
            if len(parts) >= 3 and parts[1] == "ch":
                return int(parts[2])
        except ValueError:
            pass
        return None

    def _notify_change(self, param: str, channel: int, value: Any):
        """Notify registered callbacks of parameter changes."""
        for callback in self._callbacks.get(param, []):
            callback(channel, value)
        for callback in self._callbacks.get("any", []):
            callback(param, channel, value)

    async def connect(self) -> bool:
        """
        Establish connection to TF-Rack.

        Returns:
            True if connection successful
        """
        try:
            # Create OSC client for sending messages
            self.client = SimpleUDPClient(self.host, self.port)

            # Create OSC server for receiving responses
            self.server = await AsyncIOOSCUDPServer.create(
                ("0.0.0.0", self.port + 1),
                self.dispatcher
            )

            # Send sync request to verify connection
            self.client.send_message("/info", [])

            self.is_connected = True
            logger.info(f"Connected to TF-Rack at {self.host}:{self.port}")

            # Start sync task
            asyncio.create_task(self._sync_loop())

            return True

        except Exception as e:
            logger.error(f"Failed to connect to TF-Rack: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from TF-Rack."""
        self.is_connected = False
        if self.server:
            # Close server
            pass
        logger.info("Disconnected from TF-Rack")

    async def _sync_loop(self):
        """Periodic sync with TF-Rack."""
        while self.is_connected:
            try:
                # Request meter data
                self.client.send_message("/meters", [1])
                await asyncio.sleep(0.1)  # 10Hz update rate
            except Exception as e:
                logger.error(f"Sync error: {e}")
                await asyncio.sleep(1)

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for parameter changes."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    # ========== Channel Control Methods ==========

    def set_fader(self, channel: int, db: float):
        """
        Set channel fader level.

        Args:
            channel: Channel number (1-32)
            db: Level in dB (-inf to +10)
        """
        address = self.OSC_PATTERNS["fader"].format(ch=channel)
        value = self._db_to_osc(db)
        self.client.send_message(address, [value])

    def set_channel_on(self, channel: int, on: bool):
        """Set channel on/off state."""
        address = self.OSC_PATTERNS["on"].format(ch=channel)
        self.client.send_message(address, [1 if on else 0])

    def set_mute(self, channel: int, mute: bool):
        """Set channel mute state."""
        address = self.OSC_PATTERNS["mute"].format(ch=channel)
        self.client.send_message(address, [1 if mute else 0])

    def set_pan(self, channel: int, pan: float):
        """Set channel pan (-100 to +100)."""
        address = self.OSC_PATTERNS["pan"].format(ch=channel)
        value = (pan + 100) / 200  # Convert to 0-1
        self.client.send_message(address, [value])

    def set_name(self, channel: int, name: str):
        """Set channel name (max 8 characters)."""
        address = self.OSC_PATTERNS["name"].format(ch=channel)
        self.client.send_message(address, [name[:8]])

    def set_color(self, channel: int, color: str):
        """Set channel color."""
        address = self.OSC_PATTERNS["color"].format(ch=channel)
        color_index = self._color_name_to_index(color)
        self.client.send_message(address, [color_index])

    def set_gain(self, channel: int, db: float):
        """Set input gain (-12 to +60 dB)."""
        address = self.OSC_PATTERNS["gain"].format(ch=channel)
        self.client.send_message(address, [db])

    def set_phantom(self, channel: int, on: bool):
        """Set phantom power (+48V)."""
        address = self.OSC_PATTERNS["phantom"].format(ch=channel)
        self.client.send_message(address, [1 if on else 0])

    # ========== EQ Methods ==========

    def set_eq_enabled(self, channel: int, enabled: bool):
        """Enable/disable channel EQ."""
        address = self.OSC_PATTERNS["eq_on"].format(ch=channel)
        self.client.send_message(address, [1 if enabled else 0])

    def set_eq_hpf(self, channel: int, enabled: bool, frequency: float = 80):
        """Set high-pass filter."""
        self.client.send_message(
            self.OSC_PATTERNS["eq_hpf_on"].format(ch=channel),
            [1 if enabled else 0]
        )
        self.client.send_message(
            self.OSC_PATTERNS["eq_hpf_freq"].format(ch=channel),
            [frequency]
        )

    def set_eq_band(self, channel: int, band: int, freq: float, gain: float, q: float):
        """
        Set EQ band parameters.

        Args:
            channel: Channel number
            band: Band number (1=low, 2=low-mid, 3=high-mid, 4=high)
            freq: Frequency in Hz
            gain: Gain in dB
            q: Q factor
        """
        band_map = {1: "low", 2: "lowmid", 3: "highmid", 4: "high"}
        band_name = band_map.get(band, "low")

        self.client.send_message(
            self.OSC_PATTERNS[f"eq_{band_name}_freq"].format(ch=channel),
            [freq]
        )
        self.client.send_message(
            self.OSC_PATTERNS[f"eq_{band_name}_gain"].format(ch=channel),
            [gain]
        )
        self.client.send_message(
            self.OSC_PATTERNS[f"eq_{band_name}_q"].format(ch=channel),
            [q]
        )

    # ========== Compressor Methods ==========

    def set_comp_enabled(self, channel: int, enabled: bool):
        """Enable/disable channel compressor."""
        address = self.OSC_PATTERNS["comp_on"].format(ch=channel)
        self.client.send_message(address, [1 if enabled else 0])

    def set_comp_params(self, channel: int, threshold: float, ratio: float,
                        attack: float, release: float, gain: float, knee: str = "medium"):
        """Set compressor parameters."""
        ch = channel
        self.client.send_message(self.OSC_PATTERNS["comp_thresh"].format(ch=ch), [threshold])
        self.client.send_message(self.OSC_PATTERNS["comp_ratio"].format(ch=ch), [ratio])
        self.client.send_message(self.OSC_PATTERNS["comp_attack"].format(ch=ch), [attack])
        self.client.send_message(self.OSC_PATTERNS["comp_release"].format(ch=ch), [release])
        self.client.send_message(self.OSC_PATTERNS["comp_gain"].format(ch=ch), [gain])
        knee_value = {"hard": 0, "medium": 1, "soft": 2}.get(knee, 1)
        self.client.send_message(self.OSC_PATTERNS["comp_knee"].format(ch=ch), [knee_value])

    # ========== Gate Methods ==========

    def set_gate_enabled(self, channel: int, enabled: bool):
        """Enable/disable channel gate."""
        address = self.OSC_PATTERNS["gate_on"].format(ch=channel)
        self.client.send_message(address, [1 if enabled else 0])

    def set_gate_params(self, channel: int, threshold: float, range_db: float,
                        attack: float, hold: float, release: float):
        """Set gate parameters."""
        ch = channel
        self.client.send_message(self.OSC_PATTERNS["gate_thresh"].format(ch=ch), [threshold])
        self.client.send_message(self.OSC_PATTERNS["gate_range"].format(ch=ch), [range_db])
        self.client.send_message(self.OSC_PATTERNS["gate_attack"].format(ch=ch), [attack])
        self.client.send_message(self.OSC_PATTERNS["gate_hold"].format(ch=ch), [hold])
        self.client.send_message(self.OSC_PATTERNS["gate_release"].format(ch=ch), [release])

    # ========== Aux Send Methods ==========

    def set_aux_send(self, channel: int, aux: int, level: float):
        """Set aux send level."""
        address = self.OSC_PATTERNS["send"].format(ch=channel, aux=aux)
        self.client.send_message(address, [self._db_to_osc(level)])

    def set_aux_send_on(self, channel: int, aux: int, on: bool):
        """Set aux send on/off."""
        address = self.OSC_PATTERNS["send_on"].format(ch=channel, aux=aux)
        self.client.send_message(address, [1 if on else 0])

    # ========== Scene Methods ==========

    def recall_scene(self, scene_number: int):
        """Recall a scene from TF-Rack memory."""
        self.client.send_message("/scene/recall", [scene_number])

    def store_scene(self, scene_number: int, name: str = ""):
        """Store current settings to a scene."""
        self.client.send_message("/scene/store", [scene_number, name])

    # ========== Utility Methods ==========

    def get_channel_state(self, channel: int) -> Optional[ChannelState]:
        """Get current state of a channel."""
        return self._channel_states.get(channel)

    def request_channel_info(self, channel: int):
        """Request full channel information from TF-Rack."""
        patterns = ["fader", "on", "pan", "name", "color", "gain", "phantom",
                    "eq_on", "comp_on", "gate_on"]
        for pattern in patterns:
            address = self.OSC_PATTERNS[pattern].format(ch=channel)
            self.client.send_message(address, [])

    def request_all_channels(self):
        """Request information for all channels."""
        for ch in range(1, self.INPUT_CHANNELS + 1):
            self.request_channel_info(ch)

    # ========== Conversion Helpers ==========

    @staticmethod
    def _db_to_osc(db: float) -> float:
        """Convert dB to OSC fader value (0-1)."""
        if db <= -90:
            return 0.0
        elif db >= 10:
            return 1.0
        else:
            # TF fader scale approximation
            return (db + 90) / 100

    @staticmethod
    def _osc_to_db(value: float) -> float:
        """Convert OSC fader value (0-1) to dB."""
        if value <= 0:
            return -float('inf')
        elif value >= 1:
            return 10.0
        else:
            return (value * 100) - 90

    @staticmethod
    def _color_name_to_index(color: str) -> int:
        """Convert color name to TF color index."""
        colors = {
            "off": 0, "red": 1, "green": 2, "yellow": 3,
            "blue": 4, "magenta": 5, "cyan": 6, "white": 7
        }
        return colors.get(color.lower(), 7)

    @staticmethod
    def _color_index_to_name(index: int) -> str:
        """Convert TF color index to color name."""
        colors = ["off", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
        return colors[index] if 0 <= index < len(colors) else "white"
