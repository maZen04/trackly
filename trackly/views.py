from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.views import APIView
from .serializers import UserSerializer
from .common.throttles import *
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken


class RegisterView(APIView):
    throttle_classes = [RegisterThrottle]

    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED
        )
        



class LoginView(APIView):
    throttle_classes = [LoginThrottle]

    def post(self, request, *arg, **kwargs):
        serializer = TokenObtainPairSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {
                    "message": "Logged in successfully.",
                    **serializer.validated_data
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                "message": "Invalid email or password."
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
        

class RefreshTokenView(APIView):
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            raise InvalidToken("Refresh token is invalid or expired.")
        return Response(
            {
                "message":"Token refreshed successfully.",
                **serializer.validated_data
            },
            status=200
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"message":"logged out Successfully."},
                status=200
            )
        
        except TokenError:
            raise ValidationError({
                "refresh": ["Refresh token is required."]
            })