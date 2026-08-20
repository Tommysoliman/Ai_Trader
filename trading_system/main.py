"""
CFD Trading Signal System - Main Entry Point and Scheduler
Daily run at 08:00 Cairo time (UTC+2)
Hourly run when active signals exist
"""

import os
import sys
import time
import yaml
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import pytz

# Add project to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
load_dotenv(PROJECT_ROOT / '.env')

from analysis.indicators import IndicatorCalculator, create_indicator_context
from analysis.sentiment import SentimentAnalyzer, create_sentiment_context
from analysis.earnings import EarningsChecker
from agents.crew import CFDTradingCrew
from utils.trade_card import TradeCardBuilder, TradeCardWriter


class CFDTradingSystem:
    """Main orchestration class for CFD trading signal system"""
    
    def __init__(self):
        """Initialize system with config"""
        config_path = PROJECT_ROOT / 'config.yaml'
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.watchlist = self.config.get('watchlist', [])
        self.indicator_calc = IndicatorCalculator(self.config)
        self.sentiment_analyzer = SentimentAnalyzer(self.config)
        self.earnings_checker = EarningsChecker(self.config)
        self.trade_card_builder = TradeCardBuilder(self.config)
        self.trade_card_writer = TradeCardWriter(self.config)
        self.crew = CFDTradingCrew(self.config)
        
        self.active_signals = []  # Store BUY/SELL signals for hourly run
        self.cairo_tz = pytz.timezone('Africa/Cairo')
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Setup simple logger"""
        log_file = PROJECT_ROOT / 'trading_system.log'
        class SimpleLogger:
            def log(self, msg):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                full_msg = f"[{timestamp}] {msg}"
                print(full_msg)
                try:
                    with open(log_file, 'a') as f:
                        f.write(full_msg + '\n')
                except:
                    pass
        return SimpleLogger()
    
    def daily_run(self):
        """Daily scan at 08:00 Cairo time
        Runs full pipeline for all tickers
        """
        self.logger.log("="*70)
        self.logger.log("🚀 DAILY RUN STARTED")
        self.logger.log("="*70)
        
        cairo_time = datetime.now(self.cairo_tz)
        self.logger.log(f"⏰ Cairo Time: {cairo_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        all_trade_cards = []
        self.active_signals = []
        
        for ticker in self.watchlist:
            self.logger.log(f"\n📊 Processing {ticker}...")
            
            # Step 1: Download price data and calculate indicators
            indicators_data = self.indicator_calc.calculate_all_indicators(ticker)
            
            if not indicators_data:
                self.logger.log(f"⚠️  Skipping {ticker} - no data available")
                continue
            
            # Step 2: Check earnings calendar
            skip_earnings, earnings_date = self.earnings_checker.check_earnings_within_threshold(ticker)
            
            if skip_earnings:
                trade_card = self.trade_card_builder.build_trade_card(
                    ticker=ticker,
                    signal="HOLD",
                    current_price=indicators_data['current_price'],
                    atr=indicators_data['atr'],
                    indicators_data=indicators_data,
                    confidence=0,
                    catalyst=f"Earnings on {earnings_date}",
                    sentiment_score=0.0,
                    skip_reason="EARNINGS"
                )
                all_trade_cards.append(trade_card)
                self.trade_card_writer.print_trade_card(trade_card)
                continue
            
            # Step 3: Get sentiment score
            sentiment_score = self.sentiment_analyzer.calculate_sentiment_score(ticker)
            top_headlines = self.sentiment_analyzer.get_top_headlines(ticker, limit=3)
            
            # Step 4: Run CrewAI pipeline
            try:
                trade_card = self.crew.run_signal_generation(
                    ticker=ticker,
                    indicators_data=indicators_data,
                    sentiment_score=sentiment_score,
                    top_headlines=top_headlines
                )
                
                if trade_card:
                    all_trade_cards.append(trade_card)
                    self.trade_card_writer.print_trade_card(trade_card)
                    
                    # Track active signals for hourly run
                    if trade_card['signal'] in ['BUY', 'SELL']:
                        self.active_signals.append({
                            'ticker': ticker,
                            'signal': trade_card['signal'],
                            'entry_zone_low': trade_card['entry_zone_low'],
                            'entry_zone_high': trade_card['entry_zone_high'],
                            'run_timestamp': trade_card['run_timestamp']
                        })
                else:
                    # Default HOLD if crew failed
                    trade_card = self.trade_card_builder.build_trade_card(
                        ticker=ticker,
                        signal="HOLD",
                        current_price=indicators_data['current_price'],
                        atr=indicators_data['atr'],
                        indicators_data=indicators_data,
                        confidence=0,
                        catalyst="Crew processing error",
                        sentiment_score=sentiment_score,
                        skip_reason="AGENT_ERROR"
                    )
                    all_trade_cards.append(trade_card)
            
            except Exception as e:
                self.logger.log(f"❌ Error processing {ticker}: {e}")
                trade_card = self.trade_card_builder.build_trade_card(
                    ticker=ticker,
                    signal="HOLD",
                    current_price=indicators_data['current_price'],
                    atr=indicators_data['atr'],
                    indicators_data=indicators_data,
                    confidence=0,
                    catalyst="Error in signal generation",
                    sentiment_score=0.0,
                    skip_reason="AGENT_ERROR"
                )
                all_trade_cards.append(trade_card)
        
        # Step 5: Write all trade cards to JSON
        if all_trade_cards:
            output_file = self.trade_card_writer.write_trade_cards(all_trade_cards)
            self.logger.log(f"\n✅ Daily run complete. Trade cards saved to {output_file}")
        else:
            self.logger.log("\n⚠️  No trade cards generated today")
        
        # Summary
        buy_count = len([c for c in all_trade_cards if c['signal'] == 'BUY'])
        sell_count = len([c for c in all_trade_cards if c['signal'] == 'SELL'])
        hold_count = len([c for c in all_trade_cards if c['signal'] == 'HOLD'])
        
        self.logger.log(f"\n📊 SUMMARY: {buy_count} BUY | {sell_count} SELL | {hold_count} HOLD")
        self.logger.log(f"📌 Active signals for hourly monitoring: {len(self.active_signals)}")
        
        return all_trade_cards
    
    def hourly_run(self):
        """Hourly check for entry opportunities on active signals
        Only runs if daily_run has BUY or SELL signals
        """
        if not self.active_signals:
            return
        
        self.logger.log(f"\n⏰ [HOURLY RUN] Checking entry opportunities...")
        
        for signal_data in self.active_signals:
            ticker = signal_data['ticker']
            signal = signal_data['signal']
            entry_zone_low = signal_data['entry_zone_low']
            entry_zone_high = signal_data['entry_zone_high']
            
            # Check if price is in entry zone
            is_in_zone, current_price = self.indicator_calc.check_price_in_entry_zone(
                ticker, entry_zone_low, entry_zone_high
            )
            
            if is_in_zone:
                self.logger.log(f"\n🎯 ENTRY ALERT: {ticker} {signal}")
                self.logger.log(f"   Current Price: ${current_price}")
                self.logger.log(f"   Entry Zone: ${entry_zone_low} - ${entry_zone_high}")
                self.logger.log(f"   ✅ PRICE IN ENTRY ZONE - READY FOR EXECUTION")
            else:
                self.logger.log(f"\n📊 {ticker} {signal}: Price ${current_price} outside entry zone ${entry_zone_low}-${entry_zone_high}")
    
    def schedule_jobs(self):
        """Schedule daily and hourly jobs"""
        
        # Schedule daily run
        daily_time = self.config.get('scheduler', {}).get('daily_run_time', '08:00')
        schedule.every().day.at(daily_time).do(self.daily_run)
        self.logger.log(f"📅 Daily run scheduled for {daily_time} Cairo time")
        
        # Schedule hourly run
        schedule.every().hour.do(self.hourly_run)
        self.logger.log(f"📅 Hourly run scheduled every hour")
    
    def run(self):
        """Main scheduler loop"""
        self.logger.log("🚀 Starting CFD Trading Signal System")
        self.logger.log(f"   Watchlist: {', '.join(self.watchlist)}")
        self.logger.log(f"   Config: {PROJECT_ROOT / 'config.yaml'}")
        
        self.schedule_jobs()
        
        self.logger.log("\n⏰ Scheduler started. Waiting for scheduled times...")
        self.logger.log("   Press Ctrl+C to stop\n")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        except KeyboardInterrupt:
            self.logger.log("\n🛑 Scheduler stopped by user")


def main():
    """Entry point"""
    try:
        system = CFDTradingSystem()
        system.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
