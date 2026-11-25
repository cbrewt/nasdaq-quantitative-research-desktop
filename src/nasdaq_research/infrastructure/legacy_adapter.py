"""Temporary compatibility boundary for the byte-identical V1.2 modules."""
from pathlib import Path
import sys
legacy=Path(__file__).resolve().parent / 'validated_v12'
if str(legacy) not in sys.path: sys.path.insert(0,str(legacy))
from Stock_Screener import Nasdaq_21_Session_Screener as engine
