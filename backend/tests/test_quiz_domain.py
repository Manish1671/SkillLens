from app.domain.quiz import (
    QuizSpecError,
    decode_quiz_response,
    encode_quiz_response,
    evaluate_quiz_selection,
    public_quiz_options,
)

SPEC = {
    "options": [
        {"id": "a", "label": "Alpha", "correct": True},
        {"id": "b", "label": "Beta"},
    ],
    "correct_option_id": "b",
}


def test_public_options_strip_answer_metadata() -> None:
    options = public_quiz_options(SPEC)
    assert options == [{"id": "a", "label": "Alpha"}, {"id": "b", "label": "Beta"}]
    assert all("correct" not in item for item in options)


def test_evaluate_correct_and_incorrect() -> None:
    assert evaluate_quiz_selection(SPEC, "b") is True
    assert evaluate_quiz_selection(SPEC, "a") is False


def test_evaluate_missing_spec() -> None:
    try:
        evaluate_quiz_selection(None, "a")
    except QuizSpecError:
        return
    raise AssertionError("expected QuizSpecError")


def test_encode_decode_roundtrip() -> None:
    encoded = encode_quiz_response("b")
    assert "correct" not in encoded
    assert decode_quiz_response(encoded) == "b"
