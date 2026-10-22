"""Summarize a Spark benchmark directory (moved to examples_core/spark_summary.py, shared by the use cases).

    uv run python -m walmart_grocery_forecasting.pipeline.spark_summary DIR > DIR/summary.md
"""

from __future__ import annotations

import sys
from pathlib import Path

from examples_core.spark_summary import summarize

if __name__ == '__main__':
    from examples_core.records import utf8_stdout

    utf8_stdout()
    print(summarize(Path(sys.argv[1])), end='')
