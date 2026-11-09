from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from names import normalize_name


def build_recommendations(user_profile_doc, candidates, known_names):
    """Score candidates ({artist, doc, low_confidence, ...}) against the user's doc.

    Candidates with an empty doc (or any candidate when the user doc is empty)
    get match_score=None, unrated=True. Never raises on empty input.
    """
    results = []
    for c in candidates:
        r = dict(c)
        r["known"] = normalize_name(c["artist"]) in known_names
        r["low_confidence"] = bool(c.get("low_confidence", False))
        r["match_score"] = None
        r["unrated"] = True
        results.append(r)

    scorable = [r for r in results if r.get("doc")]
    if not user_profile_doc or not scorable:
        return results

    docs = [user_profile_doc] + [r["doc"] for r in scorable]
    matrix = TfidfVectorizer(analyzer=lambda x: x).fit_transform(docs)
    scores = cosine_similarity(matrix[0], matrix[1:])[0]
    for r, s in zip(scorable, scores):
        r["match_score"] = float(s)
        r["unrated"] = False
    return results
