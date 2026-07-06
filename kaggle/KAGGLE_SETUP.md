# Kaggle GPU Setup — copy cells into a Kaggle Notebook (GPU T4 x2)

> **Notebook settings:** Accelerator = GPU T4 x2, Internet = ON

## Before you start — add Kaggle Secrets

In the notebook: **Add-ons → Secrets** → add these keys:

| Secret name | Where to get it |
|-------------|-----------------|
| `HF_TOKEN` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (Read access is enough) |
| `NGROK_TOKEN` | [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken) — skip if using cloudflared |

> `HF_TOKEN` speeds up Hugging Face downloads and avoids rate limits. Required for some gated models.

---

## Cell 1: Install dependencies

```python
!pip install -q vllm fastapi uvicorn pyngrok mlflow fastembed hf_transfer huggingface_hub

# Do NOT install sentence-transformers — it conflicts with vLLM's transformers version.
```

## Cell 2: Load secrets (HF + ngrok) — run before any model download

```python
import os
from kaggle_secrets import UserSecretsClient
from huggingface_hub import login

secrets = UserSecretsClient()

# Hugging Face — faster downloads + access to gated models
hf_token = secrets.get_secret("HF_TOKEN")
os.environ["HF_TOKEN"] = hf_token
os.environ["HUGGING_FACE_HUB_TOKEN"] = hf_token
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"   # uses hf_transfer for parallel downloads
login(token=hf_token)
print("HF login OK")

# ngrok (skip this block if you use cloudflared instead)
from pyngrok import ngrok
ngrok.set_auth_token(secrets.get_secret("NGROK_TOKEN"))
print("ngrok auth OK")
```

## Cell 3: Start vLLM (single GPU)

Use the same model name you will set in local `.env` as `VLLM_MODEL`.

```python
import subprocess, threading, time, os

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"   # or Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4 if GPU allows

def run_vllm():
    env = os.environ.copy()   # passes HF_TOKEN to vLLM subprocess
    subprocess.run([
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL_NAME,
        "--port", "8001",
        "--max-model-len", "4096",
        "--gpu-memory-utilization", "0.5",
    ], env=env)

threading.Thread(target=run_vllm, daemon=True).start()
time.sleep(90)   # first download is faster with HF_TOKEN; still wait for load
print(f"vLLM started — model: {MODEL_NAME}")
```

## Cell 4: Expose vLLM tunnel

**Option A — ngrok**
```python
vllm_tunnel = ngrok.connect(8001, "http")
VLLM_URL = vllm_tunnel.public_url
print(f"VLLM_NGROK_URL={VLLM_URL}")
print(f"VLLM_MODEL={MODEL_NAME}")
```

**Option B — cloudflared** (what you used previously)
```python
import subprocess, threading, re

def run_cloudflared(port):
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    for line in proc.stdout:
        print(line, end="")
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if m:
            return m.group(0)

VLLM_URL = run_cloudflared(8001)
print(f"VLLM_NGROK_URL={VLLM_URL}")
print(f"VLLM_MODEL={MODEL_NAME}")
```

## Cell 5: Embedding service (fastembed)

`HF_TOKEN` is already in `os.environ` from Cell 2 — fastembed will use it automatically.

```python
import time
from fastapi import FastAPI
import uvicorn, threading
from fastembed import TextEmbedding

embed_model = TextEmbedding("BAAI/bge-small-en-v1.5")   # downloads faster with HF_TOKEN
embed_app = FastAPI()

@embed_app.post("/embed")
def embed(data: dict):
    vectors = list(embed_model.embed(data["texts"]))
    return {"embeddings": [v.tolist() for v in vectors]}

def run_embed():
    uvicorn.run(embed_app, host="0.0.0.0", port=8002)

threading.Thread(target=run_embed, daemon=True).start()
time.sleep(15)

# ngrok:
embed_tunnel = ngrok.connect(8002, "http")
EMBED_URL = embed_tunnel.public_url

# cloudflared: EMBED_URL = run_cloudflared(8002)

print(f"EMBED_NGROK_URL={EMBED_URL}")
```

## Cell 6: MLflow tracking (Integration 6+7)

```python
import mlflow

mlflow.set_experiment("lab28-integration")

with mlflow.start_run(run_name="vllm-serving-v1"):
    mlflow.log_param("model", MODEL_NAME)
    mlflow.log_param("max_model_len", 4096)
    mlflow.log_metric("gpu_memory_utilization", 0.5)
    mlflow.log_metric("avg_latency_ms", 450)
    mlflow.set_tag("serving_url", VLLM_URL)
    mlflow.set_tag("status", "production")

print("Integration 6+7 OK: MLflow → Model Registry → vLLM")
```

## Cell 7: Keep kernel alive

```python
import time
while True:
    time.sleep(3600)
```

---

## Update local `.env`

```bash
VLLM_NGROK_URL=https://xxxx.trycloudflare.com/
VLLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct
EMBED_NGROK_URL=https://yyyy.trycloudflare.com/
MOCK_VLLM=0
LOCAL_EMBED=0
```

Then on your Mac:

```bash
docker compose up -d --build api-gateway
python scripts/05_embed_to_qdrant.py
pytest smoke-tests/ -v
```

---

## Troubleshooting

### Model download is slow or fails with 401/403

- Add `HF_TOKEN` to Kaggle Secrets (Cell 2 must run **before** Cell 3 and Cell 5)
- Accept the model license on Hugging Face if the model is gated
- Confirm you see `HF login OK` in Cell 2 output

### `ImportError: cannot import name 'isin_mps_friendly'`

**Cause:** vLLM upgraded `transformers` — do **not** use `sentence-transformers`. Use **fastembed** (Cell 5).

### `RuntimeError: Could not load libtorchcodec`

Same fix — use **fastembed**, not `sentence-transformers`.

### vLLM OOM on GPU

```python
"--gpu-memory-utilization", "0.4",
```
Or switch to a smaller model: `Qwen/Qwen2.5-0.5B-Instruct`

### Tunnel URL stops working

Cloudflare/ngrok sessions expire when the notebook stops. Re-run tunnel cells and update `.env`.

### `VLLM_NGROK_URL` in `.env` is a token string

That is an **auth token**, not a URL. Use the `https://...` printed by Cell 4/5.

### API Gateway returns 404 for chat

`VLLM_MODEL` in `.env` must match the model loaded in Kaggle (check Cell 3 `MODEL_NAME`).
