from functools import lru_cache
from typing import Any

from pymorphy3 import MorphAnalyzer

_MORPH = MorphAnalyzer()


@lru_cache(maxsize=10000)
def parse_word(word: str) -> dict[str, Any]:
    parsed = _MORPH.parse(word)[0]
    return {
        "lemma": parsed.normal_form,
        "pos": parsed.tag.POS,
        "case": parsed.tag.case,
        "tense": parsed.tag.tense,
    }
