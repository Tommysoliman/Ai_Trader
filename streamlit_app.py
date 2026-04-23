"""
Root-level Streamlit app wrapper for Streamlit Cloud deployment.
This file is required at the root level for Streamlit Cloud to find it.
It runs the actual app from trading_system/.
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

# Change working directory and import the app
os.chdir(TRADING_SYSTEM)

# Import and run the trading system app
from streamlit_app import *
