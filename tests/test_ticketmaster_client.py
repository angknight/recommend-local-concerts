from unittest.mock import MagicMock, patch

import ticketmaster_client as tm


def ev(artist, venue="V", date="2026-12-01", with_attr=True):
    e = {
        "url": "http://t/x",
        "dates": {"start": {"localDate": date}},
        "_embedded": {"venues": [{"name": venue, "city": {"name": "Austin"}}]},
    }
    if with_attr:
        e["_embedded"]["attractions"] = [
            {"name": artist, "classifications": [{"genre": {"name": "Rock"}, "subGenre": {"name": "Undefined"}}]},
            {"name": "Opener"},
        ]
    return e


def run(location, events):
    resp = MagicMock()
    resp.json.return_value = {"_embedded": {"events": events}}
    with patch.object(tm.requests, "get", return_value=resp) as g:
        out = tm.search_nearby_music_events(location, 50, "miles", api_key="k")
    return out, g.call_args.kwargs["params"]


def test_city_vs_postal():
    _, p = run("Austin", [])
    assert p["city"] == "Austin" and "postalCode" not in p
    _, p = run("78701", [])
    assert p["postalCode"] == "78701" and "city" not in p


def test_state_code_only_applies_to_city_search():
    def params(location, state):
        resp = MagicMock()
        resp.json.return_value = {"_embedded": {"events": []}}
        with patch.object(tm.requests, "get", return_value=resp) as g:
            tm.search_nearby_music_events(location, 50, "miles", api_key="k", state_code=state)
        return g.call_args.kwargs["params"]

    assert params("Portland", "OR")["stateCode"] == "OR"
    assert "stateCode" not in params("Portland", None)
    assert "stateCode" not in params("97201", "OR")


def test_query_params():
    _, p = run("Austin", [])
    assert p["size"] == 200 and p["sort"] == "date,asc" and p["segmentName"] == "Music"
    assert p["endDateTime"].endswith("Z") and p["unit"] == "miles"


def test_primary_attraction_and_tags():
    out, _ = run("Austin", [ev("Band")])
    assert out[0]["artist"] == "Band"
    assert out[0]["tm_genre"] == "Rock" and out[0]["tm_subgenre"] == ""
    assert out[0]["city"] == "Austin"


def test_skip_no_attractions_and_dedupe():
    out, _ = run("Austin", [ev("A", with_attr=False), ev("B"), ev("B")])
    assert [e["artist"] for e in out] == ["B"]


def test_no_events():
    out, _ = run("Nowhere", [])
    assert out == []


def test_lookup_attraction_tags_exact_match():
    resp = MagicMock()
    resp.json.return_value = {"_embedded": {"attractions": [
        {"name": "Noah Kahan Tribute", "classifications": [{"genre": {"name": "Pop"}}]},
        {"name": "Noah Kahan", "classifications": [{"genre": {"name": "Alternative"}, "subGenre": {"name": "Folk"}}]},
    ]}}
    with patch.object(tm.requests, "get", return_value=resp):
        assert tm.lookup_attraction_tags("noah kahan", api_key="k") == {"tm_genre": "Alternative", "tm_subgenre": "Folk"}


def test_lookup_attraction_tags_none():
    resp = MagicMock()
    resp.json.return_value = {}
    with patch.object(tm.requests, "get", return_value=resp):
        assert tm.lookup_attraction_tags("Nobody", api_key="k") is None
