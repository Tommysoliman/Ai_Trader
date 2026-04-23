"""
CrewAI Task Definitions
4 tasks: research, synthesis, validation, portfolio
"""

from crewai import Task
from typing import Optional

class CFDTradingTasks:
    """Define crew tasks for CFD trading signal system"""
    
    def research_task(self, agent, ticker: str, headlines: list, sentiment_score: float) -> Task:
        """
        Task 1: News Research
        Input: headlines + sentiment score from Python layer
        Output: Raw catalyst identification and sentiment assessment
        """
        headlines_text = "\n".join([f"- {h}" for h in headlines]) if headlines else "No headlines available"
        
        return Task(
            description=f"""
Analyze financial news for {ticker} to identify catalysts and market sentiment.

HEADLINES (Last 24h):
{headlines_text}

SENTIMENT SCORE: {sentiment_score} (Range: -1.0 to +1.0)
- > +0.2: Bullish sentiment
- < -0.2: Bearish sentiment
- -0.2 to +0.2: Neutral/Mixed

Your task:
1. Summarize the key catalyst or theme emerging from these headlines
2. Identify the type of catalyst (earnings, partnership, regulatory, macro, technical recovery, etc.)
3. Assess whether sentiment aligns with the headline themes
4. Rate the clarity and significance of the catalyst (clear vs. ambiguous, major vs. minor)
5. Provide a 1-2 sentence summary of the investment thesis based on news

Output your findings clearly with specific catalyst name and type.
            """,
            agent=agent,
            expected_output="Clear identification of catalyst, catalyst type, sentiment alignment assessment, and brief investment thesis"
        )
    
    def synthesis_task(self, agent, ticker: str, research_output: str, 
                       indicators_data: dict, sentiment_score: float) -> Task:
        """
        Task 2: News Manager Synthesis
        Input: News Researcher output + indicators + sentiment
        Output: Confidence score (0-100). If < 65, recommend HOLD and STOP.
        """
        
        return Task(
            description=f"""
Synthesize the news research and technical context into a confidence score for {ticker}.

RESEARCH FINDINGS:
{research_output}

TECHNICAL CONTEXT:
- Current Price: ${indicators_data.get('current_price', 0)}
- RSI(14): {indicators_data.get('rsi', 0)}
- MACD Signal: {indicators_data.get('macd_cross', 'none')}
- Price vs 200 SMA: {'ABOVE' if indicators_data.get('above_200sma') else 'BELOW'}
- Sentiment Score: {sentiment_score}

Your task:
1. Evaluate the STRENGTH of the identified catalyst
   - Is it clear and specific, or vague/ambiguous?
   - Will it actually move the stock price?
   - Is it front-run already or still a surprise to market?
2. Assess TIMING alignment
   - Does technical condition support acting on this news?
   - Is the market at a good entry point?
3. Evaluate MARKET SENTIMENT alignment
   - Does the news sentiment match headline analysis?
   - Is there potential for mean reversion?
4. ASSIGN A CONFIDENCE SCORE (0-100):
   - 85-100: Crystal clear catalyst + strong technical setup + aligned sentiment = HIGH CONVICTION
   - 70-84: Good catalyst + OK technical setup = MODERATE CONVICTION
   - 50-69: Marginal setup = LOW CONVICTION (borderline)
   - Below 50: Weak catalyst or conflicting signals = DO NOT TRADE (recommend HOLD)

CRITICAL RULE: If confidence < 50, IMMEDIATELY output "CONFIDENCE: XX (HOLD - DO NOT PROCEED)"
If confidence >= 50, output "CONFIDENCE: XX (PROCEED TO VALIDATION)"

Output your reasoning step-by-step, then your final confidence decision.
            """,
            agent=agent,
            expected_output="Confidence score (0-100) with clear reasoning. Must explicitly state PROCEED or HOLD."
        )
    
    def validation_task(self, agent, ticker: str, synthesis_output: str,
                       indicators_data: dict, confidence: int) -> Task:
        """
        Task 3: Stock Analyst Validation
        Input: Synthesis output + all technical indicators
        Output: EXPLICIT PASS or FAIL (not vague analysis)
        
        CONDITIONAL: Only run if confidence >= 50
        """
        
        # Build signal conditions check
        signal_condition = ""
        if confidence >= 50:
            rsi = indicators_data.get('rsi', 0)
            rsi_bullish = rsi < 45
            rsi_bearish = rsi > 58
            macd_cross = indicators_data.get('macd_cross', 'none')
            above_200sma = indicators_data.get('above_200sma', False)
            sentiment_score = indicators_data.get('sentiment_score', 0)
            
            bullish_conditions = rsi_bullish and macd_cross == 'bullish' and above_200sma and sentiment_score > 0.2
            bearish_conditions = rsi_bearish and macd_cross == 'bearish' and (not above_200sma) and sentiment_score < -0.2
            
            signal_condition = f"""
SIGNAL CONDITIONS CHECK:
- RSI Bullish (< 45): {rsi_bullish}
- RSI Bearish (> 58): {rsi_bearish}
- MACD Cross: {macd_cross}
- Price Above 200 SMA: {above_200sma}
- Sentiment > 0.2: {sentiment_score > 0.2}
- Sentiment < -0.2: {sentiment_score < -0.2}

Bullish Signal Met: {bullish_conditions}
Bearish Signal Met: {bearish_conditions}
"""
        
        return Task(
            description=f"""
Validate the news thesis for {ticker} using technical and fundamental indicators.

NEWS MANAGER OUTPUT:
{synthesis_output}

{signal_condition}

TECHNICAL DATA:
- RSI(14): {indicators_data.get('rsi', 0)}
- MACD: {indicators_data.get('macd_cross', 'none')}
- Price vs 200 SMA: {'ABOVE' if indicators_data.get('above_200sma') else 'BELOW'}
- ATR(14): {indicators_data.get('atr', 0)}
- Current Price: ${indicators_data.get('current_price', 0)}
- Sentiment: {indicators_data.get('sentiment_score', 0)}

Your task:
1. Verify that the technical setup CONFIRMS the news thesis
   - Does price action align with the catalyst narrative?
   - Are key technical levels supportive?
2. Check for conflicting signals
   - Any chart patterns that argue against entry?
   - Any divergences or warning signs?
3. Assess quality of the setup
   - Is this a strong technical + news alignment or weak/forced?

CRITICAL: You MUST output either PASS or FAIL - no ambiguity.
- PASS: Technical setup is sound, thesis is validated, recommend PROCEED
- FAIL: Technical setup conflicts with thesis, or entry is poor quality, recommend HOLD

Output your reasoning clearly, then state your final decision: "VALIDATION: PASS" or "VALIDATION: FAIL"
            """,
            agent=agent,
            expected_output="Clear PASS or FAIL decision with specific reasoning. No vague conclusions."
        )
    
    def portfolio_task(self, agent, ticker: str, validation_output: str,
                       indicators_data: dict, confidence: int) -> Task:
        """
        Task 4: Portfolio Manager - Build Trade Card
        Input: Analyst PASS validation + indicators + thesis
        Output: Structured JSON trade card with MiFID II compliance
        
        CONDITIONAL: Only run if validation = PASS
        """
        
        return Task(
            description=f"""
Structure the validated trade setup into a final, actionable trade card for {ticker}.

ANALYST VALIDATION:
{validation_output}

TECHNICAL DATA FOR TRADE STRUCTURING:
- Current Price: ${indicators_data.get('current_price', 0)}
- ATR(14): ${indicators_data.get('atr', 0)}
- RSI(14): {indicators_data.get('rsi', 0)}
- MACD: {indicators_data.get('macd_cross', 'none')}
- Above 200 SMA: {indicators_data.get('above_200sma', False)}
- Sentiment Score: {indicators_data.get('sentiment_score', 0)}

CONFIDENCE: {confidence}/100

Your task:
1. DETERMINE SIGNAL TYPE by applying this EXACT logic:

   A) IF CONFIDENCE < 50:
      SIGNAL = "HOLD"
      (Not enough conviction in the thesis)
   
   B) IF CONFIDENCE >= 50:
      IF SENTIMENT > 0.2:
         SIGNAL = "BUY"  (News catalyst creates bullish opportunity)
      ELSE IF SENTIMENT < -0.2:
         SIGNAL = "SELL"  (News catalyst creates bearish opportunity)
      ELSE (sentiment between -0.2 and +0.2):
         IF RSI < 50 and MACD == "bullish":
            SIGNAL = "BUY"
         ELSE IF RSI > 50 and MACD == "bearish":
            SIGNAL = "SELL"
         ELSE:
            SIGNAL = "HOLD"
   
   CRITICAL INSTRUCTION: Do not deviate from this logic. Follow it exactly.

2. CALCULATE ENTRY ZONE:
   - For BUY: low = current price, high = current price + (0.5 * ATR)
   - For SELL: high = current price, low = current price - (0.5 * ATR)
   - Entry = midpoint of zone

3. CALCULATE STOP LOSS (ATR-based):
   - For BUY: SL = entry - (1.5 * ATR)
   - For SELL: SL = entry + (1.5 * ATR)
   - Always use 1.5x ATR multiplier

4. CALCULATE TAKE PROFITS:
   - TP1 = entry + (2.0 * ATR) for BUY, or entry - (2.0 * ATR) for SELL
   - TP2 = entry + (4.0 * ATR) for BUY, or entry - (4.0 * ATR) for SELL
   - Calculate RR ratios: (TP distance from entry) / (entry distance from SL)

5. DETERMINE LEVERAGE (MiFID II compliant):
   - Stocks max: 5:1
   - Commodities max: 10:1
   - Crypto max: 2:1
   - Recommended = based on confidence:
     * Confidence >= 80: Use max allowed leverage
     * Confidence 70-79: Use 50% of max
     * Confidence < 70: Use 1:1 (no leverage)
   - YOU CANNOT OVERRIDE MiFID II CAPS

6. OUTPUT THE EXACT JSON TRADE CARD:

{{
  "ticker": "{ticker}",
  "signal": "[BUY|SELL|HOLD]",
  "entry_zone_low": [number],
  "entry_zone_high": [number],
  "entry_price": [number],
  "stop_loss": [number],
  "stop_loss_method": "1.5x ATR from entry",
  "take_profit_1": [number],
  "take_profit_2": [number],
  "rr_ratio_tp1": [number],
  "rr_ratio_tp2": [number],
  "leverage_recommended": [0-10],
  "leverage_max_mifid2": [0-10],
  "timeframe": "swing_3_7_days",
  "confidence": {confidence},
  "catalyst": "[one sentence description]",
  "sentiment_score": {indicators_data.get('sentiment_score', 0)},
  "rsi": {indicators_data.get('rsi', 0)},
  "macd_cross": "{indicators_data.get('macd_cross', 'none')}",
  "above_200sma": {indicators_data.get('above_200sma', False)},
  "skip_reason": null,
  "run_timestamp": "[ISO timestamp]"
}}

Ensure all numbers are properly rounded to 2 decimals. All fields must be completed.
            """,
            agent=agent,
            expected_output="Complete JSON trade card with all required fields, ready for execution"
        )
    
    def qa_task(self, agent, question: str, news_context: str) -> Task:
        """
        Task: Market Q&A
        Input: User question + Recent news context from DuckDuckGo
        Output: Comprehensive, well-sourced answer to the question
        """
        return Task(
            description=f"""
Answer the following question about financial markets, stocks, or trading based on the most recent news and information available.

USER QUESTION:
{question}

RECENT NEWS CONTEXT (Last 7 weeks):
{news_context}

Your task:
1. Analyze the question carefully
2. Use the provided recent news context to formulate an accurate, well-informed answer
3. If the question is about a specific stock or sector, provide relevant details from recent news
4. Explain the reasoning and context behind your answer
5. Cite specific news sources or developments where applicable
6. If information is limited or conflicting, acknowledge that and provide the best analysis you can
7. Distinguish between facts, recent developments, and analysis/predictions

Provide a comprehensive, clear, and helpful answer that would be useful to an investor or trader.
            """,
            agent=agent,
            expected_output="A comprehensive, well-sourced answer to the user's question with citations to recent news and clear reasoning"
        )
