#!/usr/bin/env python3
"""Test the fixed news agent synthesis"""

import sys
sys.path.insert(0, r"c:\Users\tommy\OneDrive\Desktop\Ai Traders")

from agents import answer_news_agent_question

# Test with a simple question
print("=" * 70)
print("Testing News Agent Synthesis Fix")
print("=" * 70)
print()

test_question = "What are the latest technology news stories?"
industry = "Technology"

print(f"Question: {test_question}")
print(f"Industry: {industry}")
print()
print("-" * 70)
print("Response from News Agent:")
print("-" * 70)

try:
    response = answer_news_agent_question(test_question, industry)
    print(response)
    print()
    print("-" * 70)
    print("Response Analysis:")
    print("-" * 70)
    
    # Count bullet points
    bullet_count = response.count('\n-') + (1 if response.startswith('-') else 0)
    print(f"Number of bullet points: {bullet_count}")
    print(f"Response length: {len(response)} characters")
    
    if bullet_count >= 4:
        print("✅ SUCCESS: Response has adequate bullet points")
    else:
        print("⚠️ WARNING: Response has fewer than expected bullet points")
        
    # Check if it contains raw news formatting
    if "PRIMARY SOURCE - NEW YORK TIMES" in response or "PREMIUM NEWS DATA" in response:
        print("⚠️ WARNING: Response contains raw news formatting (fallback mode)")
    else:
        print("✅ Response appears to be synthesized")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
