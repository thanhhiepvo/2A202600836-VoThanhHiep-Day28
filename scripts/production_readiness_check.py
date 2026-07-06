# scripts/production_readiness_check.py
import os
import subprocess
import sys

import redis
import requests
from dotenv import load_dotenv

load_dotenv()

results = {}


def check(name, fn):
    try:
        fn()
        results[name] = "PASS"
        print(f"  [PASS] {name}")
    except Exception as e:
        results[name] = f"FAIL: {e}"
        print(f"  [FAIL] {name}: {e}")


def kafka_container_name() -> str:
  """Resolve Kafka container name regardless of compose project folder."""
  result = subprocess.run(
      ["docker", "compose", "ps", "-q", "kafka"],
      capture_output=True,
      text=True,
      cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
  )
  container_id = result.stdout.strip()
  if not container_id:
      raise RuntimeError("Kafka container not running. Run: docker compose up -d")
  name_result = subprocess.run(
      ["docker", "inspect", "--format", "{{.Name}}", container_id],
      capture_output=True,
      text=True,
      check=True,
  )
  return name_result.stdout.strip().lstrip("/")


print("\n=== RELIABILITY ===")
check(
    "Health check endpoint",
    lambda: requests.get("http://localhost:8000/health", timeout=5).raise_for_status(),
)
check(
    "API Gateway responds",
    lambda: requests.get("http://localhost:8000/docs", timeout=5).raise_for_status(),
)

print("\n=== OBSERVABILITY ===")
check(
    "Prometheus up",
    lambda: requests.get("http://localhost:9090/-/healthy", timeout=5).raise_for_status(),
)
check(
    "Grafana up",
    lambda: requests.get("http://localhost:3000/api/health", timeout=5).raise_for_status(),
)
check(
    "Metrics endpoint exposed",
    lambda: requests.get("http://localhost:8000/metrics", timeout=5).raise_for_status(),
)

print("\n=== SECURITY ===")


def check_unauthorized():
    r = requests.get("http://localhost:8000/admin", timeout=5)
    assert r.status_code in [401, 403, 404]


check("Unauthorized request rejected", check_unauthorized)

print("\n=== VECTOR STORE ===")
check(
    "Qdrant healthy",
    lambda: requests.get("http://localhost:6333/healthz", timeout=5).raise_for_status(),
)


def check_collection_exists():
    r = requests.get("http://localhost:6333/collections/documents", timeout=5)
    r.raise_for_status()


check("Collection exists", check_collection_exists)

print("\n=== FEATURE STORE ===")
check("Redis reachable", lambda: redis.Redis(host="localhost", port=6379).ping())

print("\n=== KAFKA ===")


def check_kafka_topics():
    container = kafka_container_name()
    result = subprocess.run(
        [
            "docker",
            "exec",
            container,
            "kafka-topics",
            "--list",
            "--bootstrap-server",
            "localhost:9092",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "data.raw" in result.stdout


check("Kafka topics exist", check_kafka_topics)

passed = sum(1 for v in results.values() if v == "PASS")
total = len(results)
score = (passed / total) * 100
print(f"\n{'=' * 40}")
print(f"Production Readiness Score: {passed}/{total} = {score:.0f}%")
print(f"Target: >80% — Status: {'READY' if score >= 80 else 'NOT READY'}")
sys.exit(0 if score >= 80 else 1)
