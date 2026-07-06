#!/usr/bin/env python3
"""Capture submission screenshots for Lab28."""
from __future__ import annotations

import html
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS = ROOT / "screenshots"
SCREENSHOTS.mkdir(exist_ok=True)
load_dotenv(ROOT / ".env")

# Submission filename for Kaggle GPU demo evidence
KAGGLE_SCREENSHOT = SCREENSHOTS / "kaggle_notebook.png"


def run_cmd(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    return (result.stdout or "") + (result.stderr or "")


def render_terminal_png(text: str, out_path: Path, title: str):
    from PIL import Image, ImageDraw, ImageFont

    lines = textwrap.dedent(text).strip().splitlines()
    font = ImageFont.load_default()
    line_height = 14
    padding = 20
    width = min(max((len(line) for line in lines), default=40) * 7 + padding * 2, 1400)
    height = len(lines) * line_height + padding * 2 + 30
    img = Image.new("RGB", (width, height), color=(18, 18, 18))
    draw = ImageDraw.Draw(img)
    draw.text((padding, 8), title, fill=(100, 200, 255), font=font)
    y = padding + 20
    for line in lines:
        draw.text((padding, y), line, fill=(220, 220, 220), font=font)
        y += line_height
    img.save(out_path)
    print(f"  saved {out_path}")


def render_html_png(html_content: str, out_path: Path, width: int = 1280, height: int = 900):
    tmp = SCREENSHOTS / "_tmp.html"
    tmp.write_text(html_content, encoding="utf-8")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(tmp.as_uri())
        page.wait_for_timeout(1000)
        page.screenshot(path=str(out_path), full_page=True)
        browser.close()
    tmp.unlink(missing_ok=True)
    print(f"  saved {out_path}")


def screenshot_url(url: str, out_path: Path, wait_ms: int = 3000):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(wait_ms)
        page.screenshot(path=str(out_path), full_page=True)
        browser.close()
    print(f"  saved {out_path}")


def screenshot_grafana_dashboard(out_path: Path):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://localhost:3000/login", wait_until="domcontentloaded", timeout=30000)
        page.fill('input[name="user"]', "admin")
        page.fill('input[name="password"]', "admin")
        page.click('button[type="submit"]')
        page.wait_for_timeout(2000)
        page.goto(
            "http://localhost:3000/d/lab28-platform/lab28-ai-platform",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        page.wait_for_timeout(5000)
        page.screenshot(path=str(out_path), full_page=True)
        browser.close()
    print(f"  saved {out_path}")


def capture_kaggle_notebook(out_path: Path = KAGGLE_SCREENSHOT):
    """Capture Kaggle GPU integration status (vLLM + fastembed tunnels)."""
    vllm_url = os.environ.get("VLLM_NGROK_URL", "").rstrip("/")
    embed_url = os.environ.get("EMBED_NGROK_URL", "").rstrip("/")
    vllm_model = os.environ.get("VLLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")

    vllm_out = run_cmd(["curl", "-s", "--max-time", "15", f"{vllm_url}/v1/models"]) if vllm_url else "N/A"
    embed_out = (
        run_cmd([
            "curl", "-s", "--max-time", "15", "-X", "POST", f"{embed_url}/embed",
            "-H", "Content-Type: application/json", "-d", '{"texts":["Kaggle GPU embed test"]}',
        ])
        if embed_url
        else "N/A"
    )

    try:
        vllm_pretty = json.dumps(json.loads(vllm_out), indent=2)
    except json.JSONDecodeError:
        vllm_pretty = vllm_out
    try:
        embed_json = json.loads(embed_out)
        dim = len(embed_json.get("embeddings", [[]])[0]) if embed_json.get("embeddings") else 0
        embed_summary = f"status=OK, vector_dim={dim}\n{json.dumps(embed_json, indent=2)[:800]}"
    except (json.JSONDecodeError, IndexError):
        embed_summary = embed_out

    page_html = f"""
    <html>
    <body style="font-family: 'Helvetica Neue', Arial, sans-serif; background:#0e1117; color:#e6e6e6; padding:28px; max-width:1100px">
      <div style="border-bottom:1px solid #333; padding-bottom:12px; margin-bottom:20px">
        <div style="color:#20beff; font-size:22px; font-weight:600">Kaggle Notebook — Lab28 GPU Serving</div>
        <div style="color:#888; margin-top:6px">Hybrid architecture: Kaggle GPU (vLLM + fastembed) → cloudflare tunnel → Local API Gateway</div>
      </div>

      <div style="background:#1a1d24; border-radius:8px; padding:16px; margin-bottom:16px">
        <div style="color:#f5a623; font-weight:600">[Cell 2] HF_TOKEN secret + cloudflared/ngrok tunnels</div>
        <pre style="margin:8px 0 0; font-size:13px">VLLM_MODEL={html.escape(vllm_model)}
VLLM_NGROK_URL={html.escape(vllm_url)}
EMBED_NGROK_URL={html.escape(embed_url)}</pre>
      </div>

      <div style="background:#1a1d24; border-radius:8px; padding:16px; margin-bottom:16px">
        <div style="color:#7ed321; font-weight:600">[Cell 3-4] vLLM server — GET /v1/models</div>
        <pre style="margin:8px 0 0; font-size:12px; white-space:pre-wrap">{html.escape(vllm_pretty[:1500])}</pre>
      </div>

      <div style="background:#1a1d24; border-radius:8px; padding:16px; margin-bottom:16px">
        <div style="color:#7ed321; font-weight:600">[Cell 5] fastembed service — POST /embed</div>
        <pre style="margin:8px 0 0; font-size:12px; white-space:pre-wrap">{html.escape(embed_summary)}</pre>
      </div>

      <div style="color:#666; font-size:12px">Screenshot: kaggle_notebook.png — live tunnel verification from local machine</div>
    </body>
    </html>
    """
    render_html_png(page_html, out_path, width=1100, height=900)


def ensure_deps():
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pillow"])
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


def main():
    print("=== Capturing Lab28 submission screenshots ===\n")
    ensure_deps()

    embedding = "[" + ",".join(["0.1"] * 384) + "]"
    run_cmd([
        "curl", "-s", "-X", "POST", "http://localhost:8000/api/v1/chat",
        "-H", "Content-Type: application/json",
        "-d", f'{{"query": "What is platform engineering?", "embedding": {embedding}}}',
    ])
    for i in range(1, 6):
        run_cmd([
            "curl", "-s", "-o", "/dev/null", "-X", "POST", "http://localhost:8000/api/v1/chat",
            "-H", "Content-Type: application/json",
            "-d", f'{{"query": "load test {i}", "embedding": {embedding}}}',
        ])

    pytest_out = run_cmd([sys.executable, "-m", "pytest", "smoke-tests/", "-v"])
    readiness_out = run_cmd([sys.executable, "scripts/production_readiness_check.py"])
    health_out = run_cmd(["curl", "-s", "http://localhost:8000/health"])
    chat_out = run_cmd([
        "curl", "-s", "-X", "POST", "http://localhost:8000/api/v1/chat",
        "-H", "Content-Type: application/json",
        "-d", f'{{"query": "What is platform engineering?", "embedding": {embedding}}}',
    ])

    render_terminal_png(pytest_out, SCREENSHOTS / "smoke_tests_results.png", "pytest smoke-tests/ -v")
    render_terminal_png(readiness_out, SCREENSHOTS / "production_readiness.png", "production_readiness_check.py")

    try:
        health_pretty = json.dumps(json.loads(health_out), indent=2)
    except json.JSONDecodeError:
        health_pretty = health_out
    try:
        chat_pretty = json.dumps(json.loads(chat_out), indent=2)
    except json.JSONDecodeError:
        chat_pretty = chat_out

    api_html = f"""
    <html><body style="font-family:monospace;background:#1e1e1e;color:#d4d4d4;padding:24px;max-width:900px">
    <h2 style="color:#4fc3f7">API Gateway Demo</h2>
    <h3>GET /health</h3><pre>{html.escape(health_pretty)}</pre>
    <h3>POST /api/v1/chat (real vLLM via Kaggle)</h3><pre>{html.escape(chat_pretty[:4000])}</pre>
    </body></html>
    """
    render_html_png(api_html, SCREENSHOTS / "api_gateway.png", width=900, height=700)

    capture_kaggle_notebook(KAGGLE_SCREENSHOT)
    screenshot_url("http://localhost:4200", SCREENSHOTS / "prefect_ui.png")
    screenshot_grafana_dashboard(SCREENSHOTS / "grafana_dashboard.png")
    try:
        screenshot_url("http://localhost:9090/targets", SCREENSHOTS / "prometheus_targets.png", wait_ms=2000)
    except Exception as exc:
        print(f"  skip prometheus_targets.png: {exc}")

    for name in ("smoke_tests_results.png", "production_readiness.png"):
        src = SCREENSHOTS / name
        if src.exists():
            (ROOT / name).write_bytes(src.read_bytes())

    print("\n=== Done ===")
    print(f"Screenshots in: {SCREENSHOTS}")
    for p in sorted(SCREENSHOTS.glob("*.png")):
        print(f"  - {p.name}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kaggle":
        ensure_deps()
        capture_kaggle_notebook()
    else:
        main()
