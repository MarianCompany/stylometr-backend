from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp, log1p, sqrt
from typing import Any, Iterable

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from analytics.features import extract_text_metrics
from db import crud, models
from services import profile_metrics as profile_metrics_service

_SCALAR_FEATURES = (
    "avg_word_length",
    "avg_sentence_length",
    "ttr",
    "punctuation_ratio",
    "noun_ratio",
    "verb_ratio",
    "adj_ratio",
    "pronoun_ratio",
    "service_words_ratio",
)

_DISTRIBUTION_FEATURES = (
    "function_word_frequencies",
    "parts_of_speech_distribution",
    "punctuation_distribution",
    "case_distribution",
    "verb_tense_distribution",
    "pos_bigram_frequencies",
    "pos_trigram_frequencies",
)

_DELTA_TOP_N = 200


@dataclass(frozen=True)
class _MetricsBundle:
    core_metrics: dict[str, Any]
    additional_metrics: dict[str, Any]


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-value))


def _load_profile_for_comparison(
    db: Session,
    profile_id: int,
    user: models.User | None,
) -> models.AuthorProfile:
    profile = crud.get_profile_by_id(db, profile_id)

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    if user is None:
        if not profile.is_public:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
        return profile

    if profile.user_id == user.id or profile.is_public:
        return profile

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")


def _load_profile_metrics(db: Session, profile: models.AuthorProfile) -> models.ProfileMetrics:
    metrics = crud.get_profile_metrics_by_profile_id(db, profile.id)

    if not metrics:
        metrics = profile_metrics_service.recalculate_profile_metrics(db, profile.id)

    return metrics


def _ensure_profile_ready(metrics: models.ProfileMetrics) -> None:
    core = metrics.core_metrics or {}

    text_count = core.get("text_count", 0)
    texts_with_metrics = core.get("texts_with_metrics", 0)

    if text_count == 0 or texts_with_metrics == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile has no metrics")


def _decode_upload(file: UploadFile) -> str:
    content = file.file.read()

    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 text",
        ) from exc


def _metrics_from_text_metrics(metrics: models.TextMetrics) -> _MetricsBundle:
    core_metrics = {
        "avg_word_length": metrics.avg_word_length,
        "avg_sentence_length": metrics.avg_sentence_length,
        "ttr": metrics.ttr,
        "punctuation_ratio": metrics.punctuation_ratio,
        "noun_ratio": metrics.noun_ratio,
        "verb_ratio": metrics.verb_ratio,
        "adj_ratio": metrics.adj_ratio,
        "pronoun_ratio": metrics.pronoun_ratio,
        "service_words_ratio": metrics.service_words_ratio,
    }

    additional_metrics = metrics.additional_metrics or {}

    return _MetricsBundle(
        core_metrics=core_metrics,
        additional_metrics=additional_metrics,
    )


def _metrics_from_payload(payload: dict[str, Any]) -> _MetricsBundle:
    core_metrics = {key: payload.get(key) for key in _SCALAR_FEATURES}
    additional_metrics = payload.get("additional_metrics") or {}

    return _MetricsBundle(
        core_metrics=core_metrics,
        additional_metrics=additional_metrics,
    )


def _compute_nonconstant_scalar_features(
    profile_bundles: list[_MetricsBundle],
) -> set[str]:
    nonconstant_features: set[str] = set()

    for feature in _SCALAR_FEATURES:
        values: list[float] = []

        for bundle in profile_bundles:
            value = bundle.core_metrics.get(feature)

            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue

        if len(values) < 2:
            continue

        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)

        if variance > 0.0:
            nonconstant_features.add(feature)

    return nonconstant_features


def _vectorize(
    bundle: _MetricsBundle,
    allowed_scalar_features: set[str],
) -> dict[str, float]:
    vector: dict[str, float] = {}

    for key in _SCALAR_FEATURES:
        if key not in allowed_scalar_features:
            continue

        value = bundle.core_metrics.get(key)

        if value is None:
            continue

        try:
            vector[f"scalar:{key}"] = float(value)
        except (TypeError, ValueError):
            continue

    for feature_name in _DISTRIBUTION_FEATURES:
        distribution = bundle.additional_metrics.get(feature_name, {})

        if not isinstance(distribution, dict):
            continue

        for name, value in distribution.items():
            try:
                vector[f"{feature_name}:{name}"] = float(value)
            except (TypeError, ValueError):
                continue

    return vector


def _align_vectors(
    profile_vector: dict[str, float],
    candidate_vector: dict[str, float],
) -> tuple[list[float], list[float], list[str]]:
    keys = sorted(set(profile_vector) & set(candidate_vector))

    if len(keys) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough shared features to compare",
        )

    profile_values = [profile_vector[key] for key in keys]
    candidate_values = [candidate_vector[key] for key in keys]

    return profile_values, candidate_values, keys


def _cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    a_values = list(a)
    b_values = list(b)

    if len(a_values) < 2 or len(b_values) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough shared features for cosine similarity",
        )

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for x, y in zip(a_values, b_values, strict=False):
        dot += x * y
        norm_a += x * x
        norm_b += y * y

    denom = sqrt(norm_a) * sqrt(norm_b)

    if denom == 0.0:
        return 0.0

    return dot / denom


def _score_probability(
    metrics: dict[str, float],
    n_profile_texts: int,
) -> tuple[float, dict[str, Any]]:
    cosine = metrics.get("cosine_similarity", 0.0)
    delta = metrics.get("burrows_delta", 0.0)

    cosine_norm = max(0.0, min(1.0, cosine))
    delta_norm = 1.0 / (1.0 + max(delta, 0.0))

    delta_weight = min(0.9, 0.6 * (1 - exp(-n_profile_texts / 10)))
    cosine_weight = 1.0 - delta_weight

    weights = {
        "cosine_similarity": cosine_weight,
        "burrows_delta": delta_weight,
    }

    weight_sum = sum(weights.values()) or 1.0

    probability = (
        (weights["cosine_similarity"] * cosine_norm)
        + (weights["burrows_delta"] * delta_norm)
    ) / weight_sum

    meta = {
        "normalized_metrics": {
            "cosine_similarity": cosine_norm,
            "burrows_delta": delta_norm,
        },
        "weights": weights,
        "weight_sum": weight_sum,
        "combined_score": probability,
        "method": "weighted-normalized-score",
        "weighting_strategy": "dynamic-by-profile-text-count",
    }

    return probability, meta


def _delta_feature_vector(bundle: _MetricsBundle, feature_keys: list[str]) -> list[float]:
    distribution = bundle.additional_metrics.get("function_word_frequencies")

    if not isinstance(distribution, dict):
        distribution = {}

    vector = []

    for key in feature_keys:
        try:
            raw_value = float(distribution.get(key, 0.0))
            vector.append(log1p(raw_value))
        except (TypeError, ValueError):
            vector.append(0.0)

    return vector


def _select_delta_features(profile_bundles: list[_MetricsBundle]) -> list[str]:
    aggregate: dict[str, float] = {}

    for bundle in profile_bundles:
        distribution = bundle.additional_metrics.get("function_word_frequencies")

        if not isinstance(distribution, dict):
            continue

        for key, value in distribution.items():
            try:
                aggregate[key] = aggregate.get(key, 0.0) + float(value)
            except (TypeError, ValueError):
                continue

    if not aggregate:
        return []

    sorted_keys = sorted(aggregate.items(), key=lambda item: (-item[1], item[0]))

    return [key for key, _ in sorted_keys[:_DELTA_TOP_N]]


def _build_delta_stats(
    profile_bundles: list[_MetricsBundle],
) -> tuple[list[str], list[float], list[float]]:
    features = _select_delta_features(profile_bundles)

    if not features:
        return [], [], []

    valid_features: list[str] = []
    means: list[float] = []
    stds: list[float] = []

    for feature in features:
        values: list[float] = []

        for bundle in profile_bundles:
            distribution = bundle.additional_metrics.get("function_word_frequencies")

            if not isinstance(distribution, dict):
                continue

            try:
                raw_value = float(distribution.get(feature, 0.0))
                values.append(log1p(raw_value))
            except (TypeError, ValueError):
                continue

        count = len(values)

        if count < 2:
            continue

        mean = sum(values) / count
        variance = sum((value - mean) ** 2 for value in values) / (count - 1)

        std = sqrt(variance)

        if std == 0.0:
            continue

        valid_features.append(feature)
        means.append(mean)
        stds.append(std)

    return valid_features, means, stds


def _burrows_delta_from_profile_stats(
    features: list[str],
    means: list[float],
    stds: list[float],
    candidate_bundle: _MetricsBundle,
) -> float:
    if not features:
        return 0.0

    candidate_values = _delta_feature_vector(candidate_bundle, features)

    delta_sum = 0.0

    for value, mean, std in zip(candidate_values, means, stds, strict=False):
        delta_sum += abs((value - mean) / std)

    return delta_sum / len(features)

def _scale_probability(probability: float, low: float = 0.70, high: float = 0.95) -> float:
    if probability <= low:
        return 0.0
    if probability >= high:
        return 99.9
    return (probability - low) / (high - low) * 100.0

def compare_text_to_profile(
    db: Session,
    profile_id: int,
    user: models.User | None,
    *,
    text: str | None = None,
    file: UploadFile | None = None,
    text_id: int | None = None,
) -> dict[str, Any]:
    source_count = sum(1 for item in (text, file, text_id) if item)

    if source_count != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of text, file, or text_id",
        )

    if user is None:
        if file is not None or text_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required for this input type",
            )

        if text is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text is required",
            )

    profile = _load_profile_for_comparison(db, profile_id, user)
    profile_metrics = _load_profile_metrics(db, profile)

    _ensure_profile_ready(profile_metrics)

    candidate_text_id: int | None = None
    candidate_source_type = "text"
    candidate_content = ""

    if text_id is not None:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required for text_id",
            )

        stored_text = crud.get_text_by_id(db, text_id)

        if not stored_text or stored_text.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Text not found",
            )

        candidate_text_id = stored_text.id
        candidate_source_type = "stored_text"

        candidate_metrics = crud.get_text_metrics_by_text_id(db, stored_text.id)

        if candidate_metrics:
            candidate_bundle = _metrics_from_text_metrics(candidate_metrics)
        else:
            metrics_payload = extract_text_metrics(stored_text.content)
            candidate_bundle = _metrics_from_payload(metrics_payload)

        candidate_content = stored_text.content

    elif file is not None:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required for file upload",
            )

        candidate_source_type = "file"
        candidate_content = _decode_upload(file)

        metrics_payload = extract_text_metrics(candidate_content)
        candidate_bundle = _metrics_from_payload(metrics_payload)

    else:
        candidate_content = text or ""

        if not candidate_content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text is empty",
            )

        metrics_payload = extract_text_metrics(candidate_content)
        candidate_bundle = _metrics_from_payload(metrics_payload)

    profile_bundle = _MetricsBundle(
        core_metrics=profile_metrics.core_metrics or {},
        additional_metrics=profile_metrics.additional_metrics or {},
    )

    profile_text_metrics = crud.get_profile_text_metrics(db, profile.id)

    profile_text_bundles = [
        _metrics_from_text_metrics(metrics)
        for metrics in profile_text_metrics
    ]

    nonconstant_scalar_features = _compute_nonconstant_scalar_features(
        profile_text_bundles,
    )

    profile_vector = _vectorize(
        profile_bundle,
        allowed_scalar_features=nonconstant_scalar_features,
    )

    candidate_vector = _vectorize(
        candidate_bundle,
        allowed_scalar_features=nonconstant_scalar_features,
    )

    profile_vals, candidate_vals, keys = _align_vectors(
        profile_vector,
        candidate_vector,
    )

    warnings: list[str] = []

    cosine_similarity = _cosine_similarity(profile_vals, candidate_vals)

    delta_warnings: list[str] = []

    if len(profile_text_bundles) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough profile texts for Burrows's Delta",
        )

    if len(profile_text_bundles) < 3:
        delta_warnings.append(
            "Burrows's Delta may be unreliable with fewer than 3 profile texts",
        )

    delta_features, delta_means, delta_stds = _build_delta_stats(
        profile_text_bundles,
    )

    if not delta_features:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough function-word features for Burrows's Delta",
        )

    burrows_delta = _burrows_delta_from_profile_stats(
        delta_features,
        delta_means,
        delta_stds,
        candidate_bundle,
    )

    comparison_metrics = {
        "burrows_delta": burrows_delta,
        "cosine_similarity": cosine_similarity,
    }

    probability, probability_meta = _score_probability(
        comparison_metrics,
        n_profile_texts=len(profile_text_bundles),
    )

    used_features = {
        "total": len(keys),
        "scalars": len([k for k in keys if k.startswith("scalar:")]),
        "distributions": len([k for k in keys if not k.startswith("scalar:")]),
    }

    analysis_meta = {
        "profile_metrics_version": profile_metrics.metrics_version,
        "feature_families": list(_DISTRIBUTION_FEATURES),
        "scalar_features": list(nonconstant_scalar_features),
        "probability_meta": probability_meta,
        "delta_method": "profile-corpus-zscore-log-transformed",
        "delta_feature_family": "function_word_frequencies",
        "delta_features_used": len(delta_features),
        "delta_top_n": _DELTA_TOP_N,
        "delta_profile_texts": len(profile_text_bundles),
        "delta_log_transform": "log1p",
        "delta_variance": "unbiased-sample-variance",
        "delta_zero_variance_features_skipped": True,
        "cosine_shared_features_only": True,
        "dynamic_weighting": True,
        "syntactic_ngrams_enabled": True,
        "syntactic_ngram_types": ["bigrams", "trigrams"],
    }

    if not candidate_content.strip():
        warnings.append("Candidate text is empty")

    warnings.extend(delta_warnings)

    return {
        "profile_id": profile.id,
        "profile_name": profile.name,
        "is_public_profile": profile.is_public,
        "candidate_source_type": candidate_source_type,
        "candidate_text_id": candidate_text_id,
        "candidate_text_length": len(candidate_content),
        "comparison_metrics": comparison_metrics,
        "burrows_delta": burrows_delta,
        "cosine_similarity": cosine_similarity,
        "authorship_probability": _scale_probability(probability),
        "used_features": used_features,
        "analysis_meta": analysis_meta,
        "warnings": warnings or None,
        "analyzed_at": datetime.utcnow(),
    }

