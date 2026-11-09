import os
import re
import time

import pandas as pd
import requests
import spotipy
import streamlit as st
from dotenv import load_dotenv
from spotipy.cache_handler import CacheHandler, MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth

from names import normalize_name
from recommend import build_recommendations
from spotify_client import get_recent_tracks
from taste_profile import build_taste_profile, candidate_doc
from ticketmaster_client import lookup_attraction_tags, search_nearby_music_events

load_dotenv()

SCOPE = "user-read-recently-played"
REQUIRED_ENV = [
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
    "SPOTIFY_REDIRECT_URI",
    "TICKETMASTER_API_KEY",
]


class SessionCacheHandler(CacheHandler):
    """Keeps the token in this browser session only, never on disk or shared."""

    def get_cached_token(self):
        return st.session_state.get("spotify_token")

    def save_token_to_cache(self, token_info):
        st.session_state["spotify_token"] = token_info


def make_auth(cache_handler):
    return SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope=SCOPE,
        cache_handler=cache_handler,
        open_browser=False,
    )


@st.cache_resource(ttl=120, show_spinner=False)
def exchange_code(code):
    """Auth codes are single-use, but the browser can load the redirect in two
    sessions at once. Caching by code (briefly) lets both get the same token."""
    return make_auth(MemoryCacheHandler()).get_access_token(code, as_dict=True, check_cache=False)


def get_spotify_client():
    """Returns an authenticated spotipy client, or None after rendering the login link."""
    auth = make_auth(SessionCacheHandler())
    token = auth.cache_handler.get_cached_token()
    if token:
        token = auth.validate_token(token)  # refreshes if expired; None if unusable
    if not token and "code" in st.query_params:
        code = st.query_params["code"]
        st.query_params.clear()
        try:
            token = exchange_code(code)
            auth.cache_handler.save_token_to_cache(token)
        except Exception as e:
            print(f"Spotify token exchange failed: {type(e).__name__}: {e}", flush=True)
            st.error("Spotify login failed. Please try again.")
    if not token:
        st.link_button("Log in with Spotify", auth.get_authorize_url())
        return None
    return spotipy.Spotify(auth=token["access_token"])


@st.cache_data(ttl=3600, show_spinner=False)
def cached_tm_tags(norm_name, display_name):
    time.sleep(0.25)  # Ticketmaster limit: 5 requests/second
    return lookup_attraction_tags(display_name)


US_STATES = (
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO "
    "MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY"
).split()


def run_pipeline(sp, location, radius, state_code=None):
    track_artists = get_recent_tracks(sp)

    # Genres come from Ticketmaster for both sides so the vocabularies match
    # (Spotify returns empty genres for most artists).
    artist_info = {}
    unique_artists = dict(dict.fromkeys(track_artists))  # (id, name) pairs, unique
    progress = st.progress(0.0, text="Looking up your artists' genres...")
    for i, (aid, name) in enumerate(unique_artists, 1):
        tags = cached_tm_tags(normalize_name(name), name)
        genres = list(dict.fromkeys(t for t in (tags["tm_genre"], tags["tm_subgenre"]) if t)) if tags else []
        artist_info[aid] = {"name": name, "genres": genres}
        progress.progress(i / len(unique_artists), text=f"Looking up your artists' genres ({i}/{len(unique_artists)})")
    progress.empty()
    profile_doc, known_names = build_taste_profile(track_artists, artist_info)

    events = search_nearby_music_events(location, radius, "miles", state_code=state_code)
    candidates = [
        {**e, "doc": candidate_doc(e["tm_genre"], e["tm_subgenre"]), "low_confidence": False}
        for e in events
    ]

    results = build_recommendations(profile_doc, candidates, known_names)
    rated = sorted((r for r in results if not r["unrated"]), key=lambda r: r["match_score"], reverse=True)
    unrated = [r for r in results if r["unrated"]]
    stats = {
        "tracks": len(track_artists),
        "artists": len(artist_info),
        "artists_with_genres": sum(1 for v in artist_info.values() if v["genres"]),
        "events": len(events),
    }
    return rated, unrated, stats


def to_frame(rows, rated):
    data = []
    for r in rows:
        row = {"Artist": r["artist"]}
        if rated:
            row["Match %"] = round(r["match_score"] * 100)
        row.update(
            {
                "Status": "Already known" if r["known"] else "New suggestion",
                "Date": r["date"],
                "Venue": r["venue"],
                "City": r["city"],
                "Tickets": r["url"],
            }
        )
        data.append(row)
    return pd.DataFrame(data)


def show_table(df):
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        height="content",
        column_config={
            "Tickets": st.column_config.LinkColumn("Tickets", display_text="Buy"),
            "Match %": st.column_config.ProgressColumn("Match %", min_value=0, max_value=100, format="%d%%"),
        },
    )


STYLE = """
<style>
header[data-testid="stHeader"] { background: #eef2f7; }
.block-container { padding-top: 4.5rem; max-width: 1100px; }
.banner {
    background: linear-gradient(120deg, #243b5a, #44689a);
    color: #fff;
    border-radius: 12px;
    margin: 0 0 1.5rem;
    padding: 2rem;
}
.banner h1 { color: #fff; font-size: 2.2rem; margin: 0; padding: 0; }
.banner p { color: #fff; margin: .35rem 0 0; font-size: 1.05rem; }
.stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
    color: #334155 !important;
    opacity: 1 !important;
}
input::placeholder, textarea::placeholder { color: #5b6b7f !important; opacity: 1; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"] .stSlider) {
    background: #fff;
    border: none;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(36, 52, 71, .12);
    padding: .5rem;
}
.stButton > button, .stLinkButton > a {
    border-radius: 999px;
    background: #4a74a8;
    color: #fff;
    border: none;
    padding: .45rem 1.6rem;
    font-weight: 600;
}
.stButton > button *, .stLinkButton > a * { color: #fff !important; }
.stButton > button:hover, .stLinkButton > a:hover { background: #3b6190; color: #fff; }
div[data-testid="stDataFrame"] {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(36, 52, 71, .10);
    padding: .4rem;
}
</style>
"""

BANNER = """
<div class="banner">
  <h1>Spotify Concert Recommender</h1>
  <p>Concerts that match your listening</p>
</div>
"""


def main():
    st.markdown(STYLE + BANNER, unsafe_allow_html=True)

    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        st.error(
            "Missing environment variables: " + ", ".join(missing)
            + ". Copy .env.example to .env and fill them in (see README)."
        )
        return

    sp = get_spotify_client()
    if sp is None:
        return

    with st.container(border=True):
        location = st.text_input("City or US Zip Code", placeholder="e.g. Seattle or 98101", max_chars=50)
        state = st.selectbox(
            "State (optional, for city searches)",
            [None, *US_STATES],
            format_func=lambda s: "Any state" if s is None else s,
        )
        radius = st.slider("Radius (miles)", 5, 200, 50)
        only_new = st.checkbox("Include Only Concerts For New Artists I Have Not Listened To Recently", value=False)
        cap = st.selectbox(
            "How Many Concerts To Show",
            [None, *range(10, 60, 10)],
            format_func=lambda n: "Show All Results" if n is None else f"Up to {n} concerts",
        )
        search = st.button("Find Concerts")

    if not search:
        return
    location = location.strip()
    is_zip = re.fullmatch(r"[0-9]{5}", location)
    is_city = re.fullmatch(r"[^\W\d_](?:[^\W\d_]|[ .'\-]){0,49}", location)
    if not (is_zip or is_city):
        st.warning("Please enter a city name (like Seattle) or a 5-digit US zip code (like 98101).")
        return

    try:
        rated, unrated, stats = run_pipeline(sp, location, radius, state)
    except requests.RequestException:
        st.error("Couldn't reach Ticketmaster. Check your API key and try again.")
        return
    except spotipy.SpotifyException:
        st.error("Spotify request failed. Try logging in again.")
        return

    st.subheader("Your Local Concert Recommendations")
    st.caption(
        f"Recent plays: {stats['tracks']} · artists with genres: {stats['artists_with_genres']}/{stats['artists']} · "
        f"events: {stats['events']}"
    )

    if only_new:
        rated = [r for r in rated if not r["known"]]
        unrated = [r for r in unrated if not r["known"]]

    if cap:  # best matches first; unrated fill whatever room is left
        rated = rated[:cap]
        unrated = unrated[: max(0, cap - len(rated))]

    if not rated and not unrated:
        st.info("No upcoming concerts found for that location and radius. Try a larger radius.")
        return

    if rated:
        show_table(to_frame(rated, rated=True))
    if unrated:
        st.subheader("Concerts We Couldn't Match To Your Taste")
        st.caption(
            "These concerts couldn't be matched to your taste because Ticketmaster has no genre "
            "information for the artist, so they have no Match %. They're listed in case you want "
            "to check them out anyway."
        )
        show_table(to_frame(unrated, rated=False))


main()
