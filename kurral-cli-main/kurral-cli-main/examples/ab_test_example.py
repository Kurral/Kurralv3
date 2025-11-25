"""
Example: A/B Testing for Agent Version Comparison

This example demonstrates how to use Kurral's A/B testing capabilities
to validate agent changes before deployment.

Use cases:
- Model migration (GPT-4 → GPT-4-turbo)
- Prompt optimization
- Temperature tuning
- Tool addition/removal
- Configuration changes
"""

import asyncio
from kurral.core.ab_test import ABTestEngine, VersionConfig, ComparativeABTest
from kurral.models.kurral import KurralArtifact
from pathlib import Path


async def example_model_migration():
    """
    Example: Test migration from GPT-4 to GPT-4-turbo
    
    Decision criteria:
    - Version B (GPT-4-turbo) must maintain ARS >= 0.90
    - No regressions in critical paths
    - Similar or better performance
    """
    print("=" * 60)
    print("Example 1: Model Migration")
    print("=" * 60)
    
    # Load baseline artifacts from production
    baseline_artifacts = load_baseline_artifacts("./artifacts")
    
    if not baseline_artifacts:
        print("⚠️  No baseline artifacts found. Run your agent first with @trace_llm")
        return
    
    # Define versions
    version_a = VersionConfig(
        name="production-gpt4",
        model_name="gpt-4",
    )
    
    version_b = VersionConfig(
        name="candidate-gpt4-turbo",
        model_name="gpt-4-turbo",
    )
    
    # Run A/B test
    engine = ABTestEngine()
    result = await engine.run_ab_test(
        test_suite=baseline_artifacts,
        version_a=version_a,
        version_b=version_b,
        threshold=0.90,
        min_samples=5,
    )
    
    # Display results
    print(f"\n{result.summary}\n")
    
    # Make decision
    if result.recommendation == "deploy":
        print("✅ Safe to migrate to GPT-4-turbo")
        print(f"   Mean ARS improvement: {result.b_improvement:+.2%}")
    elif result.recommendation == "reject":
        print("❌ Do not migrate - regressions detected")
        print(f"   Failures: {len(result.failures)}")
    else:
        print("⚠️  Manual review required")
    
    return result


async def example_prompt_optimization():
    """
    Example: Test prompt changes
    
    Compare current prompt vs optimized version
    """
    print("\n" + "=" * 60)
    print("Example 2: Prompt Optimization")
    print("=" * 60)
    
    baseline_artifacts = load_baseline_artifacts("./artifacts")
    
    if not baseline_artifacts:
        print("⚠️  No baseline artifacts found")
        return
    
    current_prompt = """
You are a helpful customer support assistant.
Answer questions clearly and concisely.
"""
    
    optimized_prompt = """
You are a friendly customer support expert for Acme Corp.

Guidelines:
- Always be empathetic and understanding
- Provide clear, step-by-step solutions
- Offer to escalate if issue persists
- Use positive, professional language

Your goal is customer satisfaction and issue resolution.
"""
    
    # Run comparison
    engine = ComparativeABTest()
    result = await engine.test_prompt_change(
        baseline_artifacts=baseline_artifacts,
        current_prompt=current_prompt,
        new_prompt=optimized_prompt,
        threshold=0.90,
    )
    
    print(f"\n{result.summary}\n")
    
    # Analyze per-artifact results
    improvements = sum(1 for score in result.per_artifact_scores if score["b_improvement"] > 0)
    regressions = sum(1 for score in result.per_artifact_scores if score["b_improvement"] < 0)
    
    print(f"Detailed Analysis:")
    print(f"  Improvements: {improvements}")
    print(f"  Regressions: {regressions}")
    print(f"  Neutral: {len(result.per_artifact_scores) - improvements - regressions}")
    
    return result


async def example_temperature_tuning():
    """
    Example: Test temperature parameter changes
    
    Find optimal temperature for your use case
    """
    print("\n" + "=" * 60)
    print("Example 3: Temperature Tuning")
    print("=" * 60)
    
    baseline_artifacts = load_baseline_artifacts("./artifacts")
    
    if not baseline_artifacts:
        print("⚠️  No baseline artifacts found")
        return
    
    # Test multiple temperature values
    temperatures = [0.0, 0.3, 0.7, 1.0]
    results = []
    
    engine = ComparativeABTest()
    
    for temp in temperatures:
        print(f"\n Testing temperature={temp}...")
        
        result = await engine.test_temperature_tuning(
            baseline_artifacts=baseline_artifacts[:5],  # Sample for speed
            current_temp=0.0,  # Baseline
            new_temp=temp,
            threshold=0.85,  # Slightly lower threshold for exploration
        )
        
        results.append({
            "temperature": temp,
            "mean_ars": result.b_mean_ars,
            "improvement": result.b_improvement,
        })
    
    # Find optimal temperature
    print("\n" + "-" * 60)
    print("Temperature Tuning Results:")
    print("-" * 60)
    
    for r in results:
        status = "✅" if r["mean_ars"] >= 0.85 else "❌"
        print(f"{status} temp={r['temperature']:.1f}: ARS={r['mean_ars']:.4f} (Δ {r['improvement']:+.4f})")
    
    best = max(results, key=lambda x: x["mean_ars"])
    print(f"\n🏆 Optimal temperature: {best['temperature']} (ARS: {best['mean_ars']:.4f})")
    
    return results


async def example_custom_config_comparison():
    """
    Example: Compare complex configuration changes
    
    Test multiple parameter changes at once
    """
    print("\n" + "=" * 60)
    print("Example 4: Custom Configuration Comparison")
    print("=" * 60)
    
    baseline_artifacts = load_baseline_artifacts("./artifacts")
    
    if not baseline_artifacts:
        print("⚠️  No baseline artifacts found")
        return
    
    # Current production config
    version_a = VersionConfig(
        name="production-v1.0",
        model_name="gpt-4",
        temperature=0.0,
        max_tokens=500,
        metadata={"version": "1.0.0", "env": "production"},
    )
    
    # Candidate config with multiple changes
    version_b = VersionConfig(
        name="candidate-v1.1",
        model_name="gpt-4-turbo",  # Changed model
        temperature=0.2,            # Slight temperature increase
        max_tokens=1000,            # Higher token limit
        metadata={"version": "1.1.0", "env": "staging"},
    )
    
    # Run comprehensive test
    engine = ABTestEngine()
    result = await engine.run_ab_test(
        test_suite=baseline_artifacts,
        version_a=version_a,
        version_b=version_b,
        threshold=0.90,
        parallel_execution=True,  # Faster testing
    )
    
    print(f"\n{result.summary}\n")
    
    # Show per-artifact breakdown
    if result.per_artifact_scores:
        print("Per-Artifact Results:")
        for i, score in enumerate(result.per_artifact_scores[:5], 1):
            artifact_id = score["artifact_id"][:8]
            improvement = score["b_improvement"]
            status = "📈" if improvement > 0 else "📉" if improvement < 0 else "➡️"
            
            print(f"  {status} {artifact_id}... : "
                  f"A={score['a_ars']:.3f} B={score['b_ars']:.3f} "
                  f"(Δ {improvement:+.3f})")
    
    return result


def load_baseline_artifacts(artifacts_dir: str) -> list[KurralArtifact]:
    """
    Load baseline artifacts from directory
    
    In production, you'd load from:
    - Semantic bucket (semantic:customer_support)
    - Date range (last 30 days)
    - Specific tenant
    """
    artifacts = []
    path = Path(artifacts_dir)
    
    if not path.exists():
        return []
    
    # Load .kurral files
    for file in path.glob("*.kurral"):
        try:
            artifact = KurralArtifact.from_json(file.read_text())
            artifacts.append(artifact)
        except Exception as e:
            print(f"⚠️  Failed to load {file.name}: {e}")
    
    return artifacts


async def main():
    """
    Run all examples
    
    To run specific examples:
        await example_model_migration()
        await example_prompt_optimization()
        await example_temperature_tuning()
        await example_custom_config_comparison()
    """
    print("\n" + "=" * 60)
    print("Kurral A/B Testing Examples")
    print("=" * 60)
    print()
    print("These examples demonstrate how to validate agent changes")
    print("before deploying to production.")
    print()
    
    # Run examples
    await example_model_migration()
    await example_prompt_optimization()
    await example_temperature_tuning()
    await example_custom_config_comparison()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())

