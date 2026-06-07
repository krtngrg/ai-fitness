from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    First checks Authorization header.
    If no header exists, checks access_token cookie.
    """

    def authenticate(self, request):
        header = self.get_header(request)

        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            raw_token = request.COOKIES.get(settings.JWT_COOKIE_ACCESS)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return self.get_user(validated_token), validated_token