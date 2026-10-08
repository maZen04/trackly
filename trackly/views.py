from django.shortcuts import render
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from .serializers import UserSerializer, MonitorSerializer, SnapshotSerializer
from .common.throttles import *
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Monitor, Snapshot
from .services.scraper import Scraper
from .services.hash import generate_hash


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

    
class MonitorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        scraper = Scraper()
        serializer = MonitorSerializer(data=request.data)

        if serializer.is_valid():
            url = serializer.validated_data["url"]
            if not Monitor.objects.filter(
                user=request.user, 
                url=url
            ).exists():
                result = scraper.validate_url(url)
                print(result)
                if result['valid']:
                    content = result["content"]
                    content_hash = generate_hash(content)

                    monitor = serializer.save(
                        user=request.user,
                        last_hash=content_hash
                    )

                    Snapshot.objects.create(
                        monitor=monitor,
                        content=content,
                        content_hash=content_hash
                    )

                    return Response(
                        MonitorSerializer(monitor).data,
                        status=status.HTTP_201_CREATED
                    )
                return Response(
                    {"message":"This url is invalid to track please try another url."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {"message":"This url is already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def get(self, request):
        monitors = Monitor.objects.filter(user=request.user).order_by('-created_at')
        serializer = MonitorSerializer(monitors, many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class MonitorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        monitor = get_object_or_404(
                    Monitor,
                    user=request.user,
                    pk=pk
                )
        serializer = MonitorSerializer(monitor)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
    
    def patch(self, request, pk):
        monitor = get_object_or_404(
            Monitor,
            user=request.user,
            pk=pk
        )

        scraper = Scraper()

        serializer = MonitorSerializer(
            monitor,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            url = serializer.validated_data.get("url")

            if url:
                result = scraper.validate_url(url)

                if not result["valid"]:
                    return Response(
                        {
                            "message": "This url is invalid to track. Please try another url."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                content = result["content"]
                content_hash = generate_hash(content)

                monitor = serializer.save(
                    last_hash=content_hash
                )

                Snapshot.objects.create(
                    monitor=monitor,
                    content=content,
                    content_hash=content_hash
                )

            else:
                monitor = serializer.save()

            return Response(
                MonitorSerializer(monitor).data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        monitor = get_object_or_404(
                    Monitor,
                    user=request.user,
                    pk=pk
                )
                
        monitor.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class SnapshotView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        monitor = get_object_or_404(
            Monitor,
            pk=pk,
            user=request.user
        )

        snapshots = monitor.snapshots.all().order_by('-created_at')
        serializer = SnapshotSerializer(snapshots, many=True)

        return Response(serializer.data)