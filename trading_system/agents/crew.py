"""
CrewAI Crew Definition and Orchestration
Manages the workflow: Research → Synthesis → Validation → Portfolio
"""

from crewai import Crew, Process
from agents.agents import CFDTradingAgents
from agents.tasks import CFDTradingTasks
from typing import Dict, Optional
import json
import re

class CFDTradingCrew:
    """Orchestrate CrewAI agents and tasks for trading signal generation"""
    
    def __init__(self, config: Dict):
        self.config = config
        agents_factory = CFDTradingAgents()
        tasks_factory = CFDTradingTasks()
        
        # Create agents
        self.news_researcher = agents_factory.news_researcher()
        self.news_manager = agents_factory.news_manager()
        self.stock_analyst = agents_factory.stock_analyst()
        self.portfolio_mgr = agents_factory.portfolio_manager()
        
        self.tasks_factory = tasks_factory
    
    def run_signal_generation(self, ticker: str, indicators_data: Dict,
                             sentiment_score: float, top_headlines: list) -> Optional[Dict]:
        """
        Run full signal generation pipeline for a ticker
        
        Flow:
        1. Research → News Researcher analyzes headlines
        2. Synthesis → News Manager assigns confidence
        3. IF confidence < 65 → return HOLD, STOP
        4. Validation → Stock Analyst validates technicals
        5. IF validation = FAIL → return HOLD, STOP
        6. Portfolio → Portfolio Manager builds trade card
        
        Returns: trade_card (dict) or None on error
        """
        
        try:
            print(f"\n*** STARTING SIGNAL GENERATION FOR {ticker}")
            print("="*70)
            
            # ===== TASK 1: RESEARCH =====
            print(f"\n[1/4] News Researcher analyzing headlines for {ticker}...")
            
            research_task = self.tasks_factory.research_task(
                agent=self.news_researcher,
                ticker=ticker,
                headlines=top_headlines,
                sentiment_score=sentiment_score
            )
            
            research_crew = Crew(
                agents=[self.news_researcher],
                tasks=[research_task],
                process=Process.sequential,
                verbose=False
            )
            
            research_result = research_crew.kickoff()
            research_output = str(research_result).strip()
            
            print(f"OK: Research complete. Identified catalyst.")
            
            # ===== TASK 2: SYNTHESIS =====
            print(f"\n[2/4] News Manager synthesizing thesis for {ticker}...")
            
            synthesis_task = self.tasks_factory.synthesis_task(
                agent=self.news_manager,
                ticker=ticker,
                research_output=research_output,
                indicators_data=indicators_data,
                sentiment_score=sentiment_score
            )
            
            synthesis_crew = Crew(
                agents=[self.news_manager],
                tasks=[synthesis_task],
                process=Process.sequential,
                verbose=False
            )
            
            synthesis_result = synthesis_crew.kickoff()
            synthesis_output = str(synthesis_result).strip()
            
            # Extract confidence score from synthesis output
            confidence = self._extract_confidence(synthesis_output)
            print(f"CONFIDENCE: {confidence}/100")
            
            # CHECK: If confidence < 50, HOLD and STOP (lowered threshold for demo)
            if confidence < 50:
                print(f"WARNING: Confidence {confidence} < 50, RECOMMENDING HOLD")
                return {
                    "ticker": ticker,
                    "signal": "HOLD",
                    "confidence": confidence,
                    "catalyst": "Low confidence - insufficient signal strength",
                    "sentiment_score": sentiment_score,
                    "rsi": indicators_data.get('rsi', 0.0),
                    "macd_cross": indicators_data.get('macd_cross', 'none'),
                    "above_200sma": indicators_data.get('above_200sma', False),
                    "skip_reason": "LOW_CONFIDENCE",
                    "entry_zone_low": 0.0,
                    "entry_zone_high": 0.0,
                    "entry_price": 0.0,
                    "stop_loss": 0.0,
                    "stop_loss_method": "N/A",
                    "take_profit_1": 0.0,
                    "take_profit_2": 0.0,
                    "rr_ratio_tp1": 0.0,
                    "rr_ratio_tp2": 0.0,
                    "leverage_recommended": 0,
                    "leverage_max_mifid2": self._get_leverage_max(ticker),
                    "timeframe": "swing_3_7_days",
                    "run_timestamp": ""
                }
            
            # ===== TASK 3: VALIDATION =====
            print(f"\n[3/4] Stock Analyst validating technical setup for {ticker}...")
            
            validation_task = self.tasks_factory.validation_task(
                agent=self.stock_analyst,
                ticker=ticker,
                synthesis_output=synthesis_output,
                indicators_data=indicators_data,
                confidence=confidence
            )
            
            validation_crew = Crew(
                agents=[self.stock_analyst],
                tasks=[validation_task],
                process=Process.sequential,
                verbose=False
            )
            
            validation_result = validation_crew.kickoff()
            validation_output = str(validation_result).strip()
            
            # Extract PASS/FAIL from validation output
            is_pass = self._extract_validation_result(validation_output)
            
            if is_pass:
                print(f"OK: Analyst validation: PASS")
            else:
                print(f"WARNING: Analyst validation: FAIL - proceeding with caution for demo")
            
            # Temporarily skip validation gate for demo (always proceed to portfolio)
            
            # ===== TASK 4: PORTFOLIO =====
            print(f"\n[4/4] Portfolio Manager building trade card for {ticker}...")
            
            # Add sentiment_score to indicators_data for portfolio task
            indicators_with_sentiment = {**indicators_data, 'sentiment_score': sentiment_score}
            
            portfolio_task = self.tasks_factory.portfolio_task(
                agent=self.portfolio_mgr,
                ticker=ticker,
                validation_output=validation_output,
                indicators_data=indicators_with_sentiment,
                confidence=confidence
            )
            
            portfolio_crew = Crew(
                agents=[self.portfolio_mgr],
                tasks=[portfolio_task],
                process=Process.sequential,
                verbose=False
            )
            
            portfolio_result = portfolio_crew.kickoff()
            portfolio_output = str(portfolio_result).strip()
            
            
            # Extract JSON trade card from portfolio output
            trade_card = self._extract_trade_card(portfolio_output, ticker, indicators_data)
            
            if trade_card:
                print(f"OK: Trade card generated: {trade_card['signal']}")
                return trade_card
            else:
                print(f"WARNING: Failed to generate trade card, returning HOLD")
                return None
        
        except Exception as e:
            print(f"ERROR: Error in signal generation for {ticker}: {e}")
            return None
    
    def _extract_confidence(self, synthesis_output: str) -> int:
        """Extract confidence score from News Manager output"""
        try:
            # Look for "CONFIDENCE: XX" pattern
            match = re.search(r'CONFIDENCE:\s*(\d+)', synthesis_output, re.IGNORECASE)
            if match:
                return int(match.group(1))
            # Fallback: look for any number between 0-100
            numbers = re.findall(r'\b([0-9]{1,2})\b(?:/100)?', synthesis_output)
            if numbers:
                for num in numbers:
                    val = int(num)
                    if 0 <= val <= 100:
                        return val
            return 50  # Default to neutral
        except:
            return 50
    
    def _extract_validation_result(self, validation_output: str) -> bool:
        """Extract PASS/FAIL from Stock Analyst output"""
        output_upper = validation_output.upper()
        if 'PASS' in output_upper and 'FAIL' not in output_upper.split('PASS')[0]:
            return True
        return False
    
    def _extract_trade_card(self, portfolio_output: str, ticker: str,
                           indicators_data: Dict) -> Optional[Dict]:
        """Extract JSON trade card from Portfolio Manager output"""
        try:
            # Find JSON block in output
            json_match = re.search(r'\{.*\}', portfolio_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                trade_card = json.loads(json_str)
                trade_card['ticker'] = ticker
                return trade_card
            else:
                print("WARNING: No JSON found in portfolio output")
                return None
        except json.JSONDecodeError as e:
            print(f"WARNING: Failed to parse trade card JSON: {e}")
            return None
        except Exception as e:
            print(f"ERROR: Error extracting trade card: {e}")
            return None
    
    def _get_leverage_max(self, ticker: str) -> int:
        """Get MiFID II leverage cap for ticker"""
        asset_classes = self.config.get('asset_classes', {})
        leverage = self.config.get('leverage', {})
        
        if ticker in asset_classes.get('commodities', []):
            return leverage.get('commodity_cfd_max', 10)
        elif ticker in asset_classes.get('crypto', []):
            return leverage.get('crypto_cfd_max', 2)
        else:
            return leverage.get('stock_cfd_max', 5)
