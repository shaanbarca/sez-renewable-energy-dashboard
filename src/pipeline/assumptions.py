"""
Re-export shim — all pipeline constants now live in src/assumptions.py.

Import from src.assumptions directly, or continue importing from here
(everything is re-exported transparently).
"""

from src.assumptions import *  # noqa: F401, F403
from src.assumptions import rp_kwh_to_usd_mwh  # explicit re-export for type checkers
