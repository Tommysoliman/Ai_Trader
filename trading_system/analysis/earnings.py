"""
Earnings Calendar Check using yfinance
Skip tickers with earnings within N days to avoid unpredictable event risk
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

class EarningsChecker:
    """Check if ticker has earnings within threshold"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.skip_within_days = config.get('earnings', {}).get('skip_within_days', 3)
    
    def get_earnings_dates(self, ticker: str) -> Optional[list]:
        """Fetch earnings dates from yfinance for a ticker"""
        try:
            ticker_obj = yf.Ticker(ticker)
            
            # yfinance doesn't have a direct earnings calendar API,
            # but we can try to get info from quarterly financials
            # The most reliable way is through the info dict
            info = ticker_obj.info
            
            # Look for earnings dates in info
            earnings_dates = []
            
            if 'earningsDate' in info:
                earnings_dates.append(info['earningsDate'])
            
            if 'nextEarningsDate' in info:
                earnings_dates.append(info['nextEarningsDate'])
            
            return earnings_dates if earnings_dates else None
        
        except Exception as e:
            print(f"⚠️  Error fetching earnings dates for {ticker}: {e}")
            return None
    
    def check_earnings_within_threshold(self, ticker: str) -> Tuple[bool, Optional[str]]:
        """Check if earnings are within threshold days
        Returns: (skip_ticker, earnings_date_str)
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            # Get next earnings date
            next_earnings = info.get('nextEarningsDate')
            
            if not next_earnings:
                return False, None
            
            # Convert to datetime if it's a timestamp
            if isinstance(next_earnings, (int, float)):
                next_earnings_dt = datetime.fromtimestamp(next_earnings)
            elif isinstance(next_earnings, str):
                try:
                    next_earnings_dt = datetime.fromisoformat(next_earnings.replace('Z', '+00:00'))
                except:
                    next_earnings_dt = datetime.strptime(next_earnings, '%Y-%m-%d')
            else:
                return False, None
            
            # Calculate days until earnings
            now = datetime.now()
            days_until = (next_earnings_dt.date() - now.date()).days
            
            # Check if within threshold
            if 0 <= days_until <= self.skip_within_days:
                earnings_date_str = next_earnings_dt.strftime('%Y-%m-%d')
                print(f"📅 {ticker}: Earnings on {earnings_date_str} ({days_until} days away) - SKIPPING")
                return True, earnings_date_str
            
            return False, None
        
        except Exception as e:
            print(f"⚠️  Error checking earnings for {ticker}: {e}")
            # On error, don't skip - let signal generation proceed
            return False, None


def create_earnings_context(ticker: str, skip: bool, earnings_date: Optional[str]) -> str:
    """Format earnings data as readable context"""
    
    if skip and earnings_date:
        context = f"""
EARNINGS CALENDAR CHECK FOR {ticker}
======================================
⚠️  EARNINGS WITHIN {3} DAYS: {earnings_date}
SKIPPING THIS TICKER to avoid event risk
"""
    else:
        context = f"""
EARNINGS CALENDAR CHECK FOR {ticker}
======================================
✅ No earnings within {3} days
Proceeding with analysis
"""
    
    return context
