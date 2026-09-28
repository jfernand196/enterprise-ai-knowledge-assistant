import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield each event; a torn last line from a crash is skipped instead of failing startup."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue
