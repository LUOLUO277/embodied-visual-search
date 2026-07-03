from __future__ import annotations

import json
import sys
from pathlib import Path


def convert_task(raw: dict) -> dict:
    return {
        "scene": raw.get("scene"),
        "task_type": raw.get("tasktype"),
        "task_instruction": raw.get("taskquery") or raw.get("taskname") or "",
        "target_objects": raw.get("target_objects") or [],
        "related_objects": raw.get("related_objects") or [],
        "navigable_objects": raw.get("navigable_objects") or [],
        "reference_actions": ((raw.get("task_metadata") or {}).get("actions") or []),
    }


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("Usage: python scripts/import_official_test_tasks.py <input.json> <output.json>")
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    payload = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        items = payload.get("tasks") or payload.get("episodes") or []
    else:
        items = payload
    converted = [convert_task(item) for item in items]
    target.write_text(json.dumps(converted, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(converted)} tasks to {target}")


if __name__ == "__main__":
    main()
