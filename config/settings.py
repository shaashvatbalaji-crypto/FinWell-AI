import os
from pathlib import Path
from dotenv import load_dotenv

# Inner project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Outer folder, where .env is located
ENV_FILE = PROJECT_ROOT.parent / ".env"

load_dotenv(ENV_FILE)

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "lion")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "finwell_ai")