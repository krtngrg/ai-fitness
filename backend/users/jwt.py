from django.conf import settings


def set_auth_cookies(response, access_token, refresh_token=None):
    access_max_age = int(
        settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
    )

    refresh_max_age = int(
        settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
    )

    cookie_settings = {
        "httponly": True,
        "secure": settings.JWT_COOKIE_SECURE,
        "samesite": settings.JWT_COOKIE_SAMESITE,
        "path": "/",
    }

    response.set_cookie(
        key=settings.JWT_COOKIE_ACCESS,
        value=access_token,
        max_age=access_max_age,
        **cookie_settings,
    )

    if refresh_token:
        response.set_cookie(
            key=settings.JWT_COOKIE_REFRESH,
            value=refresh_token,
            max_age=refresh_max_age,
            **cookie_settings,
        )


def delete_auth_cookies(response):
    response.delete_cookie(
        key=settings.JWT_COOKIE_ACCESS,
        path="/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )

    response.delete_cookie(
        key=settings.JWT_COOKIE_REFRESH,
        path="/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )