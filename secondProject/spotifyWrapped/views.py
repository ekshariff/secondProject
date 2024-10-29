from datetime import timedelta
from django.utils import timezone

import requests
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required

from django.utils.text import normalize_newlines
from rest_framework.views import APIView
from . models import *
from rest_framework.response import Response
from .serializer import *
from rest_framework import viewsets
from .models import Artist
from .serializer import ArtistSerializer
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from .serializer import UserSerializer

from .models import SpotifyUser


# Create your views here.
from django.http import HttpResponse

SPOTIFY_CLIENT_ID = settings.SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = settings.SPOTIFY_CLIENT_SECRET
SPOTIFY_REDIRECT_URI = settings.SPOTIFY_REDIRECT_URI


# --- User Authentication API Views ---
@api_view(['POST'])
def register(request):
    """API endpoint for user registration."""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# User login
@api_view(['POST'])
def user_login(request):
    """API endpoint for user login."""
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)
    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key}, status=status.HTTP_200_OK)
    return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)


# --- Spotify Integration View ---
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unlink_spotify(request):
    # Access the SpotifyUser profile via the related name 'spotify_profile'
    spotify_profile = request.user.spotify_profile
    spotify_profile.access_token = None
    spotify_profile.refresh_token = None
    spotify_profile.save()
    return Response({"message": "Spotify account unlinked successfully"}, status=status.HTTP_200_OK)

@login_required
def spotify_login(request):
    """
    Redirects the user to Spotify's authorization URL for login.
    """
    scopes = 'user-library-read user-top-read'
    url = (
        'https://accounts.spotify.com/authorize'
        f'?client_id={SPOTIFY_CLIENT_ID}'
        f'&response_type=code'
        f'&redirect_uri={SPOTIFY_REDIRECT_URI}'
        f'&scope={scopes}'
    )
    return redirect(url)

def spotify_callback(request):
    """
    Handles the callback from Spotify after the user logs in.
    """
    # Process the request and get the authorization code
    code = request.GET.get('code')

    if code:
        # Exchange authorization code for access token
        token_url = 'https://accounts.spotify.com/api/token'
        response = requests.post(
            token_url,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': SPOTIFY_REDIRECT_URI,
                'client_id': SPOTIFY_CLIENT_ID,
                'client_secret': SPOTIFY_CLIENT_SECRET,
            },
        )

        response_data = response.json()
        access_token = response_data.get('access_token')
        refresh_token = response_data.get('refresh_token')
        expires_in = response_data.get('expires_in', 3600)
        token_expiry = timezone.now() + timedelta(seconds=expires_in)

        # Use the access token to fetch user profile information
        headers = {'Authorization': f'Bearer {access_token}'}
        user_profile_url = 'https://api.spotify.com/v1/me'
        user_data_response = requests.get(user_profile_url, headers=headers)
        user_data = user_data_response.json()

        # Extract user data
        spotify_id = user_data.get('id')
        display_name = user_data.get('display_name')
        external_url = user_data.get('external_urls').get('spotify')

        # Check if the user already exists in the database
        user, created = SpotifyUser.objects.get_or_create(spotify_id=spotify_id)
        user.display_name = display_name
        user.external_url = external_url
        user.access_token = access_token
        user.refresh_token = refresh_token
        user.token_expiry = token_expiry
        user.save()

        return JsonResponse({"message": "Spotify account linked successfully", "display_name": display_name}, status = 200)
    return JsonResponse({"error": "Spotify authentication failed"}, status = 400)


# --- Artist and React Data Views ---


class ArtistViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Artist model."""
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer

class ReactViewSet(viewsets.ModelViewSet):
    """ViewSet for managing React model."""
    queryset = React.objects.all()
    serializer_class = ReactSerializer

class ReactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        details = [{"name": detail.name, "detail": detail.detail} for detail in React.objects.all()]
        return Response(details)

    def post(self, request):
        serializer = ReactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- HTML Rendered Views (Optional if API-based) ---


def login_page(request):
    return render(request, 'login.html')

def profile_page(request):
    """Displays the user's profile with their Spotify Wrapped data."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('spotify_login')

    # Fetch the user from the database
    user = SpotifyUser.objects.get(id=user_id)

    context = {
        'user_name': user.display_name,
        'wraps': user.spotify_wraps  # Pass the user's Spotify wraps to the profile page
    }

    return render(request, 'profile.html', context)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    user = request.user
    user.delete()
    return Response({"message": "Account deleted successfully"}, status=status.HTTP_200_OK)

def refresh_spotify_token(refresh_token):
    """Function to refresh the Spotify access token when it expires."""
    token_url = 'https://accounts.spotify.com/api/token'
    response = requests.post(
        token_url,
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET,
        }
    )
    response_data = response.json()
    return response_data.get('access_token')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def spotify_data(request):
    """Displays user's Spotify data (e.g., user profile or top tracks) using the access token."""
    access_token = request.session.get('spotify_access_token')
    refresh_token = request.session.get('spotify_refresh_token')

    if not access_token:
        if refresh_token:
            access_token = refresh_spotify_token(refresh_token)
            request.user.spotifyuser.access_token = access_token
            request.user.spotifyuser.save()
        else:
            return Response({"error": "User needs to log into Spotify"}, status=status.HTTP_400_BAD_REQUEST)

    headers = {'Authorization': f'Bearer {access_token}'}
    user_profile_url = 'https://api.spotify.com/v1/me'
    user_data_response = requests.get(user_profile_url, headers=headers)

    if user_data_response.status_code != 200:
        return Response({'error': 'Failed to fetch data from Spotify'}, status=status.HTTP_400_BAD_REQUEST)

    user_data = user_data_response.json()
    return Response(user_data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout the user and clear the session."""
    request.auth.delete()
    return Response({"message": "User logged out successfully"}, status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_wrap(request, wrap_id):
    """Deletes a specific Spotify wrap by ID."""
    user = request.user.spotifyuser
    user.spotify_wraps = [wrap for wrap in user.spotify_wraps if wrap['id'] != wrap_id]
    user.save()
    return Response({"message": "Wrap deleted successfully"}, status=status.HTTP_200_OK)

def home_view(request):
    return render(request, 'home.html')
