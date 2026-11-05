import os
import sys
from pathlib import Path

# Make tpmap / tpedit importable and allow GUI tests without a display
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["QT_QPA_PLATFORM"] = "offscreen"  # never open windows during tests
