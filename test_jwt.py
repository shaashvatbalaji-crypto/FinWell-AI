from fastapi.security import HTTPAuthorizationCredentials
from fastapi import HTTPException

from api.routes.auth import create_access_token
from api.auth_dependencies import get_current_user

# Valid token test
token = create_access_token(1)
credentials = HTTPAuthorizationCredentials(
    scheme="Bearer",
    credentials=token
)

print("Valid token user ID:", get_current_user(credentials))

# Invalid token test
bad = HTTPAuthorizationCredentials(
    scheme="Bearer",
    credentials="invalid.token.value"
)

try:
    get_current_user(bad)
except HTTPException as error:
    print("Invalid token status:", error.status_code)