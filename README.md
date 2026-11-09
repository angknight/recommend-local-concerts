# Spotify Concert Recommender

Reads your recent Spotify listening, then ranks nearby concerts (Ticketmaster) by genre similarity —
including artists you don't already listen to.

## Setup

**Requirements:** Python 3 (developed on 3.14) and a Spotify account. The Spotify account that owns the app needs
Premium (Spotify's rule for dev-mode apps).

### 1. Install

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Get a Spotify Client ID and Secret

1. Log in at https://developer.spotify.com/dashboard and click **Create app**.
2. Enter any name and description. Under **Redirect URIs**, add `http://127.0.0.1:8501` exactly (no trailing
   slash; `localhost` is not allowed) and click **Add**. Under **APIs used**, tick **Web API**. Save.
3. Open the app, then **Settings**. Copy the **Client ID**, and click **View client secret** to copy the secret.
4. Dev-mode apps allow 5 users. To log in with an account other than the owner's, add it under **User Management**.

### 3. Get a Ticketmaster API key

1. Sign up at https://developer.ticketmaster.com.
2. Open **My Apps**, then your app, and copy the **Consumer Key**. The Consumer Secret isn't used.

### 4. Configure

```
cp .env.example .env
```

Fill in `.env`:

| Variable | Value |
| :-- | :-- |
| `SPOTIFY_CLIENT_ID` | Spotify Client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify Client Secret |
| `SPOTIFY_REDIRECT_URI` | `http://127.0.0.1:8501` (must match the dashboard exactly) |
| `TICKETMASTER_API_KEY` | Ticketmaster Consumer Key |

`.env` is git-ignored. Never commit it.

### 5. Run

```
pytest
streamlit run app.py --server.port 8501
```

Open **http://127.0.0.1:8501** (not `localhost`; the Spotify login redirect won't work there). The port must stay
8501 to match the redirect URI.

### 6. Use it

1. Click **Log in with Spotify** and approve access to your recently played tracks.
2. Enter a city name or a 5-digit US zip code. If you entered a city, optionally pick a state to tell cities with
   the same name apart (for example Portland, OR vs. Portland, ME); a zip code ignores the state. Set the radius,
   optionally choose how many concerts to show, and optionally tick **Include Only Concerts For New Artists I Have Not Listened To Recently**.
3. Click **Find Concerts**. Results are ranked by **Match %** against your recent listening. Concerts whose
   artist Ticketmaster has no genre for appear under **Concerts We Couldn't Match To Your Taste**, with no score.

### Troubleshooting

- **"redirect_uri: Not matching configuration" on Spotify:** the URI in the dashboard doesn't match `.env`
  exactly, or you didn't click Save after adding it.
- **"Spotify login failed" and `CERTIFICATE_VERIFY_FAILED` in the terminal:** you're behind a corporate TLS proxy
  that re-signs HTTPS traffic with a private root CA, which Python doesn't trust. Export your organization's root
  CA certificate to a PEM file, append it to Python's default certificates, and point `REQUESTS_CA_BUNDLE` at the
  result (macOS example, substitute your CA's name):
  ```
  security find-certificate -a -p -c "YOUR ROOT CA NAME" /Library/Keychains/System.keychain > root-ca.pem
  cat "$(python -c 'import certifi; print(certifi.where())')" root-ca.pem > ca-bundle.pem
  REQUESTS_CA_BUNDLE=$PWD/ca-bundle.pem streamlit run app.py --server.port 8501
  ```
  Don't disable certificate verification.

## Known limitations

- Ticketmaster skews toward arenas, theaters and larger clubs; small local shows are often absent.
  Future work: SeatGeek or JamBase behind the same event-dict shape.
- Results are capped at the first 200 events in the ~90-day window (the docs state no max `size`; verify).
- Spotify returns empty `genres` for most artists (verified, incl. Beyoncé and Noah Kahan), so Spotify is used only for
  listening history. Genres for both your artists and the concerts come from Ticketmaster's coarse genre/subGenre tags,
  looked up by exact normalized artist name. Artists Ticketmaster doesn't tag are listed under "Concerts We Couldn't Match To Your Taste".
- Spotify's batch `/artists` endpoint was removed for new apps (Feb 2026); the app doesn't need it.
- Genre similarity is a heuristic content-based model, not trained ML; no labeled feedback data exists.
- Tokens live in the Streamlit session only. The OAuth `state` parameter isn't checked because the redirect starts a new session.
