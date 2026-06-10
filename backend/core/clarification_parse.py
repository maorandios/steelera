"""Infer tap-to-answer chips from assistant prose when ask_clarification was skipped."""

from __future__ import annotations

import re
from typing import Any

from schemas.chat import ChatUiBlock

_NUMBERED_OPTIONS_RE = re.compile(
    r"(\d+)[.)]\s*(?:\*\*)?(.+?)(?:\*\*)?"
    r"(?=(?:,\s*or\s+|\s+or\s+)\d+[.)]|\?\s*(?:Please|$)|\n\n|Please indicate|$)",
    re.IGNORECASE | re.DOTALL,
)

_PROFILE_RE = re.compile(
    r"\b(HEA\d+|HEB\d+|IPE\d+|RHS[\d.xX/-]+|SHS[\d.xX/-]+|"
    r"UB[\d.xX/-]+|UC[\d.xX/-]+|L\d+[\dxX/-]*)\b",
    re.IGNORECASE,
)

_PROFILE_RANGE_RE = re.compile(
    r"from\s+(HEA\d+|HEB\d+|IPE\d+)\s+to\s+(HEA\d+|HEB\d+|IPE\d+)",
    re.IGNORECASE,
)

_YES_NO_CUE_RE = re.compile(
    r"\b(would you like|do you want|should i|shall i|proceed|confirm|prefer to)\b",
    re.IGNORECASE,
)


def _clean_option(raw: str) -> str:
    text = re.sub(r"\*\*", "", raw)
    text = re.sub(r"\s+", " ", text).strip(" ,;.")
    return text


def _block(
    question: str,
    options: list[dict[str, str]],
    *,
    allow_custom: bool = False,
    custom_placeholder: str | None = None,
) -> ChatUiBlock:
    payload: dict[str, Any] = {"question": question, "options": options}
    if allow_custom:
        payload["allowCustom"] = True
        payload["customPlaceholder"] = custom_placeholder or "Type any section e.g. HEA380"
    return ChatUiBlock(type="workspace_quick_replies", payload=payload)


def _infer_numbered(content: str) -> ChatUiBlock | None:
    matches = list(_NUMBERED_OPTIONS_RE.finditer(content))
    if len(matches) < 2 or len(matches) > 4:
        return None

    options: list[dict[str, str]] = []
    for match in matches:
        label = _clean_option(match.group(2))
        if not label or len(label) > 140:
            return None
        options.append({"label": label, "value": label})

    first = matches[0]
    question = content[: first.start()].strip()
    question = re.sub(r"\s+", " ", question).strip(" :") or "Choose an option:"
    return _block(question, options)


def _infer_profile_choices(content: str) -> ChatUiBlock | None:
    if "?" not in content and not _YES_NO_CUE_RE.search(content):
        return None

    range_m = _PROFILE_RANGE_RE.search(content)
    if range_m:
        low, high = range_m.group(1).upper(), range_m.group(2).upper()
        options = [
            {"label": low, "value": f"Yes, switch to {low}"},
            {"label": high, "value": f"Yes, switch to {high}"},
            {"label": "Keep current", "value": "No, keep the current section"},
        ]
        question = content.strip()
        if len(question) > 220:
            question = question.rsplit("?", 1)[0].strip() + "?"
        return _block(
            question,
            options,
            allow_custom=True,
            custom_placeholder="Type any section e.g. HEA380",
        )

    profiles = [p.upper() for p in _PROFILE_RE.findall(content)]
    unique = list(dict.fromkeys(profiles))
    if len(unique) < 2:
        return None

    current_m = re.search(
        r"current(?:\s+\w+){0,3}\s+section\s+is\s+(HEA\d+|HEB\d+|IPE\d+)",
        content,
        re.IGNORECASE,
    )
    current = current_m.group(1).upper() if current_m else None
    suggested = [p for p in unique if p != current]
    if not suggested:
        return None

    options = [
        {"label": p, "value": f"Yes, switch to {p}"} for p in suggested[:3]
    ]
    if current:
        options.append({"label": "Keep current", "value": "No, keep the current section"})
    elif len(options) < 4:
        options.append({"label": "No", "value": "No"})

    question = content.strip()
    if len(question) > 220:
        question = question.rsplit("?", 1)[0].strip() + "?"
    return _block(
        question,
        options[:4],
        allow_custom=True,
        custom_placeholder="Type any section e.g. HEA380",
    )


def _infer_yes_no(content: str) -> ChatUiBlock | None:
    text = content.strip()
    if "?" not in text and not _YES_NO_CUE_RE.search(text):
        return None
    if not _YES_NO_CUE_RE.search(text):
        return None

    question = text
    if len(question) > 240:
        parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        for part in reversed(parts):
            if "?" in part or _YES_NO_CUE_RE.search(part):
                question = part
                break

    return _block(
        question,
        [
            {"label": "Yes", "value": "Yes"},
            {"label": "No", "value": "No"},
        ],
    )


def infer_clarification_ui_block(content: str) -> ChatUiBlock | None:
    if not content or len(content) > 2500:
        return None

    for infer in (_infer_numbered, _infer_profile_choices, _infer_yes_no):
        block = infer(content)
        if block is not None:
            return block
    return None


def apply_inferred_clarification(
    content: str,
    ui_block: ChatUiBlock | None,
) -> tuple[str, ChatUiBlock | None]:
    """Attach inferred chips and shorten visible question text when helpful."""
    if ui_block is not None:
        return content, ui_block

    inferred = infer_clarification_ui_block(content)
    if inferred is None:
        return content, None

    question = str(inferred.payload.get("question") or "").strip()
    if question:
        return question, inferred
    return content, inferred
