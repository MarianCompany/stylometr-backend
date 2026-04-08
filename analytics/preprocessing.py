from collections.abc import Sequence

import regex
from razdel import sentenize, tokenize

from analytics.constants import PUNCT_RE, WORD_RE


def normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = regex.sub(r"\s+", " ", text)
    return normalized.strip()


def split_sentences(text: str) -> list[str]:
    return [sentence.text for sentence in sentenize(text)]


def tokenize_text(text: str) -> list[str]:
    return [token.text for token in tokenize(text)]


def split_tokens(tokens: Sequence[str]) -> tuple[list[str], list[str], list[str]]:
    word_tokens: list[str] = []
    punct_tokens: list[str] = []
    other_tokens: list[str] = []
    for token in tokens:
        if WORD_RE.match(token):
            word_tokens.append(token)
        elif PUNCT_RE.match(token):
            punct_tokens.append(token)
        else:
            other_tokens.append(token)
    return word_tokens, punct_tokens, other_tokens
