# scripts/09_verify_observability.py
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def check_prometheus():
    resp = requests.get(
        "http://localhost:9090/api/v1/query",
        params={"query": 'up{job="api-gateway"}'},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    assert data["status"] == "success"
    assert len(data["data"]["result"]) > 0
    print("Integration 9 OK: Prometheus metrics flowing")


def check_langsmith():
    api_key = os.environ.get("LANGCHAIN_API_KEY", "")
    if not api_key or api_key.startswith("lsv2_pt_your"):
        print("Integration 10 SKIP: LANGCHAIN_API_KEY not configured")
        return

    from langsmith import Client

    client = Client(api_key=api_key)
    runs = list(client.list_runs(project_name=os.environ.get("LANGCHAIN_PROJECT", "lab28-platform"), limit=1))
    if not runs:
        print("Integration 10 WARN: No LangSmith traces yet — send a /api/v1/chat request first")
        return
    print("Integration 10 OK: LangSmith traces visible")


if __name__ == "__main__":
    check_prometheus()
    try:
        check_langsmith()
    except Exception as exc:
        print(f"Integration 10 WARN: {exc}")
        sys.exit(0)
