from recommend import build_recommendations


def cand(name, doc, low=False):
    return {"artist": name, "doc": doc, "low_confidence": low}


def test_scoring_and_known_labels():
    user = ["indie_rock"] * 3 + ["jazz"]
    res = build_recommendations(
        user,
        [cand("The Strokes", ["indie_rock"]), cand("Metal Guy", ["death_metal"])],
        {"strokes"},
    )
    by = {r["artist"]: r for r in res}
    assert by["The Strokes"]["match_score"] > by["Metal Guy"]["match_score"]
    assert by["The Strokes"]["known"] is True
    assert by["Metal Guy"]["known"] is False
    assert by["Metal Guy"]["unrated"] is False


def test_empty_doc_unrated():
    res = build_recommendations(["jazz"], [cand("X", [])], set())
    assert res[0]["match_score"] is None and res[0]["unrated"] is True


def test_low_confidence_passthrough():
    res = build_recommendations(["jazz"], [cand("X", ["jazz"], low=True)], set())
    assert res[0]["low_confidence"] is True


def test_empty_user_doc_never_raises():
    res = build_recommendations([], [cand("X", ["jazz"])], set())
    assert res[0]["unrated"] is True
