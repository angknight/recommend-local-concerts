import spotipy

import spotify_client as sc


class FakeSp:
    def __init__(self, fail429=0):
        self.fail429, self.calls = fail429, 0

    def current_user_recently_played(self, limit):
        self.calls += 1
        if self.calls <= self.fail429:
            raise spotipy.SpotifyException(429, -1, "rate", headers={"Retry-After": "0"})
        return {"items": [
            {"track": {"artists": [{"id": "a", "name": "A"}, {"id": "z", "name": "Feat"}]}},
            {"track": {"artists": [{"id": "a", "name": "A"}]}},
            {"track": {"artists": [{"id": None, "name": "Local"}]}},
        ]}


def test_primary_artist_and_repeats_preserved():
    assert sc.get_recent_tracks(FakeSp()) == [("a", "A"), ("a", "A")]


def test_429_retry_then_success():
    assert len(sc.get_recent_tracks(FakeSp(fail429=2))) == 2


def test_429_exhausted_returns_empty():
    assert sc.get_recent_tracks(FakeSp(fail429=99)) == []
