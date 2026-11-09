from taste_profile import build_taste_profile, candidate_doc, genre_tokens

INFO = {
    "a": {"name": "A", "genres": ["indie rock", "dream pop"]},
    "b": {"name": "The B", "genres": ["jazz"]},
}


def test_multiword_genres_single_token():
    assert genre_tokens(["Indie Rock"]) == ["indie_rock"]


def test_frequency_weighting():
    doc, _ = build_taste_profile([("a", "A")] * 3 + [("b", "The B")], INFO)
    assert doc.count("indie_rock") == 3
    assert doc.count("jazz") == 1


def test_known_names_normalized():
    _, known = build_taste_profile([("a", "A"), ("b", "The B")], INFO)
    assert known == {"a", "b"}


def test_candidate_doc():
    assert candidate_doc("Rock", "Alternative Rock") == ["rock", "alternative_rock"]
    assert candidate_doc("", "") == []
