# tools/services.py — External service integrations.
#
# All functions synchronous (sync httpx).
# Missing env var → returns "not configured" immediately.
# Connection failure → returns "not running" immediately.
#
# Tools: searxng_search, playwright_scrape, n8n_trigger, docuseal_send,
#        comfyui_generate, stripe_op, http_request

import base64
import ipaddress
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

_WORKSPACE = Path(__file__).parent.parent / "workspace"
_TIMEOUT = 30.0
_COMFYUI_POLL_INTERVAL = 5
_COMFYUI_MAX_WAIT = 300

# RFC1918 + loopback ranges to block for http_request
_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_private_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in _PRIVATE_NETS)
    except ValueError:
        # Not an IP — check hostname directly
        lower = (urlparse(url).hostname or "").lower()
        return lower in ("localhost", "local") or lower.endswith(".local")


# ── SearXNG ───────────────────────────────────────────────────────────────────

def searxng_search(query: str, categories: str = "general", limit: int = 10) -> str:
    base_url = os.getenv("SEARXNG_URL", "http://localhost:8888").rstrip("/")
    try:
        r = httpx.get(
            f"{base_url}/search",
            params={"q": query, "categories": categories, "format": "json", "pageno": 1},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
    except httpx.ConnectError:
        return f"Service unavailable: SearXNG not running at {base_url}"
    except Exception as e:
        return f"SearXNG error: {e}"

    if not results:
        return f"No results found for: {query}"

    lines = []
    for item in results[:limit]:
        title = item.get("title", "(no title)").strip()
        url = item.get("url", "").strip()
        snippet = item.get("content", "").strip()
        lines.append(f"• {title}\n  {url}")
        if snippet:
            lines.append(f"  {snippet[:200]}")
    return "\n\n".join(lines)


# ── Playwright scraper ────────────────────────────────────────────────────────

def playwright_scrape(url: str, action: str = "content") -> str:
    sidecar_url = os.getenv("PLAYWRIGHT_URL", "http://localhost:8889").rstrip("/")
    try:
        r = httpx.post(
            f"{sidecar_url}/scrape",
            json={"url": url, "action": action},
            timeout=60.0,
        )
        r.raise_for_status()
        data = r.json()
    except httpx.ConnectError:
        return f"Service unavailable: Playwright not running at {sidecar_url}"
    except Exception as e:
        return f"Playwright error: {e}"

    if action == "screenshot":
        path = data.get("path", "")
        return f"Screenshot saved to: {path}" if path else "Screenshot failed."

    content = data.get("content", "")
    if not content:
        return "(empty page)"
    if len(content) > 4000:
        content = content[:4000] + "\n[truncated]"
    return content


# ── N8N ───────────────────────────────────────────────────────────────────────

def n8n_trigger(workflow_name: str, data: dict = None) -> str:
    n8n_url = os.getenv("N8N_URL", "http://100.101.127.60:5678").rstrip("/")
    api_key = os.getenv("N8N_API_KEY", "")
    if not api_key:
        return "Service not configured — set N8N_API_KEY in .env"

    headers = {"X-N8N-API-KEY": api_key, "Content-Type": "application/json"}

    try:
        r = httpx.get(f"{n8n_url}/api/v1/workflows", headers=headers, timeout=_TIMEOUT)
        r.raise_for_status()
        workflows = r.json().get("data", [])
    except httpx.ConnectError:
        return f"Service unavailable: n8n not running at {n8n_url}"
    except Exception as e:
        return f"n8n list error: {e}"

    match = next((w for w in workflows if workflow_name.lower() in w.get("name", "").lower()), None)
    if not match:
        names = [w.get("name", "") for w in workflows]
        return f"No workflow matching '{workflow_name}'. Available: {names}"

    nodes = match.get("nodes") or []
    webhook_node = next((n for n in nodes if n.get("type") == "n8n-nodes-base.webhook"), None)

    if webhook_node:
        path = webhook_node.get("parameters", {}).get("path", "")
        webhook_url = f"{n8n_url}/webhook/{path}"
        try:
            r = httpx.post(webhook_url, json=data or {}, timeout=_TIMEOUT)
            r.raise_for_status()
            return f"Workflow '{match['name']}' triggered. Response: {r.text[:500]}"
        except Exception as e:
            return f"n8n webhook error: {e}"
    else:
        wf_id = match.get("id")
        try:
            r = httpx.post(
                f"{n8n_url}/api/v1/workflows/{wf_id}/run",
                json={"startNodes": [], "destinationNode": ""},
                headers=headers,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            exec_id = r.json().get("data", {}).get("executionId", "unknown")
            return f"Workflow '{match['name']}' triggered via API. Execution ID: {exec_id}"
        except Exception as e:
            return f"n8n trigger error: {e}"


# ── DocuSeal ──────────────────────────────────────────────────────────────────

def docuseal_send(filename: str, signer_email: str, signer_name: str, document_title: str = "") -> str:
    ds_url = os.getenv("DOCUSEAL_URL", "http://localhost:3000").rstrip("/")
    api_key = os.getenv("DOCUSEAL_API_KEY", "")
    if not api_key:
        return "Service not configured — set DOCUSEAL_API_KEY in .env"

    # Strip accidental workspace/ prefix
    clean_filename = filename.strip()
    if clean_filename.startswith("workspace/"):
        clean_filename = clean_filename[len("workspace/"):]

    file_path = _WORKSPACE / clean_filename
    if not file_path.exists():
        return f"File not found: workspace/{clean_filename}"

    suffix = file_path.suffix.lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    mime = mime_map.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(file_path.read_bytes()).decode()
    title = document_title or file_path.stem
    headers = {"X-Auth-Token": api_key, "Content-Type": "application/json"}

    try:
        r = httpx.post(
            f"{ds_url}/api/templates",
            json={"name": title, "documents": [{"name": filename, "file": f"data:{mime};base64,{encoded}"}]},
            headers=headers,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        template = r.json()
    except httpx.ConnectError:
        return f"Service unavailable: DocuSeal not running at {ds_url}"
    except Exception as e:
        return f"DocuSeal upload error: {e}"

    template_id = template.get("id") or (template[0].get("id") if isinstance(template, list) else None)
    if not template_id:
        return f"DocuSeal error: could not get template ID from response."

    try:
        r = httpx.post(
            f"{ds_url}/api/submissions",
            json={
                "template_id": template_id,
                "send_email": True,
                "submitters": [{"role": "First Party", "email": signer_email, "name": signer_name}],
            },
            headers=headers,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        submission = r.json()
    except Exception as e:
        return f"DocuSeal submission error: {e}"

    submitters = submission if isinstance(submission, list) else submission.get("submitters", [])
    signing_link = ""
    if submitters:
        slug = submitters[0].get("slug", "")
        if slug:
            signing_link = f"{ds_url}/s/{slug}"

    return (
        f"Document '{title}' sent to {signer_name} <{signer_email}> for signing.\n"
        f"Signing link: {signing_link or '(check DocuSeal dashboard)'}"
    )


# ── ComfyUI image generation ──────────────────────────────────────────────────

def _build_comfyui_workflow(prompt: str, negative_prompt: str, steps: int, width: int, height: int, filename: str) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt or "ugly, blurry, low quality", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0],
                "seed": int(time.time()) % 2**32, "steps": steps, "cfg": 7.5,
                "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
            },
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": Path(filename).stem}},
    }


def comfyui_generate(prompt: str, filename: str, negative_prompt: str = "", steps: int = 20, width: int = 512, height: int = 512) -> str:
    comfy_url = os.getenv("COMFYUI_URL", "http://100.101.127.60:8188").rstrip("/")
    workflow = _build_comfyui_workflow(prompt, negative_prompt, steps, width, height, filename)

    try:
        r = httpx.post(f"{comfy_url}/prompt", json={"prompt": workflow}, timeout=_TIMEOUT)
        r.raise_for_status()
        prompt_id = r.json().get("prompt_id")
    except httpx.ConnectError:
        return f"Service unavailable: ComfyUI not running at {comfy_url}"
    except Exception as e:
        return f"ComfyUI queue error: {e}"

    if not prompt_id:
        return "ComfyUI error: no prompt_id in response."

    deadline = time.time() + _COMFYUI_MAX_WAIT
    output_images = []

    while time.time() < deadline:
        time.sleep(_COMFYUI_POLL_INTERVAL)
        try:
            r = httpx.get(f"{comfy_url}/history/{prompt_id}", timeout=_TIMEOUT)
            r.raise_for_status()
            history = r.json()
        except Exception as e:
            return f"ComfyUI poll error: {e}"

        if prompt_id not in history:
            continue
        result = history[prompt_id]
        status = result.get("status", {})
        if status.get("completed"):
            for node_id, node_out in result.get("outputs", {}).items():
                output_images.extend(node_out.get("images", []))
            break
        if status.get("status_str") == "error":
            return f"ComfyUI generation failed: {status.get('messages', '')}"
    else:
        return f"ComfyUI timeout: generation exceeded {_COMFYUI_MAX_WAIT}s."

    if not output_images:
        return "ComfyUI: generation completed but no images in output."

    img_info = output_images[0]
    params = {"filename": img_info.get("filename", ""), "type": img_info.get("type", "output")}
    if img_info.get("subfolder"):
        params["subfolder"] = img_info["subfolder"]

    try:
        r = httpx.get(f"{comfy_url}/view", params=params, timeout=60.0)
        r.raise_for_status()
        img_bytes = r.content
    except Exception as e:
        return f"ComfyUI download error: {e}"

    # Strip workspace/ prefix from filename if present
    clean_filename = filename.strip()
    if clean_filename.startswith("workspace/"):
        clean_filename = clean_filename[len("workspace/"):]
    out_path = _WORKSPACE / clean_filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(img_bytes)
    return f"Image saved to workspace/{clean_filename} ({len(img_bytes) // 1024} KB)"


# ── Stripe ─────────────────────────────────────────────────────────────────────

def stripe_op(action: str, params: dict = None) -> str:
    secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not secret_key:
        return "Service not configured — set STRIPE_SECRET_KEY in .env"

    try:
        import stripe  # type: ignore
    except ImportError:
        return "stripe not installed — add 'stripe' to requirements.txt."

    stripe.api_key = secret_key
    p = params or {}

    if action == "create_payment_link":
        if not secret_key.startswith("sk_"):
            return "Stripe error: STRIPE_SECRET_KEY does not look like a valid secret key."
        live_warning = "WARNING: using live Stripe key — real charges will occur.\n" if secret_key.startswith("sk_live") else ""
        product_name = p.get("product_name", "")
        amount_cents = p.get("amount_cents")
        currency = p.get("currency", "usd").lower()
        quantity = p.get("quantity", 1)
        if not product_name:
            return "Missing required param: product_name"
        if not amount_cents:
            return "Missing required param: amount_cents"
        try:
            product = stripe.Product.create(name=product_name)
            price = stripe.Price.create(product=product.id, unit_amount=int(amount_cents), currency=currency)
            link = stripe.PaymentLink.create(line_items=[{"price": price.id, "quantity": quantity}])
            return f"{live_warning}Payment link for '{product_name}' ({currency.upper()} {int(amount_cents)/100:.2f}):\n{link.url}"
        except stripe.StripeError as e:
            return f"Stripe error: {e.user_message or str(e)}"

    elif action == "list_payments":
        limit = int(p.get("limit", 10))
        try:
            intents = stripe.PaymentIntent.list(limit=limit)
            if not intents.data:
                return "No payment intents found."
            lines = []
            for pi in intents.data:
                amount = pi.amount / 100
                created = time.strftime("%Y-%m-%d", time.localtime(pi.created))
                lines.append(f"• {created} | {pi.currency.upper()} {amount:.2f} | {pi.status}")
            return "\n".join(lines)
        except stripe.StripeError as e:
            return f"Stripe error: {e.user_message or str(e)}"

    elif action == "check_revenue":
        import datetime
        thirty_days_ago = int((datetime.datetime.now() - datetime.timedelta(days=30)).timestamp())
        try:
            charges = stripe.Charge.list(created={"gte": thirty_days_ago}, limit=100)
            successful = [c for c in charges.data if c.status == "succeeded"]
            by_currency: dict = {}
            for c in successful:
                cur = c.currency.upper()
                by_currency[cur] = by_currency.get(cur, 0.0) + c.amount / 100
            if not by_currency:
                return "No successful charges in the last 30 days."
            lines = [f"  {cur}: {amt:.2f}" for cur, amt in sorted(by_currency.items())]
            return f"Revenue last 30 days ({len(successful)} charges):\n" + "\n".join(lines)
        except stripe.StripeError as e:
            return f"Stripe error: {e.user_message or str(e)}"

    else:
        return f"Unknown stripe action '{action}'. Valid: create_payment_link | list_payments | check_revenue"


# ── Generic HTTP request ──────────────────────────────────────────────────────

def http_request(method: str, url: str, headers: dict = None, json_body: dict = None) -> str:
    method = method.upper()
    if method not in ("GET", "POST"):
        return "Only GET and POST methods are allowed."

    if _is_private_url(url):
        return "Rejected: requests to private/internal IP addresses are not allowed."

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "Rejected: only http/https URLs are allowed."

    try:
        kwargs: dict = {"timeout": 15.0, "follow_redirects": True}
        if headers:
            kwargs["headers"] = headers
        if json_body and method == "POST":
            kwargs["json"] = json_body

        if method == "GET":
            r = httpx.get(url, **kwargs)
        else:
            r = httpx.post(url, **kwargs)

        r.raise_for_status()
        content = r.text[:3000]
        if len(r.text) > 3000:
            content += "\n[truncated]"
        return f"Status: {r.status_code}\n\n{content}"
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"Request failed: {e}"
