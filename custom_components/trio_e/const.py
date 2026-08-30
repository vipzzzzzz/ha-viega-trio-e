"""Constants for the Viega Trio E integration."""

from __future__ import annotations

DOMAIN = "trio_e"

DEFAULT_DEVICE_ID = 1
DEFAULT_SCAN_INTERVAL = 10  # seconds; local polling, cheap
FAST_SCAN_INTERVAL = 2  # seconds while water is running

# The device caps mixed-water temperature itself; these bounds mirror the
# on-device UI range rather than the API's theoretical limits.
MIN_TEMP = 20.0
MAX_TEMP = 60.0
DEFAULT_TEMP = 38.0

# state values seen on the /state/ endpoint. "a" is idle; anything else means
# water is (or may be) moving. Refined as more states are observed.
STATE_IDLE = "a"

SERVICE_FILL_BATH = "fill_bath"
ATTR_TEMPERATURE = "temperature"
ATTR_VOLUME = "volume"
