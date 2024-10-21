from fastapi import HTTPException, Request
from functools import wraps
from starlette.authentication import AuthCredentials, AuthenticationBackend, SimpleUser
from typing import Dict

# In-memory user database for demonstration purposes
AUTH_DB: Dict[str, str] = {
    "user1": "password123",
    "user2": "securepassword",
    "user3": "supersecurepassword",
}

SCOPES = {
    "authenticated": "Authenticated users",
    "admin": "Admin users",
    "superuser": "Superuser",
}

USER_SCOPES = {
    "user1": ["authenticated"],
    "user2": ["authenticated", "admin"],
    "user3": ["authenticated", "admin", "superuser"],
}


def authenticated(func: callable):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise HTTPException(status_code=401, detail="Authentication required")
        return await func(request, *args, **kwargs)

    return wrapper


def admin(func: callable):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise HTTPException(status_code=401, detail="Authentication required")
        if "admin" not in request.user.scopes:
            raise HTTPException(status_code=403, detail="Admin access required")
        return await func(request, *args, **kwargs)

    return wrapper


def has_scope(scope: str):
    def decorator(func: callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise HTTPException(status_code=401, detail="Authentication required")
            if scope not in request.auth.scopes:
                raise HTTPException(status_code=403, detail="Access denied")
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


class BasicAuthBackend(AuthenticationBackend):
    """Custom authentication backend that validates Basic auth credentials."""

    async def authenticate(self, request: Request):
        # Extract the 'Authorization' header from the request
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None  # No credentials provided

        try:
            # Basic authentication: "Basic <username>:<password>"
            auth_type, credentials = auth_header.split(" ", 1)
            if auth_type != "Basic":
                return None  # Unsupported auth type

            username, password = credentials.split(":")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Authorization format")

        # Validate credentials against the in-memory AUTH_DB
        if AUTH_DB.get(username) != password:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # If valid, return user object and auth credentials
        return AuthCredentials(USER_SCOPES[username]), SimpleUser(username)


# # Initialize FastAPI app
# app = FastAPI()
#
# # Add AuthenticationMiddleware to FastAPI with the custom backend
# app.add_middleware(AuthenticationMiddleware, backend=BasicAuthBackend())
#
# # Add SessionMiddleware with a secret key
# app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# @app.get("/")
# async def public():
#     """Public route."""
#     return {"message": "This route is accessible to everyone!"}
#
# @app.get("/private")
# async def private(request: Request):
#     """Private route that requires authentication."""
#     if not request.user.is_authenticated:
#         raise HTTPException(status_code=401, detail="Authentication required")
#
#     return {"message": f"Welcome, {request.user.display_name}!"}
#
# @app.get("/session")
# async def session_info(request: Request):
#     """Access session data."""
#     request.session["example"] = "This is session data"
#     return {"session_data": request.session}
