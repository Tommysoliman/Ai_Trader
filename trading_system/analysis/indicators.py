"""
Technical Indicator Calculations (Pure Python Implementation)
All calculations happen in Python before CrewAI runs
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class IndicatorCalculator:
    """Calculate technical indicators on OHLCV data using pandas_ta"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.ind_config = config.get('indicators', {})
    
    def get_daily_data(self, ticker: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """Fetch daily OHLCV data from yfinance"""
        try:
            data = yf.download(ticker, period=period, interval='1d', progress=False)
            if data is None or len(data) == 0:
                print(f"WARNING: No data found for {ticker}")
                return None
            
            # Handle MultiIndex columns (when yfinance has structure (PriceType, Ticker))
            if isinstance(data.columns, pd.MultiIndex):
                # Flatten MultiIndex columns: ('Close', 'ORCL') -> 'Close'
                data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
            
            # Ensure we have required columns
            if 'Close' not in data.columns:
                print(f"WARNING: Missing 'Close' column for {ticker}")
                return None
            
            return data
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None
    
    def get_hourly_data(self, ticker: str, period: str = '7d') -> Optional[pd.DataFrame]:
        """Fetch hourly OHLCV data from yfinance for intraday entry timing"""
        try:
            data = yf.download(ticker, period=period, interval='1h', progress=False)
            if data is None or len(data) == 0:
                print(f"WARNING: No hourly data found for {ticker}")
                return None
            
            # Handle MultiIndex columns (when yfinance has structure (PriceType, Ticker))
            if isinstance(data.columns, pd.MultiIndex):
                # Flatten MultiIndex columns: ('Close', 'ORCL') -> 'Close'
                data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
            
            # Ensure we have required columns
            if 'Close' not in data.columns:
                print(f"WARNING: Missing 'Close' column for {ticker}")
                return None
            
            return data
        except Exception as e:
            print(f"Error fetching hourly data for {ticker}: {e}")
            return None
    
    def get_daily_data_parallel(self, tickers: List[str], period: str = '1y', max_workers: int = 5) -> Dict[str, Optional[pd.DataFrame]]:
        """Fetch daily OHLCV data for multiple tickers in parallel using ThreadPoolExecutor"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {executor.submit(self.get_daily_data, ticker, period): ticker for ticker in tickers}
            
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    data = future.result()
                    results[ticker] = data
                except Exception as e:
                    print(f"Error in parallel download for {ticker}: {e}")
                    results[ticker] = None
        
        return results
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """Calculate RSI(14) using pure Python"""
        rsi_period = self.ind_config.get('rsi_period', 14)
        close = np.array(df['Close'].values, dtype=float)
        
        if len(close) < rsi_period + 1:
            return pd.Series(np.full_like(close, 50.0, dtype=float), index=df.index)
        
        deltas = np.diff(close)
        seed = deltas[:rsi_period+1]
        
        up_sum = float(np.sum(seed[seed > 0]))
        down_sum = float(np.sum(-seed[seed < 0]))
        
        up = up_sum / rsi_period
        down = down_sum / rsi_period
        
        rs = up / down if down > 0 else 0
        rsi = np.zeros_like(close)
        rsi[:rsi_period] = 100. - 100. / (1. + rs) if rs > 0 else 50.0
        
        for i in range(rsi_period, len(close)):
            delta = deltas[i - 1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta
            
            up = (up * (rsi_period - 1) + upval) / rsi_period
            down = (down * (rsi_period - 1) + downval) / rsi_period
            
            rs = up / down if down > 0 else 0
            rsi[i] = 100. - 100. / (1. + rs) if rs > 0 else 50.0
        
        return pd.Series(rsi, index=df.index)
    
    def calculate_macd(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (12,26,9) using pure Python
        Returns: macd_line, signal_line, histogram
        """
        fast = self.ind_config.get('macd_fast', 12)
        slow = self.ind_config.get('macd_slow', 26)
        signal_period = self.ind_config.get('macd_signal', 9)
        
        close = np.array(df['Close'].values, dtype=float)
        
        if len(close) < slow:
            return (pd.Series(np.zeros_like(close), index=df.index), 
                   pd.Series(np.zeros_like(close), index=df.index), 
                   pd.Series(np.zeros_like(close), index=df.index))
        
        ema_fast = self._calculate_ema(close, fast)
        ema_slow = self._calculate_ema(close, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal_period)
        macd_hist = macd_line - signal_line
        
        return pd.Series(macd_line, index=df.index), pd.Series(signal_line, index=df.index), pd.Series(macd_hist, index=df.index)
    
    def _calculate_ema(self, data, period):
        """Calculate Exponential Moving Average"""
        data = np.array(data, dtype=float)
        ema = np.zeros(len(data), dtype=float)
        ema[0] = data[0]
        multiplier = 2.0 / (period + 1)
        
        for i in range(1, len(data)):
            ema[i] = data[i] * multiplier + ema[i-1] * (1 - multiplier)
        
        return ema
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calculate ATR(14) using pure Python"""
        atr_period = self.ind_config.get('atr_period', 14)
        
        high = np.array(df['High'].values, dtype=float)
        low = np.array(df['Low'].values, dtype=float)
        close = np.array(df['Close'].values, dtype=float)
        
        if len(high) < atr_period:
            return pd.Series(np.full_like(close, 1.0), index=df.index)
        
        tr_list = []
        for i in range(len(df)):
            if i == 0:
                tr = high[i] - low[i]
            else:
                tr1 = high[i] - low[i]
                tr2 = abs(high[i] - close[i-1])
                tr3 = abs(low[i] - close[i-1])
                tr = max(tr1, tr2, tr3)
            tr_list.append(tr)
        
        tr = np.array(tr_list)
        atr = np.zeros_like(tr)
        atr[atr_period-1] = np.mean(tr[:atr_period])
        
        for i in range(atr_period, len(tr)):
            atr[i] = (atr[i-1] * (atr_period - 1) + tr[i]) / atr_period
        
        return pd.Series(atr, index=df.index)
    
    def calculate_sma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Simple Moving Average using pure Python"""
        return df['Close'].rolling(window=period).mean()
    
    def detect_macd_cross(self, macd_line: pd.Series, macd_signal: pd.Series, 
                          lookback: int = 3) -> str:
        """Detect MACD bullish/bearish crossover in last N candles
        Returns: 'bullish', 'bearish', or 'none'
        """
        if len(macd_line) < lookback + 1:
            return 'none'
        
        recent_macd = macd_line.iloc[-lookback:].values
        recent_signal = macd_signal.iloc[-lookback:].values
        
        # Check for bullish cross (MACD crosses above signal)
        for i in range(1, len(recent_macd)):
            if recent_macd[i-1] < recent_signal[i-1] and recent_macd[i] > recent_signal[i]:
                return 'bullish'
        
        # Check for bearish cross (MACD crosses below signal)
        for i in range(1, len(recent_macd)):
            if recent_macd[i-1] > recent_signal[i-1] and recent_macd[i] < recent_signal[i]:
                return 'bearish'
        
        return 'none'
    
    def calculate_all_indicators(self, ticker: str) -> Optional[Dict]:
        """Calculate all indicators for a ticker on daily data
        Returns dictionary with all values ready for CrewAI
        """
        # Fetch daily data
        df = self.get_daily_data(ticker)
        if df is None:
            return None
        
        return self.calculate_all_indicators_from_data(ticker, df)
    
    def calculate_all_indicators_from_data(self, ticker: str, df: pd.DataFrame) -> Optional[Dict]:
        """Calculate all indicators from pre-downloaded DataFrame
        Returns dictionary with all values ready for CrewAI
        Useful for parallel processing to avoid re-downloading data
        """
        try:
            # Get current price (latest close)
            current_price = float(df['Close'].iloc[-1])
            
            # Calculate all indicators
            rsi = self.calculate_rsi(df)
            macd_line, macd_signal, macd_hist = self.calculate_macd(df)
            atr = self.calculate_atr(df)
            sma_200 = self.calculate_sma(df, self.ind_config.get('sma_200_period', 200))
            sma_50 = self.calculate_sma(df, self.ind_config.get('sma_50_period', 50))
            
            # Get latest values (handle NaN)
            rsi_current = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
            atr_current = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.1
            sma_200_current = float(sma_200.iloc[-1]) if not pd.isna(sma_200.iloc[-1]) else current_price
            sma_50_current = float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else current_price
            macd_cross = self.detect_macd_cross(macd_line, macd_signal, 
                                              self.ind_config.get('macd_cross_lookback', 3))
            
            # Determine if price is above/below 200 SMA
            above_200sma = current_price > sma_200_current if sma_200_current > 0 else True
            
            # Check signal conditions
            rsi_bullish = rsi_current < self.ind_config.get('rsi_bullish_threshold', 45)
            rsi_bearish = rsi_current > self.ind_config.get('rsi_bearish_threshold', 58)
            
            # Calculate price change percentage
            price_change_pct = ((current_price - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100) if len(df) > 1 else 0
            
            return {
                'ticker': ticker,
                'current_price': round(current_price, 2),
                'rsi': round(rsi_current, 2),
                'atr': round(atr_current, 4),
                'sma_200': round(sma_200_current, 2),
                'sma_50': round(sma_50_current, 2),
                'macd_cross': macd_cross,
                'above_200sma': bool(above_200sma),
                'rsi_bullish_condition': bool(rsi_bullish),
                'rsi_bearish_condition': bool(rsi_bearish),
                'latest_volume': int(df['Volume'].iloc[-1]) if not pd.isna(df['Volume'].iloc[-1]) else 0,
                'price_change_pct': round(price_change_pct, 2),
                'dataframe': df  # For later reference
            }
        
        except Exception as e:
            print(f"Error calculating indicators for {ticker}: {e}")
            return None
    
    def check_price_in_entry_zone(self, ticker: str, entry_zone_low: float, 
                                   entry_zone_high: float) -> Tuple[bool, float]:
        """Check if current price is within entry zone for hourly run
        Returns: (is_in_zone, current_price)
        """
        try:
            data = self.get_hourly_data(ticker, period='1d')
            if data is None or len(data) == 0:
                return False, 0.0
            
            current_price = data['Close'].iloc[-1]
            is_in_zone = entry_zone_low <= current_price <= entry_zone_high
            
            return is_in_zone, round(current_price, 2)
        
        except Exception as e:
            print(f"Error checking entry zone for {ticker}: {e}")
            return False, 0.0


def create_indicator_context(ticker_data: Dict) -> str:
    """Format indicator data as a readable context string for CrewAI agents"""
    
    context = f"""
TECHNICAL ANALYSIS FOR {ticker_data['ticker']}
================================================
Current Price: ${ticker_data['current_price']}
RSI(14): {ticker_data['rsi']}
MACD Signal: {ticker_data['macd_cross'].upper()}
ATR(14): ${ticker_data['atr']}
200-day SMA: ${ticker_data['sma_200']}
50-day SMA: ${ticker_data['sma_50']}

Price Position: {'ABOVE' if ticker_data['above_200sma'] else 'BELOW'} 200-day SMA

Volume: {ticker_data['latest_volume']:,}

SIGNAL CHECK:
- RSI < 45 (Bullish): {ticker_data['rsi_bullish_condition']}
- RSI > 58 (Bearish): {ticker_data['rsi_bearish_condition']}
- MACD Cross: {ticker_data['macd_cross']}
"""
    return context
