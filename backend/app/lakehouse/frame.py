from collections import defaultdict
from collections.abc import Callable
from typing import Any

Row = dict[str, Any]


class Frame:
    """Small DataFrame stand-in for Spark-style transforms.

    On Databricks these would be Spark DataFrames over Delta tables.
    """

    def __init__(self, rows: list[Row]) -> None:
        self.rows = list(rows)

    def filter(self, predicate: Callable[[Row], bool]) -> "Frame":
        return Frame([row for row in self.rows if predicate(row)])

    def select(self, *columns: str) -> "Frame":
        return Frame([{column: row[column] for column in columns} for row in self.rows])

    def join(self, other: "Frame", on: str) -> "Frame":
        lookup = {row[on]: row for row in other.rows}
        joined: list[Row] = []
        for row in self.rows:
            match = lookup.get(row[on])
            if match is None:
                continue
            merged = {**row, **{key: value for key, value in match.items() if key != on}}
            joined.append(merged)
        return Frame(joined)

    def group_by_count(self, column: str) -> "Frame":
        counts: dict[Any, int] = defaultdict(int)
        for row in self.rows:
            counts[row[column]] += 1
        return Frame([{column: key, "count": value} for key, value in sorted(counts.items())])


def sql_count_by_category(frame: Frame) -> Frame:
    """Equivalent to: SELECT category, COUNT(*) FROM documents GROUP BY category."""
    return frame.group_by_count("category")
