"""
Reply Agent Safety Improvements - Test Cases
This script tests the enhanced reply generation system with:
- Two-tier keyword blocking (hard vs soft)
- Deterministic pattern selection
- Post-generation validation
- Enhanced audit logging
"""

import sys
sys.path.append('c:/Users/KHAN/.gemini/antigravity/scratch/lic-platform/backend')

from app.reply import generate_reply

print("=" * 80)
print("REPLY AGENT SAFETY TESTS")
print("=" * 80)

# Test 1: HARD BLOCK - Should always return NO_REPLY
print("\n[TEST 1] HARD BLOCK KEYWORD: 'claim'")
reply = generate_reply(
    email_body="I want to submit a claim for my policy.",
    intent="REQUEST",
    priority="MEDIUM",
    confidence="High",
    sentiment="NEUTRAL"
)
print(f"Result: {reply}")
assert reply == "NO_REPLY", "❌ FAILED: Hard keyword should block"
print("✅ PASSED: Correctly blocked hard keyword")

# Test 2: SOFT INDICATOR + RISK - Should block
print("\n[TEST 2] SOFT INDICATOR + URGENCY: 'timeline' + 'urgent'")
reply = generate_reply(
    email_body="I need to know the timeline for processing urgently.",
    intent="GENERAL_ENQUIRY",
    priority="MEDIUM",
    confidence="High",
    sentiment="NEUTRAL"
)
print(f"Result: {reply}")
assert reply == "NO_REPLY", "❌ FAILED: Soft + urgency should block"
print("✅ PASSED: Correctly blocked soft indicator with urgency")

# Test 3: SOFT INDICATOR + NEGATIVE - Should block
print("\n[TEST 3] SOFT INDICATOR + NEGATIVE SENTIMENT: 'approval' + NEGATIVE")
reply = generate_reply(
    email_body="Why hasn't my approval request been processed yet?",
    intent="REQUEST",
    priority="MEDIUM",
    confidence="High",
    sentiment="NEGATIVE"
)
print(f"Result: {reply}")
assert reply == "NO_REPLY", "❌ FAILED: Soft + negative sentiment should block"
print("✅ PASSED: Correctly blocked soft indicator with negative sentiment")

# Test 4: SOFT INDICATOR NO RISK - Should generate reply
print("\n[TEST 4] SOFT INDICATOR NO RISK: 'timeline' + POSITIVE sentiment")
reply = generate_reply(
    email_body="Just wondering about general timelines for policy registration.",
    intent="GENERAL_ENQUIRY",
    priority="LOW",
    confidence="High",
    sentiment="POSITIVE"
)
print(f"Result: {reply[:50]}...")
assert reply != "NO_REPLY", "❌ FAILED: Safe soft indicator should allow reply"
print("✅ PASSED: Correctly allowed safe soft indicator")

# Test 5: DETERMINISTIC PATTERN - GENERAL_ENQUIRY → Pattern B
print("\n[TEST 5] DETERMINISTIC PATTERN: GENERAL_ENQUIRY → Pattern B")
reply = generate_reply(
    email_body="Can you tell me more about LIC policies?",
    intent="GENERAL_ENQUIRY",
    priority="MEDIUM",
    confidence="High",
    sentiment="NEUTRAL"
)
print(f"Result: {reply}")
expected = "Thank you for your query"
assert expected in reply, f"❌ FAILED: Should use Pattern B for GENERAL_ENQUIRY"
print("✅ PASSED: Correctly used Pattern B")

# Test 6: DETERMINISTIC PATTERN - REQUEST → Pattern A
print("\n[TEST 6] DETERMINISTIC PATTERN: REQUEST → Pattern A")
reply = generate_reply(
    email_body="Please send me information about my policy.",
    intent="REQUEST",
    priority="LOW",
    confidence="High",
    sentiment="NEUTRAL"
)
print(f"Result: {reply}")
expected = "Thank you for contacting LIC"
assert expected in reply, f"❌ FAILED: Should use Pattern A for REQUEST"
print("✅ PASSED: Correctly used Pattern A")

# Test 7: DETERMINISTIC PATTERN - APPRECIATION → Pattern C
print("\n[TEST 7] DETERMINISTIC PATTERN: APPRECIATION → Pattern C")
reply = generate_reply(
    email_body="Thank you for your excellent service!",
    intent="APPRECIATION",
    priority="LOW",
    confidence="High",
    sentiment="POSITIVE"
)
print(f"Result: {reply}")
expected = "Thank you for your feedback"
assert expected in reply, f"❌ FAILED: Should use Pattern C for APPRECIATION"
print("✅ PASSED: Correctly used Pattern C")

# Test 8: HIGH PRIORITY - Should block
print("\n[TEST 8] HIGH PRIORITY: Should always block")
reply = generate_reply(
    email_body="I have a question about my policy.",
    intent="GENERAL_ENQUIRY",
    priority="HIGH",
    confidence="High",
    sentiment="NEUTRAL"
)
print(f"Result: {reply}")
assert reply == "NO_REPLY", "❌ FAILED: High priority should block"
print("✅ PASSED: Correctly blocked HIGH priority")

# Test 9: LOW CONFIDENCE - Should block
print("\n[TEST 9] LOW CONFIDENCE: Should block")
reply = generate_reply(
    email_body="Policy information please.",
    intent="GENERAL_ENQUIRY",
    priority="MEDIUM",
    confidence="Medium",
    sentiment="NEUTRAL"
)
print(f"Result: {reply}")
assert reply == "NO_REPLY", "❌ FAILED: Low confidence should block"
print("✅ PASSED: Correctly blocked non-High confidence")

# Test 10: RESTRICTED INTENT - Should block
print("\n[TEST 10] RESTRICTED INTENT: COMPLAINT")
reply = generate_reply(
    email_body="I want to file a complaint.",
    intent="COMPLAINT",
    priority="MEDIUM",
    confidence="High",
    sentiment="NEGATIVE"
)
print(f"Result: {reply}")
assert reply == "NO_REPLY", "❌ FAILED: COMPLAINT intent should block"
print("✅ PASSED: Correctly blocked COMPLAINT intent")

print("\n" + "=" * 80)
print("ALL TESTS PASSED! ✅")
print("=" * 80)
print("\nKey Improvements Verified:")
print("✓ Hard keywords always block")
print("✓ Soft keywords block only with risk amplifiers")
print("✓ Deterministic pattern selection working")
print("✓ Entry conditions enforced")
print("✓ Zero risk of commitments maintained")
