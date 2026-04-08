from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp, sqrt
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
)

_WEIGHTS = {
    "cosine_similarity": 0.4,
    "burrows_delta": 0.6,
}

_DELTA_EPS = 1e-12
_DELTA_TOP_N = 200
_DELTA_ALPHA = 0.25


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be UTF-8 text") from exc


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
    return _MetricsBundle(core_metrics=core_metrics, additional_metrics=additional_metrics)


def _metrics_from_payload(payload: dict[str, Any]) -> _MetricsBundle:
    core_metrics = {key: payload.get(key) for key in _SCALAR_FEATURES}
    additional_metrics = payload.get("additional_metrics") or {}
    return _MetricsBundle(core_metrics=core_metrics, additional_metrics=additional_metrics)


def _vectorize(bundle: _MetricsBundle) -> dict[str, float]:
    vector: dict[str, float] = {}
    for key in _SCALAR_FEATURES:
        value = bundle.core_metrics.get(key)
        if value is None:
            continue
        try:
            vector[f"scalar:{key}"] = float(value)
        except (TypeError, ValueError):
            continue
    for feature_name in _DISTRIBUTION_FEATURES:
        distribution = bundle.additional_metrics.get(feature_name)
        if not isinstance(distribution, dict):
            continue
        for name, value in distribution.items():
            try:
                vector[f"{feature_name}:{name}"] = float(value)
            except (TypeError, ValueError):
                continue
    return vector


def _align_vectors(profile_vector: dict[str, float], candidate_vector: dict[str, float]) -> tuple[list[float], list[float], list[str]]:
    keys = sorted(set(profile_vector) | set(candidate_vector))
    profile_values = [profile_vector.get(key, 0.0) for key in keys]
    candidate_values = [candidate_vector.get(key, 0.0) for key in keys]
    return profile_values, candidate_values, keys


def _cosine_similarity(a: Iterable[float], b: Iterable[float]) -> float:
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b, strict=False):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    denom = sqrt(norm_a) * sqrt(norm_b)
    if denom == 0.0:
        return 0.0
    return dot / denom


def _score_probability(metrics: dict[str, float]) -> tuple[float, dict[str, Any]]:
    cosine = metrics.get("cosine_similarity", 0.0)
    delta = metrics.get("burrows_delta", 0.0)
    cosine_norm = max(0.0, min(1.0, cosine))
    delta_norm = exp(-_DELTA_ALPHA * max(delta, 0.0))

    weight_sum = sum(_WEIGHTS.values()) or 1.0
    probability = (
              (_WEIGHTS["cosine_similarity"] * cosine_norm)
              + (_WEIGHTS["burrows_delta"] * delta_norm)
      ) / weight_sum

    meta = {
        "normalized_metrics": {
            "cosine_similarity": cosine_norm,
            "burrows_delta": delta_norm,
        },
        "weights": dict(_WEIGHTS),
        "weight_sum": weight_sum,
        "combined_score": probability,
        "method": "weighted-normalized-score",
    }
    return probability, meta


def _delta_feature_vector(bundle: _MetricsBundle, feature_keys: list[str]) -> list[float]:
    distribution = bundle.additional_metrics.get("function_word_frequencies")
    if not isinstance(distribution, dict):
        distribution = {}
    vector = []
    for key in feature_keys:
        try:
            vector.append(float(distribution.get(key, 0.0)))
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


def _build_delta_stats(profile_bundles: list[_MetricsBundle]) -> tuple[list[str], list[float], list[float]]:
    features = _select_delta_features(profile_bundles)
    if not features:
        return [], [], []
    per_feature_values: list[list[float]] = [[] for _ in features]
    for bundle in profile_bundles:
        values = _delta_feature_vector(bundle, features)
        for idx, value in enumerate(values):
            per_feature_values[idx].append(value)
    means: list[float] = []
    stds: list[float] = []
    for values in per_feature_values:
        count = len(values)
        if count == 0:
            means.append(0.0)
            stds.append(_DELTA_EPS)
            continue
        mean = sum(values) / count
        variance = sum((value - mean) ** 2 for value in values) / count
        std = sqrt(variance) if variance > _DELTA_EPS else _DELTA_EPS
        means.append(mean)
        stds.append(std)
    return features, means, stds


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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text is required")

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Text not found")
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text is empty")
        metrics_payload = extract_text_metrics(candidate_content)
        candidate_bundle = _metrics_from_payload(metrics_payload)

    profile_bundle = _MetricsBundle(
        core_metrics=profile_metrics.core_metrics or {},
        additional_metrics=profile_metrics.additional_metrics or {},
    )

    profile_vector = _vectorize(profile_bundle)
    candidate_vector = _vectorize(candidate_bundle)
    profile_vals, candidate_vals, keys = _align_vectors(profile_vector, candidate_vector)

    warnings: list[str] = []
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough features to compare",
        )

    cosine_similarity = _cosine_similarity(profile_vals, candidate_vals)
    profile_text_metrics = crud.get_profile_text_metrics(db, profile.id)
    profile_text_bundles = [_metrics_from_text_metrics(metrics) for metrics in profile_text_metrics]
    delta_warnings: list[str] = []
    if len(profile_text_bundles) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough profile texts for Burrows's Delta",
        )
    if len(profile_text_bundles) < 3:
        delta_warnings.append("Burrows's Delta may be unreliable with fewer than 3 profile texts")

    delta_features, delta_means, delta_stds = _build_delta_stats(profile_text_bundles)
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
    probability, probability_meta = _score_probability(comparison_metrics)

    used_features = {
        "total": len(keys),
        "scalars": len([k for k in keys if k.startswith("scalar:")]),
        "distributions": len([k for k in keys if not k.startswith("scalar:")]),
    }

    analysis_meta = {
        "profile_metrics_version": profile_metrics.metrics_version,
        "feature_families": list(_DISTRIBUTION_FEATURES),
        "scalar_features": list(_SCALAR_FEATURES),
        "probability_meta": probability_meta,
        "delta_method": "profile-corpus-zscore",
        "delta_feature_family": "function_word_frequencies",
        "delta_features_used": len(delta_features),
        "delta_top_n": _DELTA_TOP_N,
        "delta_profile_texts": len(profile_text_bundles),
        "delta_epsilon": _DELTA_EPS,
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
        "authorship_probability": probability,
        "used_features": used_features,
        "analysis_meta": analysis_meta,
        "warnings": warnings or None,
        "analyzed_at": datetime.utcnow(),
    }
