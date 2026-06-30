"""Lydian System — research module for Lydian-based modal analysis.

Based on Brett Clement's "A New Lydian Theory for Frank Zappa's Modal Music"
(Music Theory Spectrum 36, 2014), which adapts George Russell's Lydian
Chromatic Concept for compositional analysis.
"""

from jazz21.lydian.system import (
    LydianSystem,
    distance_in_fifths,
    lydian_for_position,
    parent_lydian,
)

__all__ = [
    "LydianSystem",
    "distance_in_fifths",
    "lydian_for_position",
    "parent_lydian",
]
