from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}

    for file in [Path(".env"), Path("../.env")]:
        if not file.exists():
            continue

        for line in file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")

    return env


def jsonable(value: Any):
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        return str(value)


def compact(value: Any, max_len: int = 900):
    value = jsonable(value)
    text = json.dumps(value, ensure_ascii=False, indent=2)
    if len(text) > max_len:
        return text[:max_len] + "\n...<truncated>"
    return text


def payload_keys(value: Any, depth: int = 0, prefix: str = "") -> list[str]:
    if depth > 3:
        return []

    keys: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            keys.append(path)
            keys.extend(payload_keys(child, depth + 1, path))
    elif isinstance(value, list) and value:
        keys.extend(payload_keys(value[0], depth + 1, f"{prefix}[0]" if prefix else "[0]"))

    return keys


def main():
    env = load_env()
    url = (
        os.getenv("DATABASE_URL")
        or env.get("DATABASE_URL")
        or env.get("DB_DSN")
        or env.get("POSTGRES_DSN")
    )

    if not url:
        raise SystemExit("[FAIL] DATABASE_URL / DB_DSN / POSTGRES_DSN not found")

    engine = create_engine(url)

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    id,
                    scene,
                    provider,
                    model,
                    success,
                    output_payload,
                    created_at
                FROM ai_invocation_logs
                ORDER BY created_at DESC
                LIMIT 20
            """)
        ).mappings().all()

    print("========== AI Invocation Payload Inspection ==========")
    print("sample_count =", len(rows))

    for i, row in enumerate(rows, start=1):
        payload = row["output_payload"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                pass

        print()
        print(f"----- #{i} -----")
        print("id       =", row["id"])
        print("scene    =", row["scene"])
        print("provider =", row["provider"])
        print("model    =", row["model"])
        print("success  =", row["success"])
        print("created  =", row["created_at"])
        print("keys     =", payload_keys(payload))
        print("payload  =")
        print(compact(payload))


if __name__ == "__main__":
    main()
