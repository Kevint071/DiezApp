from diezapp.features.google_drive.application.start_link import build_login_url


def test_build_login_url_includes_web_return_url():
    url = build_login_url(
        "https://api.example.com/login",
        "state-value",
        "ws://localhost:8550/settings",
    )

    assert (
        url == "https://api.example.com/login?app_state=state-value&"
        "web_return_url=http%3A%2F%2Flocalhost%3A8550%2Fcallback"
    )


def test_build_login_url_omits_invalid_web_return_url():
    url = build_login_url("https://api.example.com/login", "state-value", "app://local")

    assert url == "https://api.example.com/login?app_state=state-value"
