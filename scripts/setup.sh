#!/usr/bin/env bash
# One-command local setup (run from repo root)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit VLLM_NGROK_URL and EMBED_NGROK_URL before chat tests."
fi

echo "=== Installing Python dependencies (Python 3.11 recommended) ==="
if command -v python3.11 &>/dev/null; then
  PYTHON=python3.11
else
  PYTHON=python3
fi
$PYTHON -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt

echo "=== Starting Docker stack ==="
docker compose up -d --build

echo "=== Waiting for services (30s) ==="
sleep 30
docker compose ps

echo "=== Running integration pipeline ==="
LOCAL_EMBED=1 python scripts/run_full_pipeline.py

echo ""
echo "=== Setup complete ==="
echo "NOTE: Stop other Docker stacks using ports 8000/3000/9090 before setup."
echo "      Example: docker stop day23-app day23-grafana day23-prometheus"
echo ""
echo "  Prefect UI:  http://localhost:4200"
echo "  Grafana:     http://localhost:3000 (admin/admin) → Dashboard: Lab28 AI Platform"
echo "  API Gateway: http://localhost:8000/health"
echo ""
echo "For local smoke tests without Kaggle: set MOCK_VLLM=1 in .env, then:"
echo "  docker compose up -d --build api-gateway"
echo ""
echo "For final submission with real vLLM:"
echo "  1. Follow kaggle/KAGGLE_SETUP.md"
echo "  2. Set VLLM_NGROK_URL and EMBED_NGROK_URL in .env, MOCK_VLLM=0"
echo "  3. docker compose up -d --build api-gateway"
echo "  4. pytest smoke-tests/ -v"
echo "  5. python scripts/production_readiness_check.py"
echo "  6. Capture screenshots → screenshots/"
echo "  7. Include ANSWERS.md in submission"
