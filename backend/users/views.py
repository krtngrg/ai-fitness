from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from django.conf import settings

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
)
from .jwt import set_auth_cookies, delete_auth_cookies


RegisterResponseSerializer = inline_serializer(
    name="RegisterResponseSerializer",
    fields={
        "message": serializers.CharField(),
        "email": serializers.EmailField(),
        "username": serializers.CharField(),
    },
)

LoginResponseSerializer = inline_serializer(
    name="LoginResponseSerializer",
    fields={
        "message": serializers.CharField(),
        "email": serializers.EmailField(),
        "username": serializers.CharField(),
        "access": serializers.CharField(),
        "refresh": serializers.CharField(),
    },
)

MessageResponseSerializer = inline_serializer(
    name="MessageResponseSerializer",
    fields={
        "message": serializers.CharField(),
    },
)

ErrorResponseSerializer = inline_serializer(
    name="ErrorResponseSerializer",
    fields={
        "detail": serializers.CharField(),
    },
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Register user",
        description="Create a new user account. This does not return tokens. User must login after registration.",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=RegisterResponseSerializer,
                description="User registered successfully.",
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Validation error.",
            ),
        },
        examples=[
            OpenApiExample(
                "Register Example",
                value={
                    "name": "James",
                    "email": "james@example.com",
                    "password": "StrongPass123",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "message": "User registered successfully",
                "email": user.email,
                "username": user.name,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login user",
        description="Login with email and password. Access and refresh tokens are returned. Both are also stored in HttpOnly cookies.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=LoginResponseSerializer,
                description="Login successful.",
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Invalid email or password.",
            ),
        },
        examples=[
            OpenApiExample(
                "Login Example",
                value={
                    "email": "james@example.com",
                    "password": "StrongPass123",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response(
            {
                "message": "Login successful",
                "email": user.email,
                "username": user.name,
                "access": access_token,
                "refresh": refresh_token,
            },
            status=status.HTTP_200_OK,
        )

        set_auth_cookies(
            response=response,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        return response


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Refresh access token",
        description="Refresh access token using the refresh_token stored in HttpOnly cookie.",
        request=None,
        responses={
            200: OpenApiResponse(
                response=MessageResponseSerializer,
                description="Token refreshed successfully.",
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Refresh token not found or invalid.",
            ),
        },
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_COOKIE_REFRESH)

        if not refresh_token:
            return Response(
                {"detail": "Refresh token not found"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = TokenRefreshSerializer(
            data={"refresh": refresh_token}
        )

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as error:
            raise InvalidToken(error.args[0])

        access_token = serializer.validated_data["access"]

        new_refresh_token = serializer.validated_data.get(
            "refresh",
            refresh_token,
        )

        response = Response(
            {
                "message": "Token refreshed",
                "access": access_token,
            },
            status=status.HTTP_200_OK,
        )

        set_auth_cookies(
            response=response,
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Logout user",
        description="Blacklist refresh token and delete auth cookies.",
        request=None,
        responses={
            200: OpenApiResponse(
                response=MessageResponseSerializer,
                description="Logout successful.",
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication required.",
            ),
        },
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(settings.JWT_COOKIE_REFRESH)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response = Response(
            {"message": "Logout successful"},
            status=status.HTTP_200_OK,
        )

        delete_auth_cookies(response)

        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Get current logged-in user",
        description="Returns the authenticated user's details.",
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description="Current user details.",
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Authentication required.",
            ),
        },
    )
    def get(self, request):
        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )