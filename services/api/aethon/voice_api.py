"""Compatibility alias for the canonical voice API module."""

import sys

from app import voice_api as _voice_api

sys.modules[__name__] = _voice_api
