import pytz
from datetime import datetime
from typing import Dict

def get_us_and_egyptian_time() -> Dict[str, str]:
    """
    Get current time in both US (Eastern) and Egyptian time zones
    Returns time in 12-hour AM/PM format
    """
    # US Eastern Time
    us_tz = pytz.timezone('America/New_York')
    us_time = datetime.now(us_tz)
    us_time_str = us_time.strftime('%I:%M:%S %p')
    us_date = us_time.strftime('%A, %B %d, %Y')
    
    # Egyptian Time
    egypt_tz = pytz.timezone('Africa/Cairo')
    egypt_time = datetime.now(egypt_tz)
    egypt_time_str = egypt_time.strftime('%I:%M:%S %p')
    egypt_date = egypt_time.strftime('%A, %B %d, %Y')
    
    return {
        'us_time': us_time_str,
        'us_date': us_date,
        'egypt_time': egypt_time_str,
        'egypt_date': egypt_date,
        'us_timezone': 'US Eastern Time (ET)',
        'egypt_timezone': 'Egypt (CAT)'
    }

def format_time_display() -> str:
    """
    Format current time for display in Streamlit
    """
    times = get_us_and_egyptian_time()
    return f"""
    **🕐 Current Time:**
    
    🇺🇸 **US Eastern Time:** {times['us_time']} | {times['us_date']}
    
    🇪🇬 **Egyptian Time:** {times['egypt_time']} | {times['egypt_date']}
    """
