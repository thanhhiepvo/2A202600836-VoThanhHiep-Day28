# scripts/run_full_pipeline.py
"""Run all local integration steps in order (Integrations 1–5)."""
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def run(cmd: list[str]):
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    os.chdir(ROOT)
    print("=== Lab28 Full Pipeline ===\n")

    run([sys.executable, "scripts/01_ingest_to_kafka.py"])
    run([sys.executable, "scripts/02_kafka_to_delta.py"])
    run([sys.executable, "scripts/03_delta_to_feast.py"])
    run([sys.executable, "scripts/05_embed_to_qdrant.py"])

    print("\n=== Pipeline complete ===")
    print("Next steps:")
    print("  1. Set VLLM_NGROK_URL in .env from Kaggle (see kaggle/KAGGLE_SETUP.md)")
    print("  2. docker compose up -d --build api-gateway")
    print("  3. pytest smoke-tests/ -v")
    print("  4. python scripts/production_readiness_check.py")


if __name__ == "__main__":
    main()
