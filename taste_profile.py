from names import normalize_name


def genre_tokens(genres):
    """'indie rock' -> 'indie_rock' so TF-IDF treats each genre as one token."""
    tokens = []
    for g in genres or []:
        t = "_".join((g or "").lower().split())
        if t:
            tokens.append(t)
    return tokens


def build_taste_profile(track_artists, artist_info):
    """track_artists: [(artist_id, name)] with repeats; artist_info: {id: {"name", "genres"}}.

    Returns (profile_doc, known_names).
    """
    doc = []
    known = set()
    for artist_id, name in track_artists:
        known.add(normalize_name(name))
        info = artist_info.get(artist_id)
        if info:
            doc.extend(genre_tokens(info.get("genres")))
    return doc, known


def candidate_doc(tm_genre, tm_subgenre):
    """Ticketmaster genre tags -> token doc (empty if Ticketmaster has none)."""
    return list(dict.fromkeys(genre_tokens([tm_genre, tm_subgenre])))
