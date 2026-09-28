"""Quality gate: run the golden set and fail when the pass rate drops.

    cd backend && .venv/bin/python -m app.llmops.gate --min-pass-rate 0.85
"""

import argparse
import asyncio
import sys

from app.main import app, lifespan
from app.schemas.evaluation import EvaluationReport


async def evaluate() -> EvaluationReport:
    async with lifespan(app):
        return await app.state.evaluation_service.create_report()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args()

    report = asyncio.run(evaluate())
    for result in report.results:
        failed = [name for name, ok in result.checks.items() if not ok]
        status = "PASS" if result.passed else f"FAIL ({', '.join(failed)})"
        print(f"{status:<28} {result.id:<24} {result.latency_ms:>6} ms  {result.model}")
    print(f"\n{report.prompt_version}: {report.passed}/{report.cases} passed ({report.pass_rate:.0%}); rates {report.check_rates}")

    if report.pass_rate < args.min_pass_rate:
        print(f"Gate failed: pass rate {report.pass_rate:.0%} is below {args.min_pass_rate:.0%}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
