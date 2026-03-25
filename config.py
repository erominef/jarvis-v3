# config.py — Configuration and environment.
#
# All values loaded from .env via python-dotenv.
# Required vars must be set — missing values raise KeyError at startup.
# Optional vars fall back to sensible defaults.
#
# Xeon service URLs default to the tool server's internal address.
# Set these explicitly in .env if your network layout differs.

import os
from dotenv import load_dotenv

load_dotenv()

# LLM
OLLAMA_API_KEY: str = os.environ["OLLAMA_API_KEY"]
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/api")
MODEL: str = os.getenv("MODEL", "minimax-m2.7:cloud")
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))
MAX_TOOL_ROUNDS: int = int(os.getenv("MAX_TOOL_ROUNDS", "10"))

# PC services
SEARXNG_URL: str = os.environ["SEARXNG_URL"]
PLAYWRIGHT_URL: str = os.getenv("PLAYWRIGHT_URL", "http://YOUR_XEON_IP:8082")

# Telegram
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_OWNER_ID: int = int(os.environ["TELEGRAM_OWNER_ID"])

# Xeon services
MEMORY_URL: str = os.getenv("MEMORY_URL", "http://YOUR_XEON_IP:8083")
CODE_RUNNER_URL: str = os.getenv("CODE_RUNNER_URL", "http://YOUR_XEON_IP:8084")
EMAIL_URL: str = os.getenv("EMAIL_URL", "http://YOUR_XEON_IP:8085")
N8N_URL: str = os.getenv("N8N_URL", "http://YOUR_XEON_IP:5678")
N8N_API_KEY: str = os.getenv("N8N_API_KEY", "")
COMFYUI_URL: str = os.getenv("COMFYUI_URL", "http://YOUR_XEON_IP:8188")
GITEA_URL: str = os.getenv("GITEA_URL", "http://YOUR_XEON_IP:3030")
GITEA_TOKEN: str = os.getenv("GITEA_TOKEN", "")

# Optional integrations
DOCUSEAL_URL: str = os.getenv("DOCUSEAL_URL", "http://localhost:3000")
DOCUSEAL_API_KEY: str = os.getenv("DOCUSEAL_API_KEY", "")
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
