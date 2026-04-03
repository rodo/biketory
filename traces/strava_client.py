import logging
from datetime import UTC

import requests
from django.conf import settings
from django.utils import timezone as dj_timezone

logger = logging.getLogger(__name__)

STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"


class StravaNotConnectedError(Exception):
    pass


class StravaAPIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _get_social_token(user):
    """Retrieve the allauth SocialToken for the strava provider."""
    from allauth.socialaccount.models import SocialAccount

    account = SocialAccount.objects.filter(user=user, provider="strava").first()
    if account is None:
        raise StravaNotConnectedError("No Strava account linked.")

    token = account.socialtoken_set.first()
    if token is None:
        raise StravaNotConnectedError("No Strava token found.")
    return token


def _refresh_if_needed(token):
    """Refresh the Strava token if it has expired, persist the new token."""
    if token.expires_at and token.expires_at > dj_timezone.now():
        return token

    resp = requests.post(STRAVA_TOKEN_URL, data={
        "client_id": settings.STRAVA_CLIENT_ID,
        "client_secret": settings.STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": token.token_secret,
    }, timeout=15)

    if resp.status_code != 200:
        raise StravaAPIError("Failed to refresh Strava token.", status_code=resp.status_code)

    data = resp.json()
    token.token = data["access_token"]
    token.token_secret = data["refresh_token"]
    from datetime import datetime
    token.expires_at = dj_timezone.make_aware(
        datetime.fromtimestamp(data["expires_at"], tz=UTC).replace(tzinfo=None)
    )
    token.save()
    return token


def fetch_recent_activities(user, per_page=30):
    """Fetch the user's recent Strava activities."""
    token = _get_social_token(user)
    token = _refresh_if_needed(token)

    resp = requests.get(
        f"{STRAVA_API_BASE}/athlete/activities",
        headers={"Authorization": f"Bearer {token.token}"},
        params={"per_page": per_page},
        timeout=15,
    )

    if resp.status_code == 429:
        raise StravaAPIError("Strava rate limit reached. Please try again later.", status_code=429)
    if resp.status_code != 200:
        raise StravaAPIError(f"Strava API error ({resp.status_code}).", status_code=resp.status_code)

    return resp.json()


def fetch_activity_streams(user, activity_id):
    """Fetch GPS streams (latlng, time, altitude) for a Strava activity."""
    token = _get_social_token(user)
    token = _refresh_if_needed(token)

    resp = requests.get(
        f"{STRAVA_API_BASE}/activities/{activity_id}/streams",
        headers={"Authorization": f"Bearer {token.token}"},
        params={"keys": "latlng,time,altitude", "key_by_type": "true"},
        timeout=15,
    )

    if resp.status_code == 429:
        raise StravaAPIError("Strava rate limit reached. Please try again later.", status_code=429)
    if resp.status_code != 200:
        raise StravaAPIError(f"Strava API error ({resp.status_code}).", status_code=resp.status_code)

    return resp.json()
