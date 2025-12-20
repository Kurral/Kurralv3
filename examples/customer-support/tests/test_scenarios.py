"""
Test scenarios for customer support agent using Kurral replay.

Run once to capture, then replay unlimited times for free!

Usage:
    # Initial capture (costs ~$1-2)
    pytest test_scenarios.py

    # Replay (FREE!)
    kurral replay --latest
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import run_agent
import os


# Test data - realistic customer support scenarios
TEST_SCENARIOS = [
    {
        "id": "shipping_inquiry",
        "query": "What are your shipping options and costs?",
        "expected_keywords": ["standard", "express", "business days"],
    },
    {
        "id": "return_policy",
        "query": "How do I return an item I purchased last week?",
        "expected_keywords": ["30 days", "return", "refund"],
    },
    {
        "id": "password_reset",
        "query": "I forgot my password, how can I reset it?",
        "expected_keywords": ["forgot password", "reset link", "email"],
    },
    {
        "id": "international_shipping",
        "query": "Do you ship to Canada?",
        "expected_keywords": ["international", "ship", "countries"],
    },
    {
        "id": "tracking",
        "query": "How can I track my order?",
        "expected_keywords": ["tracking", "email", "order"],
    },
]


def test_customer_support_scenarios():
    """
    Test multiple customer support scenarios.

    Kurral captures all interactions on first run.
    Subsequent runs replay from artifacts (zero cost).
    """
    api_key = os.getenv("OPENAI_API_KEY", "")

    # Use mock mode if no API key (for CI/CD)
    mock_mode = not api_key

    results = []

    for scenario in TEST_SCENARIOS:
        print(f"\n📋 Testing: {scenario['id']}")
        print(f"   Query: {scenario['query']}")

        result = run_agent(
            user_input=scenario['query'],
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=api_key,
            mock=mock_mode
        )

        output = result["output"]

        # Validate response contains expected keywords
        matched = [kw for kw in scenario['expected_keywords']
                  if kw.lower() in output.lower()]

        results.append({
            "scenario": scenario['id'],
            "passed": len(matched) > 0,
            "matched_keywords": matched,
            "output_length": len(output)
        })

        print(f"   ✅ Response: {len(output)} chars, matched: {matched}")

    # Summary
    passed = sum(1 for r in results if r['passed'])
    total = len(results)

    print(f"\n📊 Test Summary: {passed}/{total} scenarios passed")

    # Assert all passed (or skip if using mock mode)
    if not mock_mode:
        assert passed == total, f"Only {passed}/{total} scenarios passed"
    else:
        print("   ⚠️  Mock mode: Skipping assertions")


def test_knowledge_base_tool():
    """Test that knowledge base lookups are deterministic."""
    from agent import search_knowledge_base

    # Same query should always return same result
    result1 = search_knowledge_base("shipping")
    result2 = search_knowledge_base("shipping")

    assert result1 == result2, "Knowledge base should be deterministic!"
    assert "shipping" in result1.lower()

    print("✅ Knowledge base tool is deterministic (perfect for Kurral!)")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
