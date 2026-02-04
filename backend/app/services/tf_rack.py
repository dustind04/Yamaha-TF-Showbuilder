"""
Yamaha TF-Rack RCP Protocol Service

Implements communication with Yamaha TF series mixers using the RCP (Remote Control Protocol)
over TCP. Based on community documentation and Bitfocus Companion implementation.

Protocol Reference:
- TCP port 49280
- Text-based commands, newline delimited
- Commands: set, get, ssrecall_ex
- Responses: OK, OKm, NOTIFY, ERROR

Sources:
- https://github.com/BrenekH/yamaha-rcp-docs
- https://github.com/Dom-TC/Yamaha-TF-Control
- https://github.com/bitfocus/companion-module-yamaha-rcp
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ChannelState:
    """Current state of a channel."""
    name: str = ""
    color: str = "white"
    icon: str = ""
    fader: float = -90.0  # dB, -90 (off) to +10
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
    Service for communicating with Yamaha TF-Rack via RCP (Remote Control Protocol).

    RCP Protocol Reference (TF Series):
    - TCP connection on port 49280
    - Commands are text-based, terminated with newline

    Command Examples:
    - set MIXER:Current/InCh/Fader/Level {ch} 0 {value} - Set fader (value = dB * 100)
    - set MIXER:Current/InCh/Fader/On {ch} 0 {0|1} - Channel on/off
    - ssrecall_ex scene_a {num} - Recall scene from bank A (0-99)
    - ssrecall_ex scene_b {num} - Recall scene from bank B (0-99)
    """

    # Channel count constants for TF-Rack
    INPUT_CHANNELS = 32
    STEREO_INPUTS = 2
    AUX_BUSES = 20
    MATRIX_OUTPUTS = 4
    DCA_GROUPS = 8

    # RCP command patterns (channel numbers are 0-indexed in protocol)
    RCP_COMMANDS = {
        "fader_level": "set MIXER:Current/InCh/Fader/Level {ch} 0 {value}",
        "channel_on": "set MIXER:Current/InCh/Fader/On {ch} 0 {value}",
        "channel_name": "set MIXER:Current/InCh/Label/Name {ch} 0 \"{value}\"",
        "pan": "set MIXER:Current/InCh/ToSt/Pan {ch} 0 {value}",
        "gain": "set MIXER:Current/InCh/Preamp/Gain {ch} 0 {value}",
        "phantom": "set MIXER:Current/InCh/Preamp/48V {ch} 0 {value}",
        "eq_on": "set MIXER:Current/InCh/Eq/On {ch} 0 {value}",
        "comp_on": "set MIXER:Current/InCh/Dyn1/On {ch} 0 {value}",
        "gate_on": "set MIXER:Current/InCh/Dyn2/On {ch} 0 {value}",
        "scene_recall_a": "ssrecall_ex scene_a {scene}",
        "scene_recall_b": "ssrecall_ex scene_b {scene}",
        "scene_store_a": "ssstore_ex scene_a {scene}",
        "scene_store_b": "ssstore_ex scene_b {scene}",
        "dca_fader": "set MIXER:Current/DcaCh/Fader/Level {ch} 0 {value}",
        "dca_on": "set MIXER:Current/DcaCh/Fader/On {ch} 0 {value}",
        "get_fader": "get MIXER:Current/InCh/Fader/Level {ch} 0",
        "get_channel_on": "get MIXER:Current/InCh/Fader/On {ch} 0",
    }

    def __init__(self, host: str = "192.168.1.100", port: int = 49280):
        """
        Initialize TF-Rack service.

        Args:
            host: IP address of TF-Rack
            port: TCP port (default 49280)
        """
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.is_connected = False
        self._callbacks: Dict[str, List[Callable]] = {}
        self._channel_states: Dict[int, ChannelState] = {}
        self._lock = asyncio.Lock()
        self._receive_task: Optional[asyncio.Task] = None

        # Initialize channel states
        for i in range(1, self.INPUT_CHANNELS + 1):
            self._channel_states[i] = ChannelState()

    async def connect(self) -> bool:
        """
        Establish TCP connection to TF-Rack.

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to TF-Rack at {self.host}:{self.port}...")
            print(f"Connecting to TF-Rack at {self.host}:{self.port}...")

            # Create TCP connection with timeout
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0
            )

            self.is_connected = True
            logger.info(f"Connected to TF-Rack at {self.host}:{self.port}")
            print(f"✓ Connected to TF-Rack at {self.host}:{self.port}")

            # Start background task to receive responses
            self._receive_task = asyncio.create_task(self._receive_loop())

            return True

        except asyncio.TimeoutError:
            logger.error(f"Connection to TF-Rack timed out ({self.host}:{self.port})")
            print(f"✗ Connection to TF-Rack timed out ({self.host}:{self.port})")
            self.is_connected = False
            return False
        except ConnectionRefusedError:
            logger.error(f"Connection refused by TF-Rack ({self.host}:{self.port})")
            print(f"✗ Connection refused by TF-Rack ({self.host}:{self.port})")
            self.is_connected = False
            return False
        except OSError as e:
            logger.error(f"Network error connecting to TF-Rack: {e}")
            print(f"✗ Network error connecting to TF-Rack: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Failed to connect to TF-Rack: {e}")
            print(f"✗ Failed to connect to TF-Rack: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from TF-Rack."""
        self.is_connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
            self.reader = None

        logger.info("Disconnected from TF-Rack")

    async def _receive_loop(self):
        """Background task to receive and process responses from TF-Rack."""
        try:
            while self.is_connected and self.reader:
                try:
                    line = await asyncio.wait_for(
                        self.reader.readline(),
                        timeout=30.0
                    )
                    if not line:
                        logger.warning("TF-Rack connection closed")
                        break

                    response = line.decode('utf-8').strip()
                    if response:
                        self._handle_response(response)

                except asyncio.TimeoutError:
                    # Send keepalive
                    pass
                except Exception as e:
                    logger.error(f"Error receiving from TF-Rack: {e}")
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Receive loop error: {e}")
        finally:
            if self.is_connected:
                self.is_connected = False
                logger.warning("TF-Rack connection lost")

    def _handle_response(self, response: str):
        """Handle response from TF-Rack."""
        logger.debug(f"TF-Rack response: {response}")

        if response.startswith("OK get"):
            # Response to a get command - parse the value
            self._handle_get_response(response)
        elif response.startswith("OK"):
            # Command acknowledged
            pass
        elif response.startswith("NOTIFY"):
            # Parameter change notification
            self._handle_notify(response)
        elif response.startswith("ERROR"):
            logger.error(f"TF-Rack error: {response}")

        # Notify callbacks
        for callback in self._callbacks.get("response", []):
            callback(response)

    def _handle_get_response(self, response: str):
        """Handle responses to get commands."""
        # Format: OK get MIXER:Current/InCh/Fader/Level 0 0 -1000
        # parts: [OK, get, MIXER:..., ch, 0, value]
        try:
            parts = response.split()
            if len(parts) >= 6 and "InCh/Fader/Level" in response:
                ch = int(parts[3]) + 1  # Convert 0-indexed to 1-indexed
                value = int(parts[5])
                db = value / 100.0
                if ch in self._channel_states:
                    self._channel_states[ch].fader = db
                    print(f"  CH{ch} fader: {db}dB")
            elif len(parts) >= 6 and "InCh/Fader/On" in response:
                ch = int(parts[3]) + 1
                value = int(parts[5])
                if ch in self._channel_states:
                    self._channel_states[ch].on = bool(value)
                    print(f"  CH{ch} on: {bool(value)}")
            elif len(parts) >= 6 and "InCh/Label/Name" in response:
                ch = int(parts[3]) + 1
                # Name is everything after the 5th part, stripped of quotes
                name = " ".join(parts[5:]).strip('"')
                if ch in self._channel_states:
                    self._channel_states[ch].name = name
                    print(f"  CH{ch} name: '{name}'")
        except Exception as e:
            print(f"Could not parse get response '{response}': {e}")

    def _handle_notify(self, response: str):
        """Handle NOTIFY messages (parameter changes from console)."""
        # Parse NOTIFY messages to update local state
        # Format: NOTIFY set MIXER:Current/InCh/Fader/Level 0 0 -1000
        try:
            parts = response.split()
            if len(parts) >= 5 and "InCh/Fader/Level" in response:
                ch = int(parts[3]) + 1  # Convert 0-indexed to 1-indexed
                value = int(parts[5])
                db = value / 100.0
                if ch in self._channel_states:
                    self._channel_states[ch].fader = db
                    self._notify_change("fader", ch, db)
            elif len(parts) >= 5 and "InCh/Fader/On" in response:
                ch = int(parts[3]) + 1
                value = int(parts[5])
                if ch in self._channel_states:
                    self._channel_states[ch].on = bool(value)
                    self._notify_change("on", ch, bool(value))
        except Exception as e:
            logger.debug(f"Could not parse NOTIFY: {e}")

    async def _send_command(self, command: str) -> bool:
        """
        Send a command to TF-Rack.

        Args:
            command: RCP command string (without newline)

        Returns:
            True if command was sent successfully
        """
        if not self.is_connected or not self.writer:
            logger.warning(f"Cannot send command: not connected")
            return False

        async with self._lock:
            try:
                full_command = f"{command}\n"
                self.writer.write(full_command.encode('utf-8'))
                await self.writer.drain()
                logger.debug(f"Sent: {command}")
                return True
            except Exception as e:
                logger.error(f"Failed to send command: {e}")
                self.is_connected = False
                return False

    def _notify_change(self, param: str, channel: int, value: Any):
        """Notify callbacks of parameter change."""
        for callback in self._callbacks.get(param, []):
            callback(channel, value)
        for callback in self._callbacks.get("any", []):
            callback(param, channel, value)

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for parameter changes."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def get_channel_state(self, channel: int) -> Optional[ChannelState]:
        """Get cached state for a channel."""
        return self._channel_states.get(channel)

    # ========== Channel Control Methods ==========

    def _db_to_rcp(self, db: float) -> int:
        """Convert dB value to RCP protocol value (dB * 100)."""
        if db <= -138:
            return -32768  # -infinity
        return int(db * 100)

    def _rcp_to_db(self, value: int) -> float:
        """Convert RCP protocol value to dB."""
        if value <= -32768:
            return -138.0  # -infinity
        return value / 100.0

    def set_fader(self, channel: int, db: float) -> bool:
        """
        Set channel fader level (sync wrapper for backwards compatibility).

        For new code, use set_fader_async instead.
        """
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.set_fader_async(channel, db))
                return True
            else:
                return loop.run_until_complete(self.set_fader_async(channel, db))
        except Exception as e:
            logger.error(f"set_fader error: {e}")
            return False

    async def set_fader_async(self, channel: int, db: float) -> bool:
        """
        Set channel fader level.

        Args:
            channel: Channel number (1-32)
            db: Level in dB (-138 to +10)
        """
        if channel < 1 or channel > self.INPUT_CHANNELS:
            logger.error(f"Invalid channel number: {channel}")
            return False

        ch_idx = channel - 1  # Convert to 0-indexed
        value = self._db_to_rcp(db)
        command = self.RCP_COMMANDS["fader_level"].format(ch=ch_idx, value=value)

        success = await self._send_command(command)
        if success:
            self._channel_states[channel].fader = db
        return success

    def set_channel_on(self, channel: int, on: bool) -> bool:
        """
        Set channel on/off state (sync wrapper).
        """
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.set_channel_on_async(channel, on))
                return True
            else:
                return loop.run_until_complete(self.set_channel_on_async(channel, on))
        except Exception as e:
            logger.error(f"set_channel_on error: {e}")
            return False

    async def set_channel_on_async(self, channel: int, on: bool) -> bool:
        """
        Set channel on/off state.

        Note: In TF protocol, On=1 means channel is ON (passing audio),
        On=0 means channel is OFF (muted).
        """
        if channel < 1 or channel > self.INPUT_CHANNELS:
            logger.error(f"Invalid channel number: {channel}")
            return False

        ch_idx = channel - 1
        value = 1 if on else 0
        command = self.RCP_COMMANDS["channel_on"].format(ch=ch_idx, value=value)

        success = await self._send_command(command)
        if success:
            self._channel_states[channel].on = on
        return success

    def set_mute(self, channel: int, mute: bool) -> bool:
        """
        Set channel mute state (sync wrapper).
        This is the inverse of channel on - mute=True means channel is OFF.
        """
        return self.set_channel_on(channel, not mute)

    async def set_mute_async(self, channel: int, mute: bool) -> bool:
        """Set channel mute state (async)."""
        return await self.set_channel_on_async(channel, not mute)

    def set_pan(self, channel: int, pan: float) -> bool:
        """Set channel pan (sync wrapper)."""
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.set_pan_async(channel, pan))
                return True
            else:
                return loop.run_until_complete(self.set_pan_async(channel, pan))
        except Exception as e:
            logger.error(f"set_pan error: {e}")
            return False

    async def set_pan_async(self, channel: int, pan: float) -> bool:
        """
        Set channel pan (-100 to +100).
        Protocol uses 0-127 where 64 is center.
        """
        if channel < 1 or channel > self.INPUT_CHANNELS:
            return False

        ch_idx = channel - 1
        # Convert -100..+100 to 0..127
        value = int((pan + 100) / 200 * 127)
        value = max(0, min(127, value))
        command = self.RCP_COMMANDS["pan"].format(ch=ch_idx, value=value)

        success = await self._send_command(command)
        if success:
            self._channel_states[channel].pan = pan
        return success

    def set_name(self, channel: int, name: str) -> bool:
        """Set channel name (sync wrapper)."""
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.set_name_async(channel, name))
                return True
            else:
                return loop.run_until_complete(self.set_name_async(channel, name))
        except Exception as e:
            logger.error(f"set_name error: {e}")
            return False

    async def set_name_async(self, channel: int, name: str) -> bool:
        """Set channel name (max 8 characters)."""
        if channel < 1 or channel > self.INPUT_CHANNELS:
            return False

        ch_idx = channel - 1
        name = name[:8]  # TF supports max 8 chars
        command = self.RCP_COMMANDS["channel_name"].format(ch=ch_idx, value=name)

        success = await self._send_command(command)
        if success:
            self._channel_states[channel].name = name
        return success

    def set_gain(self, channel: int, db: float) -> bool:
        """Set input gain (sync wrapper)."""
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.set_gain_async(channel, db))
                return True
            else:
                return loop.run_until_complete(self.set_gain_async(channel, db))
        except Exception as e:
            logger.error(f"set_gain error: {e}")
            return False

    async def set_gain_async(self, channel: int, db: float) -> bool:
        """Set input gain (-12 to +60 dB)."""
        if channel < 1 or channel > self.INPUT_CHANNELS:
            return False

        ch_idx = channel - 1
        value = self._db_to_rcp(db)
        command = self.RCP_COMMANDS["gain"].format(ch=ch_idx, value=value)

        success = await self._send_command(command)
        if success:
            self._channel_states[channel].gain = db
        return success

    def set_phantom(self, channel: int, on: bool) -> bool:
        """Set phantom power (sync wrapper)."""
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.set_phantom_async(channel, on))
                return True
            else:
                return loop.run_until_complete(self.set_phantom_async(channel, on))
        except Exception as e:
            logger.error(f"set_phantom error: {e}")
            return False

    async def set_phantom_async(self, channel: int, on: bool) -> bool:
        """Set phantom power (+48V)."""
        if channel < 1 or channel > self.INPUT_CHANNELS:
            return False

        ch_idx = channel - 1
        value = 1 if on else 0
        command = self.RCP_COMMANDS["phantom"].format(ch=ch_idx, value=value)

        success = await self._send_command(command)
        if success:
            self._channel_states[channel].phantom = on
        return success

    # ========== Scene Methods ==========

    def recall_scene(self, scene_number: int, bank: str = "a") -> bool:
        """Recall scene (sync wrapper)."""
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.recall_scene_async(scene_number, bank))
                return True
            else:
                return loop.run_until_complete(self.recall_scene_async(scene_number, bank))
        except Exception as e:
            logger.error(f"recall_scene error: {e}")
            return False

    async def recall_scene_async(self, scene: int, bank: str = "a") -> bool:
        """
        Recall a scene from TF-Rack's internal memory.

        Args:
            scene: Scene number (0-99)
            bank: Scene bank ('a' or 'b')
        """
        if scene < 0 or scene > 99:
            logger.error(f"Invalid scene number: {scene}")
            return False

        bank = bank.lower()
        if bank not in ('a', 'b'):
            logger.error(f"Invalid bank: {bank}")
            return False

        command_key = f"scene_recall_{bank}"
        command = self.RCP_COMMANDS[command_key].format(scene=scene)

        logger.info(f"Recalling scene {scene} from bank {bank.upper()}")
        print(f"Recalling TF-Rack scene {scene} from bank {bank.upper()}")
        return await self._send_command(command)

    def store_scene(self, scene_number: int, bank: str = "a") -> bool:
        """Store scene (sync wrapper)."""
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.store_scene_async(scene_number, bank))
                return True
            else:
                return loop.run_until_complete(self.store_scene_async(scene_number, bank))
        except Exception as e:
            logger.error(f"store_scene error: {e}")
            return False

    async def store_scene_async(self, scene: int, bank: str = "a") -> bool:
        """
        Store current state to a scene in TF-Rack's internal memory.

        Args:
            scene: Scene number (0-99)
            bank: Scene bank ('a' or 'b')
        """
        if scene < 0 or scene > 99:
            logger.error(f"Invalid scene number: {scene}")
            return False

        bank = bank.lower()
        if bank not in ('a', 'b'):
            return False

        command_key = f"scene_store_{bank}"
        command = self.RCP_COMMANDS[command_key].format(scene=scene)

        logger.info(f"Storing scene {scene} to bank {bank.upper()}")
        return await self._send_command(command)

    # ========== DCA Methods ==========

    async def set_dca_fader(self, dca: int, db: float) -> bool:
        """Set DCA fader level (DCA 1-8)."""
        if dca < 1 or dca > self.DCA_GROUPS:
            return False

        dca_idx = dca - 1
        value = self._db_to_rcp(db)
        command = self.RCP_COMMANDS["dca_fader"].format(ch=dca_idx, value=value)
        return await self._send_command(command)

    async def set_dca_on(self, dca: int, on: bool) -> bool:
        """Set DCA on/off state (DCA 1-8)."""
        if dca < 1 or dca > self.DCA_GROUPS:
            return False

        dca_idx = dca - 1
        value = 1 if on else 0
        command = self.RCP_COMMANDS["dca_on"].format(ch=dca_idx, value=value)
        return await self._send_command(command)

    # ========== Utility Methods ==========

    def request_all_channels(self):
        """Request current state of all channels from TF-Rack (sync wrapper)."""
        if not self.is_connected:
            return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.request_all_channels_async())
        except Exception as e:
            logger.error(f"request_all_channels error: {e}")

    async def request_all_channels_async(self):
        """Request current state of all channels from TF-Rack."""
        for ch in range(self.INPUT_CHANNELS):
            await self._send_command(f"get MIXER:Current/InCh/Fader/Level {ch} 0")
            await self._send_command(f"get MIXER:Current/InCh/Fader/On {ch} 0")
            await self._send_command(f"get MIXER:Current/InCh/Label/Name {ch} 0")
            await asyncio.sleep(0.02)  # Small delay to not overwhelm
        # Wait for responses to come back
        await asyncio.sleep(0.5)

    # ========== EQ/Dynamics Stubs (for API compatibility) ==========

    def set_eq_enabled(self, channel: int, enabled: bool) -> bool:
        """Enable/disable channel EQ."""
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                ch_idx = channel - 1
                value = 1 if enabled else 0
                command = self.RCP_COMMANDS["eq_on"].format(ch=ch_idx, value=value)
                asyncio.create_task(self._send_command(command))
                return True
        except Exception:
            pass
        return False

    def set_comp_enabled(self, channel: int, enabled: bool) -> bool:
        """Enable/disable channel compressor."""
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                ch_idx = channel - 1
                value = 1 if enabled else 0
                command = self.RCP_COMMANDS["comp_on"].format(ch=ch_idx, value=value)
                asyncio.create_task(self._send_command(command))
                return True
        except Exception:
            pass
        return False

    def set_gate_enabled(self, channel: int, enabled: bool) -> bool:
        """Enable/disable channel gate."""
        if not self.is_connected:
            return False
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                ch_idx = channel - 1
                value = 1 if enabled else 0
                command = self.RCP_COMMANDS["gate_on"].format(ch=ch_idx, value=value)
                asyncio.create_task(self._send_command(command))
                return True
        except Exception:
            pass
        return False

    # ========== Color Helpers (for API compatibility) ==========

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
