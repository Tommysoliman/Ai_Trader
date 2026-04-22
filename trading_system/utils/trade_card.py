"""
Trade Card Builder and JSON Output Writer
Formats the final structured trade card for each ticker
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

class TradeCardBuilder:
    """Build and validate trade card structure"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def get_leverage_max(self, ticker: str) -> int:
        """Get MiFID II leverage cap based on asset class"""
        asset_classes = self.config.get('asset_classes', {})
        leverage_config = self.config.get('leverage', {})
        
        if ticker in asset_classes.get('commodities', []):
            return leverage_config.get('commodity_cfd_max', 10)
        elif ticker in asset_classes.get('crypto', []):
            return leverage_config.get('crypto_cfd_max', 2)
        else:
            # Default to stocks
            return leverage_config.get('stock_cfd_max', 5)
    
    def calculate_take_profits(self, entry: float, atr: float) -> tuple:
        """Calculate TP1 and TP2 based on entry and ATR"""
        tp1_multiplier = self.config.get('take_profit', {}).get('tp1_atr_multiplier', 2.0)
        tp2_multiplier = self.config.get('take_profit', {}).get('tp2_atr_multiplier', 4.0)
        
        tp1 = entry + (tp1_multiplier * atr)
        tp2 = entry + (tp2_multiplier * atr)
        
        return round(tp1, 2), round(tp2, 2)
    
    def calculate_risk_reward_ratios(self, entry: float, stop_loss: float, 
                                     tp1: float, tp2: float) -> tuple:
        """Calculate RR ratios for each TP"""
        risk = abs(entry - stop_loss)
        
        if risk == 0:
            return 0.0, 0.0
        
        rr1 = round(abs(tp1 - entry) / risk, 2)
        rr2 = round(abs(tp2 - entry) / risk, 2)
        
        return rr1, rr2
    
    def build_trade_card(self, 
                        ticker: str,
                        signal: str,  # BUY, SELL, HOLD
                        current_price: float,
                        atr: float,
                        indicators_data: Dict,
                        confidence: int,
                        catalyst: str = "",
                        sentiment_score: float = 0.0,
                        skip_reason: Optional[str] = None) -> Dict:
        """Build complete trade card structure"""
        
        # Calculate entry zone
        if signal == 'BUY':
            entry_zone_low = current_price
            entry_zone_high = current_price + (0.5 * atr)
            entry_price = (entry_zone_low + entry_zone_high) / 2
            stop_loss = entry_price - (1.5 * atr)
        elif signal == 'SELL':
            entry_zone_low = current_price - (0.5 * atr)
            entry_zone_high = current_price
            entry_price = (entry_zone_low + entry_zone_high) / 2
            stop_loss = entry_price + (1.5 * atr)
        else:  # HOLD
            entry_zone_low = current_price
            entry_zone_high = current_price
            entry_price = current_price
            stop_loss = 0.0
        
        # Calculate take profits
        if signal != 'HOLD':
            tp1, tp2 = self.calculate_take_profits(entry_price, atr)
            rr1, rr2 = self.calculate_risk_reward_ratios(entry_price, stop_loss, tp1, tp2)
        else:
            tp1, tp2 = 0.0, 0.0
            rr1, rr2 = 0.0, 0.0
        
        # Determine leverage
        leverage_max = self.get_leverage_max(ticker)
        if signal == 'HOLD':
            leverage_recommended = 0
        elif confidence >= 80:
            leverage_recommended = leverage_max
        elif confidence >= 70:
            leverage_recommended = max(1, leverage_max // 2)
        else:
            leverage_recommended = 1
        
        trade_card = {
            "ticker": ticker,
            "signal": signal,
            "entry_zone_low": round(entry_zone_low, 2),
            "entry_zone_high": round(entry_zone_high, 2),
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "stop_loss_method": f"1.5x ATR ({round(1.5 * atr, 2)}) from entry",
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "rr_ratio_tp1": rr1,
            "rr_ratio_tp2": rr2,
            "leverage_recommended": leverage_recommended,
            "leverage_max_mifid2": leverage_max,
            "timeframe": "swing_3_7_days",
            "confidence": confidence,
            "catalyst": catalyst,
            "sentiment_score": round(sentiment_score, 2),
            "rsi": indicators_data.get('rsi', 0.0),
            "macd_cross": indicators_data.get('macd_cross', 'none'),
            "above_200sma": indicators_data.get('above_200sma', False),
            "skip_reason": skip_reason,
            "run_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return trade_card


class TradeCardWriter:
    """Write trade cards to JSON file"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.signals_dir = Path(__file__).parent.parent / "signals"
        self.signals_dir.mkdir(parents=True, exist_ok=True)
    
    def get_output_filename(self) -> str:
        """Generate output filename with date: signal_YYYYMMDD.json"""
        date_str = datetime.utcnow().strftime('%Y%m%d')
        return f"signal_{date_str}.json"
    
    def write_trade_cards(self, trade_cards: list) -> str:
        """Write all trade cards to JSON file
        Returns: filepath
        """
        filename = self.get_output_filename()
        filepath = self.signals_dir / filename
        
        output = {
            "run_timestamp": datetime.utcnow().isoformat() + "Z",
            "total_signals": len(trade_cards),
            "buy_signals": len([c for c in trade_cards if c['signal'] == 'BUY']),
            "sell_signals": len([c for c in trade_cards if c['signal'] == 'SELL']),
            "hold_signals": len([c for c in trade_cards if c['signal'] == 'HOLD']),
            "trade_cards": trade_cards
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(output, f, indent=2)
            
            print(f"✅ Trade cards written to {filepath}")
            return str(filepath)
        
        except Exception as e:
            print(f"❌ Error writing trade cards: {e}")
            return ""
    
    def append_trade_card(self, trade_card: Dict) -> bool:
        """Append a single trade card to today's file"""
        filename = self.get_output_filename()
        filepath = self.signals_dir / filename
        
        try:
            # Load existing cards or create new
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
            else:
                data = {
                    "run_timestamp": datetime.utcnow().isoformat() + "Z",
                    "trade_cards": []
                }
            
            # Append new card
            data['trade_cards'].append(trade_card)
            
            # Update counts
            trade_cards = data['trade_cards']
            data['total_signals'] = len(trade_cards)
            data['buy_signals'] = len([c for c in trade_cards if c['signal'] == 'BUY'])
            data['sell_signals'] = len([c for c in trade_cards if c['signal'] == 'SELL'])
            data['hold_signals'] = len([c for c in trade_cards if c['signal'] == 'HOLD'])
            
            # Write back
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        
        except Exception as e:
            print(f"❌ Error appending trade card: {e}")
            return False
    
    def print_trade_card(self, card: Dict):
        """Pretty print trade card to terminal"""
        
        print("\n" + "="*70)
        print(f"📊 TRADE CARD: {card['ticker']}")
        print("="*70)
        print(f"Signal: {card['signal']}")
        print(f"Confidence: {card['confidence']}/100")
        print(f"Catalyst: {card['catalyst']}")
        print(f"Sentiment Score: {card['sentiment_score']}")
        print()
        print("ENTRY ZONE")
        print(f"  Low:  ${card['entry_zone_low']}")
        print(f"  High: ${card['entry_zone_high']}")
        print()
        print("RISK MANAGEMENT")
        print(f"  Entry Price: ${card['entry_price']}")
        print(f"  Stop Loss: ${card['stop_loss']} ({card['stop_loss_method']})")
        print(f"  TP1: ${card['take_profit_1']} (RR: 1:{card['rr_ratio_tp1']})")
        print(f"  TP2: ${card['take_profit_2']} (RR: 1:{card['rr_ratio_tp2']})")
        print()
        print("LEVERAGE")
        print(f"  Recommended: {card['leverage_recommended']}:1")
        print(f"  MiFID II Max: {card['leverage_max_mifid2']}:1")
        print()
        print("TECHNICALS")
        print(f"  RSI(14): {card['rsi']}")
        print(f"  MACD Cross: {card['macd_cross']}")
        print(f"  Above 200 SMA: {card['above_200sma']}")
        print()
        if card['skip_reason']:
            print(f"⚠️  SKIP REASON: {card['skip_reason']}")
        print()
        print(f"Timestamp: {card['run_timestamp']}")
        print("="*70 + "\n")
