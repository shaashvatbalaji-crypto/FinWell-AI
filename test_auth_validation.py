from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

tests = [
    {
        "username": "ab",
        "email": "valid@example.com",
        "password": "StrongPassword123!"
    },
    {
        "username": "testuser",
        "email": "invalid-email",
        "password": "StrongPassword123!"
    },
    {
        "username": "testuser",
        "email": "valid@example.com",
        "password": "short"
    }
]

for data in tests:
    response = client.post("/api/auth/register", json=data)
    print("Status:", response.status_code)