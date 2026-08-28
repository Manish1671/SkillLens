"""Quiz answer helpers.

Selected quiz answers are stored on Attempt.code_text as JSON:

    {"kind":"quiz","selected_option":"b"}

This reuses the existing attempt column instead of a second answers table.
Correctness is never taken from the client; the server compares selected_option
to Problem.quiz_spec.correct_option_id.
"""

from __future__ import annotations

import json
from typing import Any

QUIZ_RESPONSE_KIND = "quiz"


class QuizSpecError(ValueError):
    """Raised when a quiz problem is missing a usable answer key."""


def public_quiz_options(quiz_spec: dict[str, Any] | None) -> list[dict[str, str]]:
    if not quiz_spec:
        return []
    raw = quiz_spec.get("options")
    if not isinstance(raw, list):
        return []
    options: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        option_id = str(item.get("id", "")).strip()
        label = str(item.get("label", ""))
        if not option_id:
            continue
        options.append({"id": option_id, "label": label})
    return options


def valid_option_ids(quiz_spec: dict[str, Any] | None) -> set[str]:
    return {item["id"] for item in public_quiz_options(quiz_spec)}


def correct_option_id(quiz_spec: dict[str, Any] | None) -> str:
    if not quiz_spec:
        raise QuizSpecError("Quiz is missing quiz_spec")
    raw = quiz_spec.get("correct_option_id")
    if raw is None or str(raw).strip() == "":
        raise QuizSpecError("Quiz is missing correct_option_id")
    option_id = str(raw).strip()
    if option_id not in valid_option_ids(quiz_spec):
        raise QuizSpecError("Quiz correct_option_id is not among published options")
    return option_id


def evaluate_quiz_selection(quiz_spec: dict[str, Any] | None, selected_option: str) -> bool:
    return selected_option.strip() == correct_option_id(quiz_spec)


def encode_quiz_response(selected_option: str) -> str:
    return json.dumps(
        {"kind": QUIZ_RESPONSE_KIND, "selected_option": selected_option.strip()},
        separators=(",", ":"),
    )


def decode_quiz_response(code_text: str | None) -> str | None:
    if not code_text:
        return None
    try:
        payload = json.loads(code_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("kind") != QUIZ_RESPONSE_KIND:
        return None
    raw = payload.get("selected_option")
    if raw is None:
        return None
    selected = str(raw).strip()
    return selected or None
