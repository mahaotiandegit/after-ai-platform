from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv" / "bin" / "python"

LOG_FILE = Path("/tmp/after_ai_run_all_acceptance_uvicorn.log")

ORDERED_ACCEPTANCE = [
    # AI quality 主链路，按依赖顺序执行
    "ai_quality_overview_acceptance.py",
    "ai_quality_trends_acceptance.py",
    "ai_quality_evaluations_acceptance.py",
    "ai_quality_evaluation_summary_acceptance.py",
    "ai_quality_payload_adapter_acceptance.py",
    "ai_quality_to_bad_case_acceptance.py",
]


def run(cmd: list[str], *, cwd: Path = ROOT, check: bool = True):
    print()
    print("----- RUN:", " ".join(cmd), "-----")
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout)

    if check and result.returncode != 0:
        raise SystemExit(result.returncode)

    return result


def port_8000_pids() -> list[str]:
    result = subprocess.run(
        ["bash", "-lc", "command -v lsof >/dev/null 2>&1 && lsof -tiTCP:8000 -sTCP:LISTEN || true"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def stop_existing_backend():
    pids = port_8000_pids()
    if not pids:
        print("[OK] no existing process on port 8000")
        return

    print("[INFO] killing old process on port 8000:", " ".join(pids))
    subprocess.run(["kill", *pids], text=True)
    time.sleep(1)


def start_backend():
    if not PYTHON.exists():
        raise SystemExit(f"[FAIL] python not found: {PYTHON}")

    stop_existing_backend()

    log = LOG_FILE.open("w")
    process = subprocess.Popen(
        [
            str(PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        cwd=str(ROOT),
        stdout=log,
        stderr=subprocess.STDOUT,
    )

    print("[INFO] uvicorn pid:", process.pid)
    print("[INFO] uvicorn log:", LOG_FILE)

    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/healthz", timeout=1)
            print("[OK] backend healthy")
            return process
        except Exception:
            time.sleep(1)

    print("[FAIL] backend did not become healthy")
    print("----- uvicorn log tail -----")
    if LOG_FILE.exists():
        print(LOG_FILE.read_text(errors="replace")[-8000:])
    process.terminate()
    raise SystemExit(1)


def collect_acceptance_scripts() -> list[Path]:
    acceptance_dir = ROOT / "scripts" / "acceptance"

    ordered = []
    seen = set()

    for name in ORDERED_ACCEPTANCE:
        path = acceptance_dir / name
        if path.exists():
            ordered.append(path)
            seen.add(path.name)
        else:
            print("[SKIP] missing:", name)

    extra = sorted(
        p
        for p in acceptance_dir.glob("*_acceptance.py")
        if p.name not in seen and p.name != "run_all_acceptance.py"
    )

    return ordered + extra


def main():
    print("========== AFTER-AI BACKEND RUN ALL ACCEPTANCE ==========")
    print("ROOT =", ROOT)

    run([str(PYTHON), "-m", "compileall", "app", "scripts/acceptance"], check=True)

    process = start_backend()

    try:
        scripts = collect_acceptance_scripts()

        if not scripts:
            raise SystemExit("[FAIL] no acceptance scripts found")

        print()
        print("========== acceptance scripts ==========")
        for script in scripts:
            print("-", script.relative_to(ROOT))

        passed = []
        failed = []

        for script in scripts:
            print()
            print("=" * 80)
            print("RUN ACCEPTANCE:", script.relative_to(ROOT))
            print("=" * 80)

            result = subprocess.run(
                [str(PYTHON), str(script)],
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            print(result.stdout)

            if result.returncode == 0:
                passed.append(script.name)
            else:
                failed.append(script.name)
                print("----- uvicorn log tail -----")
                if LOG_FILE.exists():
                    print(LOG_FILE.read_text(errors="replace")[-10000:])
                break

        print()
        print("========== SUMMARY ==========")
        print("passed:", len(passed))
        for name in passed:
            print("  [PASS]", name)

        print("failed:", len(failed))
        for name in failed:
            print("  [FAIL]", name)

        if failed:
            raise SystemExit(1)

        print()
        print("[PASS] all backend acceptance scripts passed")

    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
