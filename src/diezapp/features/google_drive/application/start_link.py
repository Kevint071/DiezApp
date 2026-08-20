from urllib.parse import urlencode, urlsplit


def build_login_url(
    login_endpoint: str,
    app_state: str,
    page_url: str | None = None,
    account_id: str | None = None,
) -> str:
    params = {"app_state": app_state}
    if account_id:
        params["account_id"] = account_id
    if page_url:
        current_url = urlsplit(page_url)
        web_scheme = {"ws": "http", "wss": "https"}.get(current_url.scheme)
        if web_scheme and current_url.netloc:
            params["web_return_url"] = f"{web_scheme}://{current_url.netloc}/callback"
    return f"{login_endpoint}?{urlencode(params)}"
