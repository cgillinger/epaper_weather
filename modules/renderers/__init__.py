#!/usr/bin/env python3
"""
Renderers Module - Dynamic Module Rendering Pipeline
E-Paper Weather Daemon - Fas 3

Exponerar renderer-klasser för enkel import:
- ModuleRenderer: Abstract base class
- PrecipitationRenderer: Nederbörd-modul 
- ModuleFactory: Factory för renderer-skapande
"""

from .base_renderer import ModuleRenderer, LegacyModuleRenderer
from .precipitation_renderer import PrecipitationRenderer  
from .module_factory import ModuleFactory

__all__ = [
    'ModuleRenderer',
    'LegacyModuleRenderer', 
    'PrecipitationRenderer',
    'ModuleFactory'
]

__version__ = '3.0.0'
__description__ = 'Dynamic Module Rendering Pipeline för E-Paper Weather Daemon'