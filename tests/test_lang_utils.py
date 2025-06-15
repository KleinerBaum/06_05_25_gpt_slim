from utils.lang_utils import detect_language


def test_detect_language_english() -> None:
    text = "This is a simple English sentence about a job description."
    assert detect_language(text) == "en"


def test_detect_language_german() -> None:
    text = "Dies ist ein einfacher deutscher Satz über eine Stellenanzeige und die Aufgaben."
    assert detect_language(text) == "de"
