"""
Configuration settings for the Fourth Circuit Court Opinions Email Digest.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Fourth Circuit Court URLs
FOURTH_CIRCUIT_BASE_URL = "https://www.ca4.uscourts.gov"
OPINIONS_URL = f"{FOURTH_CIRCUIT_BASE_URL}/opinions/recent-opinions/published-only"

# Data storage
DATA_DIR = BASE_DIR / "data"
REVIEWED_OPINIONS_FILE = DATA_DIR / "reviewed_opinions.json"
OPINIONS_CACHE_DIR = DATA_DIR / "opinion_pdfs"

# Anthropic API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# Email settings
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
# Support multiple recipients (comma-separated)
_recipient_env = os.getenv("RECIPIENT_EMAIL", "mswigley@wardandsmith.com")
RECIPIENT_EMAILS = [email.strip() for email in _recipient_env.split(",")]

# Timezone
TIMEZONE = os.getenv("TIMEZONE", "US/Eastern")

# Reviewed opinions tracking (comma-separated unique IDs for persistence in cloud environments)
# Format: "case1_20260101,case2_20260102,..."
_reviewed_env = os.getenv("REVIEWED_OPINION_IDS", "")
REVIEWED_OPINION_IDS = set(id.strip() for id in _reviewed_env.split(",") if id.strip())

# Schedule settings
SCHEDULE_DAY = "friday"
SCHEDULE_TIME = "17:00"  # 5:00 PM

# Request settings
REQUEST_TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def ensure_data_dirs():
    """Create data directories if they don't exist."""
    DATA_DIR.mkdir(exist_ok=True)
    OPINIONS_CACHE_DIR.mkdir(exist_ok=True)
