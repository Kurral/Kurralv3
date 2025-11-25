"""
Example of running a backtest for regression testing
"""

import asyncio

from kurral.core.backtest import BacktestEngine
from kurral.models.kurral import KurralArtifact


async def run_backtest():
    """Run backtest comparing baseline against new config"""

    # Load baseline artifacts (golden test set)
    baseline_artifacts = [
        KurralArtifact.load("baseline_1.kurral"),
        KurralArtifact.load("baseline_2.kurral"),
        KurralArtifact.load("baseline_3.kurral"),
    ]

    # New agent configuration to test
    candidate_config = {
        "model_name": "gpt-4-1106-preview",  # New model
        "temperature": 0.0,
        "prompt": "You are a helpful assistant. Be concise.",
    }

    # Run backtest
    engine = BacktestEngine()
    result = await engine.backtest(
        baseline_artifacts=baseline_artifacts,
        candidate_config=candidate_config,
        threshold=0.90,  # 90% similarity required to pass
        sample_strategy="adaptive",
    )

    # Display results
    print(f"\n{'='*50}")
    print(f"Backtest Results")
    print(f"{'='*50}")
    print(f"ARS Score: {result.ars_score:.4f}")
    print(f"Threshold: {result.threshold:.4f}")
    print(f"Passed: {result.passed}")
    print(f"Failures: {len(result.failures)}")
    print(f"\n{result.summary}")

    if result.failures:
        print(f"\nFailed Artifacts:")
        for failure in result.failures:
            print(f"  - {failure['kurral_id']}: ARS={failure['ars_score']:.4f}")

    # Return exit code for CI/CD
    return 0 if result.passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_backtest())
    exit(exit_code)

