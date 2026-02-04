"""
Prevent Windows from sleeping while the application is running.

Uses the Windows SetThreadExecutionState API to keep the system awake.
On non-Windows platforms, this module does nothing.
"""

import sys
import logging

logger = logging.getLogger(__name__)

_sleep_prevented = False


def prevent_sleep():
    """
    Prevent the system from sleeping.

    On Windows, this uses SetThreadExecutionState to tell the OS
    that the application requires the system to stay awake.
    """
    global _sleep_prevented

    if sys.platform != 'win32':
        logger.debug("Sleep prevention only supported on Windows")
        return False

    try:
        import ctypes

        # Execution state flags
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002  # Also keeps display on
        ES_AWAYMODE_REQUIRED = 0x00000040  # Enables away mode (Windows Vista+)

        # Set execution state to prevent sleep
        # ES_CONTINUOUS makes it persistent until we clear it
        result = ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )

        if result == 0:
            logger.warning("SetThreadExecutionState failed")
            return False

        _sleep_prevented = True
        logger.info("System sleep prevention enabled - computer will stay awake")
        print("✓ Sleep prevention enabled - computer will stay awake while server runs")
        return True

    except Exception as e:
        logger.error(f"Failed to prevent sleep: {e}")
        return False


def allow_sleep():
    """
    Allow the system to sleep again.

    Call this when shutting down to restore normal sleep behavior.
    """
    global _sleep_prevented

    if sys.platform != 'win32':
        return

    if not _sleep_prevented:
        return

    try:
        import ctypes

        ES_CONTINUOUS = 0x80000000

        # Clear all flags by just setting ES_CONTINUOUS
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

        _sleep_prevented = False
        logger.info("System sleep prevention disabled - normal sleep behavior restored")

    except Exception as e:
        logger.error(f"Failed to restore sleep: {e}")


def is_sleep_prevented() -> bool:
    """Check if sleep prevention is currently active."""
    return _sleep_prevented
