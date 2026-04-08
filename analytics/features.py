from collections import Counter

from analytics.constants import (
    ADJ_POS,
    FUNCTION_WORDS,
    METRICS_VERSION,
    NOUN_POS,
    PRONOUN_POS,
    SERVICE_POS,
    TOP_WORDS_LIMIT,
    VERB_POS,
)
from analytics.morph import parse_word
from analytics.preprocessing import normalize_text, split_sentences, split_tokens, tokenize_text


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _base_additional_metrics() -> dict:
    return {
        "version": METRICS_VERSION,
        "function_word_frequencies": {},
        "punctuation_distribution": {},
        "parts_of_speech_distribution": {},
        "top_word_frequencies": {},
        "case_distribution": {},
        "verb_tense_distribution": {},
    }


def _relative_frequencies(counter: Counter, total: int) -> dict[str, float]:
    if total == 0:
        return {}
    return {key: count / total for key, count in counter.items()}


def extract_text_metrics(text: str) -> dict:
    normalized_text = normalize_text(text)
    if not normalized_text:
        return {
            "word_count": 0,
            "sentence_count": 0,
            "avg_word_length": 0.0,
            "avg_sentence_length": 0.0,
            "ttr": 0.0,
            "punctuation_ratio": 0.0,
            "noun_ratio": 0.0,
            "verb_ratio": 0.0,
            "adj_ratio": 0.0,
            "pronoun_ratio": 0.0,
            "service_words_ratio": 0.0,
            "unique_words_count": 0,
            "additional_metrics": _base_additional_metrics(),
        }

    sentences = split_sentences(normalized_text)
    tokens = tokenize_text(normalized_text)
    word_tokens, punct_tokens, _ = split_tokens(tokens)

    word_count = len(word_tokens)
    sentence_count = len(sentences)
    if sentence_count == 0 and word_count > 0:
        sentence_count = 1

    avg_word_length = _safe_div(sum(len(token) for token in word_tokens), word_count)
    avg_sentence_length = _safe_div(word_count, sentence_count)

    total_token_count = len(tokens)
    punctuation_ratio = _safe_div(len(punct_tokens), total_token_count)

    lemma_counts: Counter[str] = Counter()
    pos_counts: Counter[str] = Counter()
    case_counts: Counter[str] = Counter()
    tense_counts: Counter[str] = Counter()
    function_word_counts: Counter[str] = Counter()

    noun_count = 0
    verb_count = 0
    adj_count = 0
    pronoun_count = 0
    service_word_count = 0

    for token in word_tokens:
        lowered = token.lower()
        parsed = parse_word(lowered)
        lemma = parsed["lemma"]
        pos = parsed["pos"]
        case = parsed["case"]
        tense = parsed["tense"]

        lemma_counts[lemma] += 1

        if pos:
            pos_counts[pos] += 1
            if pos in NOUN_POS:
                noun_count += 1
            if pos in VERB_POS:
                verb_count += 1
            if pos in ADJ_POS:
                adj_count += 1
            if pos in PRONOUN_POS:
                pronoun_count += 1
            if pos in SERVICE_POS:
                service_word_count += 1

        if case:
            case_counts[case] += 1
        if tense:
            tense_counts[tense] += 1

        if lemma in FUNCTION_WORDS:
            function_word_counts[lemma] += 1

    unique_words_count = len(lemma_counts)
    ttr = _safe_div(unique_words_count, word_count)

    punctuation_distribution = _relative_frequencies(Counter(punct_tokens), len(punct_tokens))
    parts_of_speech_distribution = _relative_frequencies(pos_counts, word_count)
    case_distribution = _relative_frequencies(case_counts, sum(case_counts.values()))
    verb_tense_distribution = _relative_frequencies(tense_counts, sum(tense_counts.values()))
    function_word_frequencies = _relative_frequencies(function_word_counts, word_count)

    top_word_frequencies = {
        lemma: count / word_count
        for lemma, count in lemma_counts.most_common(TOP_WORDS_LIMIT)
    } if word_count else {}

    additional_metrics = {
        "version": METRICS_VERSION,
        "function_word_frequencies": function_word_frequencies,
        "punctuation_distribution": punctuation_distribution,
        "parts_of_speech_distribution": parts_of_speech_distribution,
        "top_word_frequencies": top_word_frequencies,
        "case_distribution": case_distribution,
        "verb_tense_distribution": verb_tense_distribution,
    }

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_word_length": avg_word_length,
        "avg_sentence_length": avg_sentence_length,
        "ttr": ttr,
        "punctuation_ratio": punctuation_ratio,
        "noun_ratio": _safe_div(noun_count, word_count),
        "verb_ratio": _safe_div(verb_count, word_count),
        "adj_ratio": _safe_div(adj_count, word_count),
        "pronoun_ratio": _safe_div(pronoun_count, word_count),
        "service_words_ratio": _safe_div(service_word_count, word_count),
        "unique_words_count": unique_words_count,
        "additional_metrics": additional_metrics,
    }
