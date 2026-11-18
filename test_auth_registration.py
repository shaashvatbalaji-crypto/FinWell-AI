
from fastapi.testclient import TestClient
from api.main import app
from mysql_pipeline.user_storage import get_user_by_email

client = TestClient(app)

# Test account credentials
username = "finwell_auth_test"
email = "finwell_auth_test@example.com"
password = "FinWell_Test@2026!"

# 1. Register user
registration = client.post(
    "/api/auth/register",
    json={
        "username": username,
        "email": email,
        "password": password,
    },
)

print("Registration status:", registration.status_code)
print("Registration response:", registration.json())

if registration.status_code != 201:
    raise RuntimeError("Registration failed. Stop testing.")

# 2. Verify password hash in MySQL
user = get_user_by_email(email)

if not user or not user.get("password_hash", "").startswith("$argon2"):
    raise RuntimeError("Argon2id password hash verification failed.")

print("Argon2id storage: PASS")

# 3. Correct password login
login = client.post(
    "/api/auth/login",
    json={
        "email": email,
        "password": password,
    },
)

print("Correct login status:", login.status_code)

if login.status_code != 200:
    raise RuntimeError("Correct password login failed.")

token = login.json()["access_token"]
print("JWT issued: PASS")

# 4. Incorrect password login
wrong_login = client.post(
    "/api/auth/login",
    json={
        "email": email,
        "password": "IncorrectPassword@123",
    },
)

print("Incorrect login status:", wrong_login.status_code)

# 5. Access protected API using returned JWT
response = client.get(
    "/api/documents",
    headers={"Authorization": f"Bearer {token}"},
)

print("Authenticated documents status:", response.status_code)

print("\nAuthentication integration test completed.")
