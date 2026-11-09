from names import normalize_name


def test_accents():
    assert normalize_name("Beyoncé") == "beyonce"


def test_punctuation():
    assert normalize_name("Guns N' Roses!") == "guns n roses"


def test_leading_the():
    assert normalize_name("The Strokes") == "strokes"
    assert normalize_name("Theory of a Deadman") == "theory of a deadman"


def test_whitespace():
    assert normalize_name("  Arctic   Monkeys ") == "arctic monkeys"
