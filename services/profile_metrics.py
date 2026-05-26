from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from analytics.constants import METRICS_VERSION, TOP_WORDS_LIMIT
from db import crud, models


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _weighted_avg(pairs: list[tuple[float | None, int]]) -> float:
    total_weight = 0
    total_value = 0.0
    for value, weight in pairs:
        if value is None or weight <= 0:
            continue
        total_weight += weight
        total_value += value * weight
    return _safe_div(total_value, total_weight)


def _merge_counts(target: dict[str, float], source: dict[str, Any], weight: int) -> None:
    if weight <= 0:
        return
    for key, value in source.items():
        try:
            target[key] = target.get(key, 0.0) + float(value) * weight
        except (TypeError, ValueError):
            continue


def _normalize_counts(counts: dict[str, float]) -> dict[str, float]:
    total = sum(counts.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in counts.items()}


def _top_n_from_counts(counts: dict[str, float], limit: int) -> dict[str, float]:
    if not counts or limit <= 0:
        return {}
    sorted_items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return dict(sorted_items[:limit])


def _get_additional_dict(metrics: models.TextMetrics, key: str) -> dict[str, Any]:
    payload = metrics.additional_metrics or {}
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _aggregate_additional_metrics(
    text_metrics: list[models.TextMetrics],
    total_word_count: int,
) -> tuple[dict[str, Any], list[str]]:
    function_word_counts: dict[str, float] = {}
    punctuation_counts: dict[str, float] = {}
    pos_counts: dict[str, float] = {}
    top_word_counts: dict[str, float] = {}
    case_counts: dict[str, float] = {}
    tense_counts: dict[str, float] = {}
    pos_bigram_counts: dict[str, float] = {}
    pos_trigram_counts: dict[str, float] = {}

    approximate_keys = []

    for metrics in text_metrics:
        word_count = metrics.word_count or 0
        if word_count <= 0:
            continue

        _merge_counts(function_word_counts, _get_additional_dict(metrics, "function_word_frequencies"), word_count)
        _merge_counts(pos_counts, _get_additional_dict(metrics, "parts_of_speech_distribution"), word_count)
        _merge_counts(top_word_counts, _get_additional_dict(metrics, "top_word_frequencies"), word_count)

        _merge_counts(
            pos_bigram_counts,
            _get_additional_dict(metrics, "pos_bigram_frequencies"),
            word_count,
        )
        _merge_counts(
            pos_trigram_counts,
            _get_additional_dict(metrics, "pos_trigram_frequencies"),
            word_count,
        )

        _merge_counts(punctuation_counts, _get_additional_dict(metrics, "punctuation_distribution"), word_count)
        _merge_counts(case_counts, _get_additional_dict(metrics, "case_distribution"), word_count)
        _merge_counts(tense_counts, _get_additional_dict(metrics, "verb_tense_distribution"), word_count)

    if punctuation_counts:
        approximate_keys.append("punctuation_distribution")
    if case_counts:
        approximate_keys.append("case_distribution")
    if tense_counts:
        approximate_keys.append("verb_tense_distribution")
    if pos_bigram_counts:
        approximate_keys.append("pos_bigram_frequencies")
    if pos_trigram_counts:
        approximate_keys.append("pos_trigram_frequencies")

    function_word_frequencies = _normalize_counts(function_word_counts)
    punctuation_distribution = _normalize_counts(punctuation_counts)
    parts_of_speech_distribution = _normalize_counts(pos_counts)
    case_distribution = _normalize_counts(case_counts)
    verb_tense_distribution = _normalize_counts(tense_counts)
    pos_bigram_frequencies = _normalize_counts(pos_bigram_counts)
    pos_trigram_frequencies = _normalize_counts(pos_trigram_counts)

    top_word_counts = _top_n_from_counts(top_word_counts, TOP_WORDS_LIMIT)

    if top_word_counts and total_word_count > 0:
        top_word_frequencies = {
            key: value / total_word_count for key, value in top_word_counts.items()
        }
    else:
        top_word_frequencies = {}

    additional_metrics = {
        "version": METRICS_VERSION,
        "function_word_frequencies": function_word_frequencies,
        "punctuation_distribution": punctuation_distribution,
        "parts_of_speech_distribution": parts_of_speech_distribution,
        "top_word_frequencies": top_word_frequencies,
        "case_distribution": case_distribution,
        "verb_tense_distribution": verb_tense_distribution,
        "pos_bigram_frequencies": pos_bigram_frequencies,
        "pos_trigram_frequencies": pos_trigram_frequencies,
        "aggregation_meta": {
            "top_words_limit": TOP_WORDS_LIMIT,
            "approximate_distributions": approximate_keys,
        },
    }

    return additional_metrics, approximate_keys


def aggregate_profile_metrics(
    text_metrics: list[models.TextMetrics],
    texts_total: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    texts_with_metrics = len(text_metrics)

    if texts_with_metrics == 0:
        core_metrics = {
            "metrics_version": METRICS_VERSION,
            "text_count": texts_total,
            "texts_with_metrics": 0,
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
            "aggregation_meta": {
                "approx_unique_words": True,
                "approx_ttr": True,
            },
        }

        additional_metrics = {
            "version": METRICS_VERSION,
            "function_word_frequencies": {},
            "punctuation_distribution": {},
            "parts_of_speech_distribution": {},
            "top_word_frequencies": {},
            "case_distribution": {},
            "verb_tense_distribution": {},
            "pos_bigram_frequencies": {},
            "pos_trigram_frequencies": {},
            "aggregation_meta": {
                "top_words_limit": TOP_WORDS_LIMIT,
                "approximate_distributions": [],
            },
        }

        return core_metrics, additional_metrics

    total_word_count = sum(metrics.word_count or 0 for metrics in text_metrics)
    total_sentence_count = sum(metrics.sentence_count or 0 for metrics in text_metrics)
    unique_words_sum = sum(metrics.unique_words_count or 0 for metrics in text_metrics)

    avg_word_length = _weighted_avg(
        [(metrics.avg_word_length, metrics.word_count or 0) for metrics in text_metrics]
    )

    avg_sentence_length = _weighted_avg(
        [(metrics.avg_sentence_length, metrics.sentence_count or 0) for metrics in text_metrics]
    )

    punctuation_ratio = _weighted_avg(
        [(metrics.punctuation_ratio, metrics.word_count or 0) for metrics in text_metrics]
    )

    noun_ratio = _weighted_avg(
        [(metrics.noun_ratio, metrics.word_count or 0) for metrics in text_metrics]
    )

    verb_ratio = _weighted_avg(
        [(metrics.verb_ratio, metrics.word_count or 0) for metrics in text_metrics]
    )

    adj_ratio = _weighted_avg(
        [(metrics.adj_ratio, metrics.word_count or 0) for metrics in text_metrics]
    )

    pronoun_ratio = _weighted_avg(
        [(metrics.pronoun_ratio, metrics.word_count or 0) for metrics in text_metrics]
    )

    service_words_ratio = _weighted_avg(
        [(metrics.service_words_ratio, metrics.word_count or 0) for metrics in text_metrics]
    )

    if total_word_count > 0:
        ttr = _safe_div(unique_words_sum, total_word_count)
    else:
        ttr = _weighted_avg([(metrics.ttr, metrics.word_count or 0) for metrics in text_metrics])

    additional_metrics, approximate_keys = _aggregate_additional_metrics(
        text_metrics,
        total_word_count,
    )

    core_metrics = {
        "metrics_version": METRICS_VERSION,
        "text_count": texts_total,
        "texts_with_metrics": texts_with_metrics,
        "word_count": total_word_count,
        "sentence_count": total_sentence_count,
        "avg_word_length": avg_word_length,
        "avg_sentence_length": avg_sentence_length,
        "ttr": ttr,
        "punctuation_ratio": punctuation_ratio,
        "noun_ratio": noun_ratio,
        "verb_ratio": verb_ratio,
        "adj_ratio": adj_ratio,
        "pronoun_ratio": pronoun_ratio,
        "service_words_ratio": service_words_ratio,
        "unique_words_count": unique_words_sum,
        "aggregation_meta": {
            "approx_unique_words": True,
            "approx_ttr": True,
            "approximate_distributions": approximate_keys,
            "weighted_by": {
                "avg_word_length": "word_count",
                "avg_sentence_length": "sentence_count",
                "ratios": "word_count",
                "punctuation_ratio": "word_count",
            },
        },
    }

    return core_metrics, additional_metrics


def recalculate_profile_metrics(db: Session, profile_id: int) -> models.ProfileMetrics:
    profile = crud.get_profile_by_id(db, profile_id)

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    texts_total = (
        db.query(models.AuthorProfileText)
        .filter(models.AuthorProfileText.profile_id == profile_id)
        .count()
    )

    text_metrics = (
        db.query(models.TextMetrics)
        .join(models.Text, models.TextMetrics.text_id == models.Text.id)
        .join(models.AuthorProfileText, models.AuthorProfileText.text_id == models.Text.id)
        .filter(models.AuthorProfileText.profile_id == profile_id)
        .all()
    )

    core_metrics, additional_metrics = aggregate_profile_metrics(text_metrics, texts_total)

    existing = crud.get_profile_metrics_by_profile_id(db, profile_id)

    if existing:
        return crud.update_profile_metrics(
            db,
            existing,
            {
                "metrics_version": METRICS_VERSION,
                "core_metrics": core_metrics,
                "additional_metrics": additional_metrics,
            },
        )

    return crud.create_profile_metrics(
        db,
        profile_id=profile_id,
        metrics_version=METRICS_VERSION,
        core_metrics=core_metrics,
        additional_metrics=additional_metrics,
    )


def recalculate_profiles_for_text(db: Session, text_id: int) -> None:
    profile_ids = (
        db.query(models.AuthorProfileText.profile_id)
        .filter(models.AuthorProfileText.text_id == text_id)
        .distinct()
        .all()
    )

    for (profile_id,) in profile_ids:
        recalculate_profile_metrics(db, profile_id)