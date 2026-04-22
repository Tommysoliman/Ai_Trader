"""
Root-level Streamlit app wrapper for Streamlit Cloud deployment.
This file is required at the root level for Streamlit Cloud to find it.
It simply imports and runs the actual app from trading_system/.
"""

import sys
import os
from pathlib import Path

# Get absolute paths
ROOT = Path(__file__).parent.absolute()
TRADING_SYSTEM = ROOT / "trading_system"

# Add to Python path
if str(TRADING_SYSTEM) not in sys.path:
    sys.path.insert(0, str(TRADING_SYSTEM))

# Change to trading_system directory so relative imports work
os.chdir(TRADING_SYSTEM)

# Now run the main app (this will use relative imports from trading_system context)
from streamlit_app import *
