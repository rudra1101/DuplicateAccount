from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ai.duplicate_engine import (
    duplicate_detection_engine,
)
from app.ai.duplicate_engine.types import (
    DuplicatePrediction,
)
from app.ai.ml import (
    duplicate_ml_predictor,
)
from app.ai.vector_store import (
    account_vector_index_service,
)
from app.ai.vector_store.types import (
    VectorSearchResult,
)
from app.ai.duplicate_engine.evidence_attributes import (
    build_different_attributes,
    build_matched_attributes,
)


@dataclass(frozen=True)
class HybridSearchResult:
    vector_similarity: float
    evidence_score: float
    ml_probability: float | None
    final_confidence: float
    classification: str
    recommendation: str
    account: dict[str, Any]
    matched_attributes: list[str]
    different_attributes: list[str]
    reasons: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    features: dict[str, Any]
    model_version: str
    ml_model_version: str | None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "vectorSimilarity": (
                self.vector_similarity
            ),
            "evidenceScore": (
                self.evidence_score
            ),
            "mlProbability": (
                self.ml_probability
            ),
            "finalConfidence": (
                self.final_confidence
            ),
            "classification": (
                self.classification
            ),
            "recommendation": (
                self.recommendation
            ),
            "account": self.account,
            "matchedAttributes": (
                self.matched_attributes
            ),
            "differentAttributes": (
                self.different_attributes
            ),
            "reasons": self.reasons,
            "warnings": self.warnings,
            "features": self.features,
            "modelVersion": (
                self.model_version
            ),
            "mlModelVersion": (
                self.ml_model_version
            ),
        }


ATTRIBUTE_LABELS = {
    "employeeId": "Employee ID",
    "email": "Email",
    "username": "Username",
    "displayName": "Display Name",
    "firstName": "First Name",
    "lastName": "Last Name",
    "phone": "Phone",
    "department": "Department",
    "manager": "Manager",
    "jobTitle": "Job Title",
    "location": "Location",
    "status": "Status",
    "dataQuality": "Data Quality",
}


SEMANTIC_REASON_FIELDS = {
    "semanticName",
    "semanticIdentity",
    "semanticOrganization",
}


def vector_result_to_account(
    result: VectorSearchResult,
) -> dict[str, Any]:
    metadata = result.metadata
    extra = metadata.extra or {}

    return {
        "id": (
            metadata.source_account_id
        ),
        "application": (
            metadata.application
        ),
        "username": (
            metadata.username
        ),
        "displayName": (
            metadata.display_name
        ),
        "email": metadata.email,
        "employeeId": (
            metadata.employee_id
        ),
        "department": (
            extra.get("department")
        ),
        "manager": (
            extra.get("manager")
        ),
        "status": (
            extra.get("status")
        ),
        "jobTitle": (
            extra.get("jobTitle")
        ),
        "location": (
            extra.get("location")
        ),
        "phone": (
            extra.get("phone")
        ),
        "scanId": (
            metadata.scan_id
        ),
        "vectorId": (
            metadata.vector_id
        ),
    }


def has_account_value(
    account: Any,
    attribute_name: str,
) -> bool:
    value = getattr(
        account,
        attribute_name,
        None,
    )

    return bool(
        str(value or "").strip()
    )


def both_have_value(
    prediction: DuplicatePrediction,
    attribute_name: str,
) -> bool:
    return (
        has_account_value(
            prediction.account_1,
            attribute_name,
        )
        and has_account_value(
            prediction.account_2,
            attribute_name,
        )
    )


def build_matched_attributes(
    prediction: DuplicatePrediction,
) -> list[str]:
    features = prediction.features
    matched: list[str] = []

    if both_have_value(prediction, "employee_id") and features.employee_id_exact:
        matched.append("Employee ID")

    if both_have_value(prediction, "email") and features.email_exact:
        matched.append("Email")

    if both_have_value(prediction, "username") and features.username_exact:
        matched.append("Username")
    elif (
        both_have_value(prediction, "username")
        and features.username_similarity >= 0.90
    ):
        matched.append("Username Similarity")

    if (
        both_have_value(prediction, "display_name")
        and features.display_name_similarity >= 0.90
    ):
        matched.append("Display Name")

    if (
        both_have_value(prediction, "first_name")
        and features.first_name_similarity >= 0.90
    ):
        matched.append("First Name")

    if (
        both_have_value(prediction, "last_name")
        and features.last_name_similarity >= 0.90
    ):
        matched.append("Last Name")

    if both_have_value(prediction, "phone") and features.phone_exact:
        matched.append("Phone")

    if both_have_value(prediction, "department") and features.department_exact:
        matched.append("Department")

    if both_have_value(prediction, "manager") and features.manager_exact:
        matched.append("Manager")

    if both_have_value(prediction, "status") and features.status_exact:
        matched.append("Status")

    if (
        both_have_value(prediction, "job_title")
        and features.title_similarity >= 0.90
    ):
        matched.append("Job Title")

    if (
        both_have_value(prediction, "location")
        and features.location_similarity >= 0.90
    ):
        matched.append("Location")

    return matched


def build_different_attributes(
    prediction: DuplicatePrediction,
) -> list[str]:
    features = prediction.features
    different: list[str] = []

    if (
        both_have_value(prediction, "employee_id")
        and not features.employee_id_exact
    ):
        different.append("Employee ID")

    if (
        both_have_value(prediction, "email")
        and not features.email_exact
        and features.email_similarity < 0.85
    ):
        different.append("Email")

    if (
        both_have_value(prediction, "username")
        and not features.username_exact
        and features.username_similarity < 0.80
    ):
        different.append("Username")

    if (
        both_have_value(prediction, "display_name")
        and features.display_name_similarity < 0.80
    ):
        different.append("Display Name")

    if (
        both_have_value(prediction, "first_name")
        and features.first_name_similarity < 0.80
    ):
        different.append("First Name")

    if (
        both_have_value(prediction, "last_name")
        and features.last_name_similarity < 0.80
    ):
        different.append("Last Name")

    if (
        both_have_value(prediction, "department")
        and not features.department_exact
        and features.department_similarity < 0.80
    ):
        different.append("Department")

    if (
        both_have_value(prediction, "manager")
        and not features.manager_exact
        and features.manager_similarity < 0.80
    ):
        different.append("Manager")

    if (
        both_have_value(prediction, "phone")
        and not features.phone_exact
        and features.phone_similarity < 0.80
    ):
        different.append("Phone")

    if (
        both_have_value(prediction, "job_title")
        and features.title_similarity < 0.80
    ):
        different.append("Job Title")

    if (
        both_have_value(prediction, "location")
        and features.location_similarity < 0.80
    ):
        different.append("Location")

    if (
        both_have_value(prediction, "status")
        and not features.status_exact
    ):
        different.append("Status")

    return different


def calculate_vector_evidence_score(
    *,
    prediction: DuplicatePrediction,
    vector_similarity: float,
) -> float:
    """
    Combine evidence-engine confidence with FAISS
    similarity.

    FAISS is a candidate-retrieval signal. It cannot
    independently create a high-confidence match.
    """

    features = prediction.features
    evidence_score = (
        prediction.confidence
    )

    vector_score = max(
        0.0,
        min(
            vector_similarity * 100,
            100.0,
        ),
    )

    has_strong_identifier = any(
        (
            features.employee_id_exact,
            features.email_exact,
            features.phone_exact,
        )
    )

    supporting_matches = sum(
        (
            features.username_exact,
            features.department_exact,
            features.manager_exact,
            features.status_exact,
            (
                features
                .display_name_similarity
                >= 0.85
            ),
            (
                features
                .first_name_similarity
                >= 0.85
                and features
                .last_name_similarity
                >= 0.90
            ),
            (
                features.username_similarity
                >= 0.90
                and features
                .email_local_similarity
                >= 0.90
            ),
        )
    )

    if has_strong_identifier:
        score = (
            evidence_score * 0.90
            + vector_score * 0.10
        )

    elif supporting_matches >= 3:
        score = (
            evidence_score * 0.85
            + vector_score * 0.15
        )

    elif supporting_matches >= 2:
        score = (
            evidence_score * 0.88
            + vector_score * 0.12
        )

    else:
        score = (
            evidence_score * 0.92
            + vector_score * 0.08
        )

    if (
        not has_strong_identifier
        and supporting_matches < 2
    ):
        score = min(
            score,
            62.0,
        )

    if (
        not has_strong_identifier
        and features
        .display_name_similarity
        == 0
        and features
        .first_name_similarity
        == 0
        and features
        .last_name_similarity
        == 0
    ):
        score = min(
            score,
            48.0,
        )

    if (
        features.account_1_missing_fields
        >= 7
        and features.account_2_missing_fields
        >= 7
        and not has_strong_identifier
    ):
        score -= 3

    if (
        not features.employee_id_exact
        and not features.email_exact
        and features.username_similarity
        < 0.80
    ):
        score -= 8

    if (
        features.same_application
        and not has_strong_identifier
    ):
        score -= 5

    return round(
        max(
            0.0,
            min(
                score,
                100.0,
            ),
        ),
        2,
    )


def calculate_final_confidence(
    *,
    prediction: DuplicatePrediction,
    vector_evidence_score: float,
    ml_probability: float | None,
) -> float:
    """
    Blend ML probability with the transparent evidence
    score.

    Until the ML model has substantial, balanced
    reviewer-labelled data, the evidence score remains
    authoritative.
    """

    if ml_probability is None:
        return vector_evidence_score

    features = prediction.features

    has_strong_identifier = any(
        (
            features.employee_id_exact,
            features.email_exact,
            features.phone_exact,
        )
    )

    total_missing = (
        features.account_1_missing_fields
        + features.account_2_missing_fields
    )

    # Use less ML influence for sparse comparisons.
    if total_missing >= 14:
        evidence_weight = 0.85
        ml_weight = 0.15

    elif total_missing >= 10:
        evidence_weight = 0.80
        ml_weight = 0.20

    elif has_strong_identifier:
        evidence_weight = 0.65
        ml_weight = 0.35

    else:
        evidence_weight = 0.75
        ml_weight = 0.25

    final_score = (
        vector_evidence_score
        * evidence_weight
        + ml_probability
        * ml_weight
    )

    # Exact deterministic evidence remains authoritative.
    if (
        features.employee_id_exact
        and features.email_exact
    ):
        final_score = max(
            final_score,
            95.0,
        )

    elif features.employee_id_exact:
        final_score = max(
            final_score,
            88.0,
        )

    elif (
        features.email_exact
        and features.username_similarity
        >= 0.85
    ):
        final_score = max(
            final_score,
            85.0,
        )

    # Prevent an immature ML model from overriding
    # insufficient or contradictory evidence.
    if (
        not has_strong_identifier
        and vector_evidence_score < 40
    ):
        final_score = min(
            final_score,
            55.0,
        )

    if (
        features.email_similarity > 0
        and features.email_similarity
        < 0.35
        and features.username_similarity
        < 0.50
    ):
        final_score = min(
            final_score,
            45.0,
        )

    if (
        total_missing >= 14
        and not has_strong_identifier
    ):
        final_score = min(
            final_score,
            60.0,
        )

    return round(
        max(
            0.0,
            min(
                final_score,
                100.0,
            ),
        ),
        2,
    )


def classify_confidence(
    confidence: float,
) -> str:
    if confidence >= 95:
        return "VERY_HIGH"

    if confidence >= 85:
        return "HIGH"

    if confidence >= 70:
        return "REVIEW_REQUIRED"

    if confidence >= 50:
        return "POSSIBLE_MATCH"

    return "UNLIKELY"


def build_recommendation(
    confidence: float,
) -> str:
    if confidence >= 95:
        return "LIKELY_DUPLICATE"

    if confidence >= 75:
        return "REVIEW"

    if confidence >= 50:
        return "LOW_PRIORITY"

    return "IGNORE"


def search_and_rerank_accounts(
    *,
    query_account: dict[str, Any],
    result_limit: int = 10,
    candidate_limit: int = 30,
    minimum_vector_similarity: float = 0.55,
    minimum_duplicate_confidence: float = 50,
    scan_id: int | None = None,
    application_filter: str | None = None,
    source_account_id: str | None = None,
    exclude_vector_id: int | None = None,
) -> list[HybridSearchResult]:
    candidate_limit = max(
        result_limit,
        candidate_limit,
    )

    vector_candidates = (
        account_vector_index_service
        .search_account(
            query_account,
            limit=candidate_limit,
            minimum_similarity=(
                minimum_vector_similarity
            ),
            scan_id=scan_id,
            application=(
                application_filter
            ),
            source_account_id=(
                source_account_id
            ),
            exclude_vector_id=(
                exclude_vector_id
            ),
        )
    )

    reranked_results: list[
        HybridSearchResult
    ] = []

    for candidate in vector_candidates:
        candidate_account = (
            vector_result_to_account(
                candidate
            )
        )

        prediction = (
            duplicate_detection_engine
            .compare(
                query_account,
                candidate_account,
                include_embeddings=False,
            )
        )

        vector_evidence_score = (
            calculate_vector_evidence_score(
                prediction=prediction,
                vector_similarity=(
                    candidate.score
                ),
            )
        )

        feature_dictionary = (
            prediction
            .features
            .to_dict()
        )

        ml_probability: float | None
        ml_model_version: str | None

        try:
            (
                ml_probability,
                ml_model_version,
            ) = (
                duplicate_ml_predictor
                .predict_probability(
                    feature_dictionary
                )
            )

        except Exception:
            # Search must continue even when the ML model
            # is missing, invalid, or incompatible.
            ml_probability = None
            ml_model_version = None

        final_confidence = (
            calculate_final_confidence(
                prediction=prediction,
                vector_evidence_score=(
                    vector_evidence_score
                ),
                ml_probability=(
                    ml_probability
                ),
            )
        )

        if (
            final_confidence
            < minimum_duplicate_confidence
        ):
            continue

        reasons = [
            reason.to_dict()
            for reason
            in prediction.reasons
        ]

        reasons.append(
            {
                "field": (
                    "vectorSimilarity"
                ),
                "message": (
                    "FAISS retrieved this "
                    "account as a semantic "
                    "candidate."
                ),
                "impact": "SUPPORTING",
                "similarity": round(
                    candidate.score * 100,
                    1,
                ),
            }
        )

        if ml_probability is not None:
            reasons.append(
                {
                    "field": (
                        "mlProbability"
                    ),
                    "message": (
                        "The reviewer-trained "
                        "machine-learning model "
                        "estimated duplicate "
                        "probability."
                    ),
                    "impact": "SUPPORTING",
                    "similarity": (
                        ml_probability
                    ),
                }
            )

        reranked_results.append(
            HybridSearchResult(
                vector_similarity=round(
                    candidate.score,
                    6,
                ),
                evidence_score=(
                    vector_evidence_score
                ),
                ml_probability=(
                    ml_probability
                ),
                final_confidence=(
                    final_confidence
                ),
                classification=(
                    classify_confidence(
                        final_confidence
                    )
                ),
                recommendation=(
                    build_recommendation(
                        final_confidence
                    )
                ),
                account=(
                    candidate_account
                ),
                matched_attributes=(
                    build_matched_attributes(
                        prediction
                    )
                ),
                different_attributes=(
                    build_different_attributes(
                        prediction
                    )
                ),
                reasons=reasons,
                warnings=[
                    warning.to_dict()
                    for warning
                    in prediction.warnings
                ],
                features=(
                    feature_dictionary
                ),
                model_version=(
                    "evidence-vector-ml-reranker-v4"
                ),
                ml_model_version=(
                    ml_model_version
                ),
            )
        )

    reranked_results.sort(
        key=lambda result: (
            result.final_confidence,
            result.vector_similarity,
        ),
        reverse=True,
    )

    return reranked_results[
        :result_limit
    ]