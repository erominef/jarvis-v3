# tools/services.py — External service integrations.
#
# All functions synchronous (sync httpx).
# Missing env var → returns "not configured" immediately.
# Connection failure → returns "not running" immediately.
#
# http_request blocks RFC1918 + loopback addresses (checked in Python before
# any connection is opened — covers all redirect hops too).
#
# Tools: searxng_search, playwright_scrape, n8n_trigger, docuseal_send,
#        comfyui_generate, stripe_op, http_request


def searxng_search(query: str, categories: str = "general", limit: int = 10) -> str:
    """
    Search via self-hosted SearXNG instance.
    Env: SEARXNG_URL
    Returns up to `limit` results with title, URL, and snippet.
    Preferred over web_search for general queries.
    """
    # Implementation omitted.
    raise NotImplementedError


def playwright_scrape(url: str, action: str = "content") -> str:
    """
    Scrape a URL via headless Chromium (Playwright).
    action: "content" (default) | "screenshot"
    Env: PLAYWRIGHT_URL
    Use for JS-rendered pages that web_fetch can't read.
    """
    # Implementation omitted.
    raise NotImplementedError


def n8n_trigger(workflow_name: str, data: dict = None) -> str:
    """
    Trigger an n8n workflow by name. Searches for a matching workflow,
    then fires via webhook node if present, otherwise via the run API.
    Env: N8N_URL, N8N_API_KEY
    """
    # Implementation omitted.
    raise NotImplementedError


def docuseal_send(filename: str, signer_email: str, signer_name: str, document_title: str = "") -> str:
    """
    Upload a workspace/ document to DocuSeal and send a signing request.
    filename: path relative to workspace/ (.pdf or .docx)
    Returns a signing link on success.
    Env: DOCUSEAL_URL, DOCUSEAL_API_KEY
    """
    # Implementation omitted.
    raise NotImplementedError


def comfyui_generate(prompt: str, filename: str, negative_prompt: str = "", steps: int = 20, width: int = 512, height: int = 512) -> str:
    """
    Generate an image via ComfyUI. Polls /history/{prompt_id} until complete.
    Saves output to workspace/<filename>.
    Env: COMFYUI_URL
    Timeout: 300s.
    """
    # Implementation omitted.
    raise NotImplementedError


def stripe_op(action: str, params: dict = None) -> str:
    """
    Stripe operations.
    action: create_payment_link | list_payments | check_revenue
    Env: STRIPE_SECRET_KEY
    Live key warning is shown if sk_live_ prefix detected.
    """
    # Implementation omitted.
    raise NotImplementedError


def http_request(method: str, url: str, headers: dict = None, json_body: dict = None) -> str:
    """
    Generic HTTP GET or POST.
    Blocks RFC1918 ranges (10.x, 172.16-31.x, 192.168.x), loopback,
    link-local, and .local hostnames before opening any connection.
    method: GET | POST only.
    """
    # Implementation omitted.
    raise NotImplementedError
