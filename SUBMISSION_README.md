# Lab28 Submission — Vo Thanh Hiep (2A202600836)

End-to-end AI platform: Kafka → Prefect → Delta Lake → Feast (Redis) → Qdrant → API Gateway → vLLM (Kaggle GPU).

## Quick verification

```bash
docker compose ps
pytest smoke-tests/ -v
python scripts/production_readiness_check.py
```

## Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| API Gateway | http://localhost:8000/health | — |
| Prefect | http://localhost:4200 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Qdrant | http://localhost:6333/dashboard | — |

## Architecture reflection

See [ANSWERS.md](ANSWERS.md) for responses to the 5 submission questions.

## Screenshots

All demo screenshots are in [`screenshots/`](screenshots/):

- `prefect_ui.png` — Prefect orchestration UI
- `grafana_dashboard.png` — Lab28 metrics dashboard
- `api_gateway.png` — Health + chat API responses
- `kaggle_notebook_ui.png` — **Real Kaggle notebook UI** (vLLM APIServer running)
- `kaggle_notebook.png` — Kaggle tunnel verification (vLLM + fastembed live test)
- `smoke_tests_results.png` — 8/8 pytest passing
- `production_readiness.png` — 100% readiness score
- `prometheus_targets.png` — Prometheus scrape targets

## Kaggle GPU setup

See [kaggle/KAGGLE_SETUP.md](kaggle/KAGGLE_SETUP.md).

## Student

- **ID:** 2A202600836
- **Name:** Vo Thanh Hiep
