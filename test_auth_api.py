from fastapi.testclient import TestClient
from api.main import app
from api.routes.auth import create_access_token

client = TestClient(app)

# Simulate another authenticated user
token = create_access_token(999)

headers = {
    "Authorization": f"Bearer {token}"
}

response = client.get(
    "/api/documents/12",
    headers=headers
)

print("Other user's document access:", response.status_code)
print("Response:", response.json())