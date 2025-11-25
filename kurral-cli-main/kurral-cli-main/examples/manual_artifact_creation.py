"""
Example of manually creating Kurral artifacts

Useful when you can't use the decorator (e.g., legacy code)
"""

from kurral.core.decorator import create_artifact_from_trace

# Example: Manually create artifact from existing trace data
artifact = create_artifact_from_trace(
    run_id="manual_run_123",
    tenant_id="acme_corp",
    inputs={"query": "What is the weather today?"},
    outputs={"response": "I don't have access to real-time weather data."},
    model_name="gpt-4-0613",
    provider="openai",
    temperature=0.0,
    prompt_text="You are a helpful assistant.",
    semantic_bucket="weather_queries",
    duration_ms=1500,
    random_seed=12345,
)

# Save to file
artifact.save("manual_artifact.kurral")

print(f"✅ Created artifact: {artifact.kurral_id}")
print(f"Deterministic: {artifact.deterministic}")
print(f"Replay Level: {artifact.replay_level.value}")
print(f"Score: {artifact.determinism_report.overall_score:.4f}")

