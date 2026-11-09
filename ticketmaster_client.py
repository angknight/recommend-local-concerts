import os
from datetime import datetime, timedelta, timezone

import requests

BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
WINDOW_DAYS = 90
PAGE_SIZE = 200  # NOTE: docs state no max size; verify on first live call.


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _tag(classification, key):
    name = ((classification or {}).get(key) or {}).get("name") or ""
    return "" if name.lower() in ("undefined", "other") else name


def _parse_event(ev):
    attractions = (ev.get("_embedded") or {}).get("attractions") or []
    if not attractions:
        return None
    primary = attractions[0]
    classifications = primary.get("classifications") or ev.get("classifications") or [{}]
    cl = classifications[0]
    venues = (ev.get("_embedded") or {}).get("venues") or [{}]
    venue = venues[0]
    return {
        "artist": primary.get("name", ""),
        "date": ((ev.get("dates") or {}).get("start") or {}).get("localDate", ""),
        "venue": venue.get("name", ""),
        "city": (venue.get("city") or {}).get("name", ""),
        "url": ev.get("url", ""),
        "tm_genre": _tag(cl, "genre"),
        "tm_subgenre": _tag(cl, "subGenre"),
    }


def search_nearby_music_events(location, radius, unit="miles", api_key=None, state_code=None):
    key = api_key or os.environ.get("TICKETMASTER_API_KEY")
    if not key:
        raise RuntimeError("TICKETMASTER_API_KEY is not set")
    location = location.strip()
    now = datetime.now(timezone.utc)
    params = {
        "apikey": key,
        "segmentName": "Music",
        "radius": str(radius),
        "unit": unit,
        "startDateTime": _iso(now),
        "endDateTime": _iso(now + timedelta(days=WINDOW_DAYS)),
        "sort": "date,asc",
        "size": PAGE_SIZE,
    }
    if location.isdigit():
        params["postalCode"] = location
    else:
        params["city"] = location
        if state_code:  # only meaningful for city searches; a zip already pins the place
            params["stateCode"] = state_code

    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    raw = (resp.json().get("_embedded") or {}).get("events") or []

    seen, events = set(), []
    for ev in raw:
        parsed = _parse_event(ev)
        if not parsed:
            continue
        k = (parsed["artist"], parsed["venue"], parsed["date"])
        if k in seen:
            continue
        seen.add(k)
        events.append(parsed)
    return events


ATTRACTIONS_URL = "https://app.ticketmaster.com/discovery/v2/attractions.json"


def lookup_attraction_tags(name, api_key=None):
    """Genre/subGenre tags for an artist by exact normalized name, or None."""
    from names import normalize_name

    key = api_key or os.environ.get("TICKETMASTER_API_KEY")
    if not key:
        raise RuntimeError("TICKETMASTER_API_KEY is not set")
    try:
        resp = requests.get(
            ATTRACTIONS_URL, params={"apikey": key, "keyword": name, "size": 10}, timeout=15
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None
    target = normalize_name(name)
    for a in (resp.json().get("_embedded") or {}).get("attractions") or []:
        if normalize_name(a.get("name", "")) == target:
            cl = (a.get("classifications") or [{}])[0]
            tags = {"tm_genre": _tag(cl, "genre"), "tm_subgenre": _tag(cl, "subGenre")}
            return tags if (tags["tm_genre"] or tags["tm_subgenre"]) else None
    return None
