import json
from pathlib import Path
from typing import Any

Row = dict[str, Any]


class DeltaTable:
    """Versioned table with overwrite, merge, and time travel.

    This is the local equivalent of a Delta Lake table. Databricks would
    provide ACID, schema enforcement, and time travel on object storage.
    """

    def __init__(self, root: Path, name: str) -> None:
        self._dir = root / name

    def latest_version(self) -> int | None:
        versions = self.versions()
        return versions[-1] if versions else None

    def versions(self) -> list[int]:
        if not self._dir.exists():
            return []
        return sorted(
            int(path.stem.removeprefix("v"))
            for path in self._dir.glob("v*.json")
        )

    def write(self, rows: list[Row]) -> int:
        self._dir.mkdir(parents=True, exist_ok=True)
        latest = self.latest_version()
        version = 0 if latest is None else latest + 1
        self._path(version).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return version

    def read(self, version: int | None = None) -> list[Row]:
        target = self.latest_version() if version is None else version
        if target is None:
            return []
        path = self._path(target)
        if not path.exists():
            raise FileNotFoundError(f"Version {target} not found for {self._dir.name}")
        return json.loads(path.read_text(encoding="utf-8"))

    def merge(self, incoming: list[Row], key: str) -> int:
        current = {row[key]: row for row in self.read()}
        for row in incoming:
            current[row[key]] = row
        return self.write(list(current.values()))

    def _path(self, version: int) -> Path:
        return self._dir / f"v{version:03d}.json"
