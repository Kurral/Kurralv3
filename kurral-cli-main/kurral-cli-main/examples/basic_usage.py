"""
Basic usage example for Kurral decorator
"""

from openai import OpenAI

from kurral import trace_llm

# Initialize OpenAI client
client = OpenAI()


@trace_llm(semantic_bucket="customer_support", tenant_id="acme_prod")
def handle_customer_query(query: str) -> str:
    """
    Handle customer support query with LLM

    This function is automatically traced and exported as a .kurral artifact
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": query}],
        temperature=0.0,  # Set to 0 for determinism
        seed=12345,  # Important for determinism!
    )

    return response.choices[0].message.content


@trace_llm(semantic_bucket="refund_flow", tenant_id="acme_prod", environment="production")
def process_refund_request(order_id: str, reason: str) -> dict:
    """
    Process refund request using LLM for decision

    Returns refund decision and explanation
    """
    prompt = f"""
    Analyze this refund request:
    Order ID: {order_id}
    Reason: {reason}

    Should we approve this refund? Provide reasoning.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a refund policy expert."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        seed=54321,
    )

    decision_text = response.choices[0].message.content

    # Simple parsing (in real app, use structured output)
    approved = "approve" in decision_text.lower()

    return {
        "order_id": order_id,
        "approved": approved,
        "reasoning": decision_text,
    }


def main():
    """Example usage"""
    # Example 1: Customer support
    print("Example 1: Customer Support Query")
    response = handle_customer_query("I need help with my order #12345")
    print(f"Response: {response}\n")

    # Example 2: Refund processing
    print("Example 2: Refund Request")
    result = process_refund_request(
        order_id="12345", reason="Product arrived damaged"
    )
    print(f"Decision: {result}\n")

    print("✅ Traces have been captured and exported to .kurral artifacts")
    print("Check your configured storage location for the generated files")


if __name__ == "__main__":
    main()

