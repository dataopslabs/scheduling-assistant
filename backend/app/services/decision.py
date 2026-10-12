"""Compatibility entry point: `decide` runs the guarded scheduling flow."""
from .scheduling_service import run_scheduling_flow as decide

__all__ = ["decide"]
