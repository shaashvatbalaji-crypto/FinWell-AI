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

# JWT Authentication Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

# Validate JWT configuration
if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
    raise ValueError("JWT_SECRET_KEY is missing or too short.")

if JWT_ALGORITHM != "HS256":
    raise ValueError("Unsupported JWT algorithm.")