# Authentication
import httpx
from src.exceptions import handle_exceptions
from src.configure import LOG_CONFIG, LOGGER


@handle_exceptions("Login failed", True)
async def login(username, password, server_path):
    """
    Logs into the application using provided credentials.
    Returns:
        httpx.Response: The HTTP response object after successful login.
        dict: Cookies obtained from the login response.
    Raises:
        HTTPError: If the login request fails.
    """
    url = f"{server_path}{LOG_CONFIG['LOGIN_URL']}"
    data = {"username": username, "password": password}
    async with httpx.AsyncClient(timeout=httpx.Timeout(10, read=60)) as client:
        response = await client.post(url, json=data, headers=LOG_CONFIG["LOGIN_JSON_HEADERS"])
        response.raise_for_status()
        return response, response.cookies


def handle_cookies(response_cookies):
    """Extracts and formats required cookies from the HTTPX response.
    Returns: Formatted cookies string, access token, csrf token
    """
    access_token_cookie = response_cookies.get("access_token_cookie")
    csrf_token = response_cookies.get("csrf_access_token")

    if not all([access_token_cookie, csrf_token]):
        LOGGER.error("Error: Missing required cookies")
        raise ValueError("Missing required cookies")

    cookies_str = f"access_token_cookie={access_token_cookie}; csrf_access_token={csrf_token}"
    return cookies_str, access_token_cookie, csrf_token
