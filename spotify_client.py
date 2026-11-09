import time

import spotipy

MAX_RETRIES = 3
MAX_WAIT_S = 30


def _with_retry(fn, *args, **kwargs):
    """Call fn; on 429 honor Retry-After (bounded). Returns None on final failure."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except spotipy.SpotifyException as e:
            if e.http_status == 429 and attempt < MAX_RETRIES:
                retry_after = (e.headers or {}).get("Retry-After", 1)
                try:
                    wait = min(float(retry_after), MAX_WAIT_S)
                except (TypeError, ValueError):
                    wait = 1
                time.sleep(wait)
                continue
            return None
    return None


def get_recent_tracks(sp):
    """[(artist_id, artist_name)] for each of the last 50 plays; repeats preserved."""
    result = _with_retry(sp.current_user_recently_played, limit=50)
    out = []
    for item in (result or {}).get("items", []):
        artists = (item.get("track") or {}).get("artists") or []
        if artists and artists[0].get("id"):
            out.append((artists[0]["id"], artists[0]["name"]))
    return out
