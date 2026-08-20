from __future__ import annotations

import re
from typing import Any


TECHNICAL_IGNORE_PATTERNS = (
    "objectguid",
    "objectsid",
    "distinguishedname",
    "dn",
    "pwdlastset",
    "whencreated",
    "whenchanged",
    "createdat",
    "updatedat",
    "timestamp",
    "lastlogon",
    "lastlogontimestamp",
    "usnchanged",
    "objectclass",
)


SEMANTIC_RULES: list[dict[str, Any]] = [
    {
        "patterns": (
            "employeeid",
            "employeenumber",
            "employeenumber",
            "workernumber",
            "workerid",
            "personnumber",
            "personid",
            "staffid",
        ),
        "score": 100.0,
        "matchType": "EXACT",
        "normalizationType": "ALPHANUMERIC",
        "category": "strong_identifier",
    },
    {
        "patterns": (
            "mail",
            "email",
            "emailaddress",
            "workemail",
            "primaryemail",
            "userprincipalname",
            "upn",
        ),
        "score": 90.0,
        "matchType": "EXACT",
        "normalizationType": "EMAIL",
        "category": "email_identifier",
    },
    {
        "patterns": (
            "samaccountname",
            "username",
            "userid",
            "loginid",
            "loginname",
            "uid",
            "accountname",
        ),
        "score": 75.0,
        "matchType": "FUZZY",
        "normalizationType": "LOWERCASE",
        "category": "account_identifier",
    },
    {
        "patterns": (
            "phone",
            "phonenumber",
            "telephone",
            "telephonenumber",
            "mobile",
            "mobilephone",
        ),
        "score": 65.0,
        "matchType": "EXACT",
        "normalizationType": "PHONE",
        "category": "contact_identifier",
    },
    {
        "patterns": (
            "firstname",
            "givenname",
            "preferredname",
        ),
        "score": 45.0,
        "matchType": "FUZZY",
        "normalizationType": "NAME",
        "category": "name",
    },
    {
        "patterns": (
            "lastname",
            "surname",
            "familyname",
            "sn",
        ),
        "score": 45.0,
        "matchType": "FUZZY",
        "normalizationType": "NAME",
        "category": "name",
    },
    {
        "patterns": (
            "displayname",
            "fullname",
            "commonname",
            "cn",
        ),
        "score": 35.0,
        "matchType": "FUZZY",
        "normalizationType": "NAME",
        "category": "display_name",
    },
    {
        "patterns": (
            "department",
            "departmentcode",
            "businessunit",
            "orgunit",
        ),
        "score": 20.0,
        "matchType": "EXACT",
        "normalizationType": "LOWERCASE",
        "category": "supporting",
    },
    {
        "patterns": (
            "manager",
            "managerid",
            "managername",
        ),
        "score": 15.0,
        "matchType": "EXACT",
        "normalizationType": "LOWERCASE",
        "category": "supporting",
    },
    {
        "patterns": (
            "location",
            "office",
            "site",
            "country",
        ),
        "score": 12.0,
        "matchType": "EXACT",
        "normalizationType": "LOWERCASE",
        "category": "supporting",
    },
]


def normalize_attribute_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _is_ignored(name: str) -> bool:
    normalized = normalize_attribute_name(name)
    return normalized in TECHNICAL_IGNORE_PATTERNS or any(
        normalized == pattern
        for pattern in TECHNICAL_IGNORE_PATTERNS
    )


def _semantic_rule(name: str) -> dict[str, Any] | None:
    normalized = normalize_attribute_name(name)
    for rule in SEMANTIC_RULES:
        if normalized in rule["patterns"]:
            return rule
    return None


def _round_weights(candidates: list[dict[str, Any]]) -> None:
    total_score = sum(float(item["score"]) for item in candidates)
    if total_score <= 0:
        return

    running = 0.0
    for index, candidate in enumerate(candidates):
        if index == len(candidates) - 1:
            weight = round(100.0 - running, 2)
        else:
            weight = round((float(candidate["score"]) / total_score) * 100.0, 2)
            running += weight
        candidate["matchWeight"] = weight


def generate_matching_policy(
    attributes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate an application-scoped duplicate matching policy.

    This first version uses schema semantics only. It intentionally avoids
    source-unique technical identifiers such as objectGUID/DN because two
    duplicate accounts normally have different values for those fields.
    Later account profiling can refine these defaults using coverage and
    uniqueness statistics without changing the API contract.
    """

    candidates: list[dict[str, Any]] = []
    ignored: list[str] = []

    for index, attribute in enumerate(attributes):
        name = str(attribute.get("name") or "").strip()
        if not name:
            continue

        if _is_ignored(name):
            ignored.append(name)
            continue

        rule = _semantic_rule(name)
        if rule is None:
            continue

        candidates.append(
            {
                "index": index,
                "name": name,
                "score": float(rule["score"]),
                "matchType": rule["matchType"],
                "normalizationType": rule["normalizationType"],
                "category": rule["category"],
                "reason": f"Recognized as {rule['category'].replace('_', ' ')}.",
            }
        )

    # Keep the strategy focused. Strong semantic signals are preferable to
    # enabling every field and introducing noise into the confidence score.
    candidates.sort(key=lambda item: (-float(item["score"]), item["index"]))
    candidates = candidates[:6]

    if not candidates:
        # Safe fallback for uncommon/custom applications: use a small number
        # of scalar string-like attributes instead of forcing manual setup.
        for index, attribute in enumerate(attributes):
            name = str(attribute.get("name") or "").strip()
            data_type = str(attribute.get("dataType") or "string").lower()
            multi_valued = bool(attribute.get("multiValued", False))
            if (
                not name
                or _is_ignored(name)
                or multi_valued
                or data_type not in {"string", "number"}
            ):
                continue
            candidates.append(
                {
                    "index": index,
                    "name": name,
                    "score": 1.0,
                    "matchType": "EXACT",
                    "normalizationType": "TRIM",
                    "category": "generic",
                    "reason": "Selected as a safe scalar fallback attribute.",
                }
            )
            if len(candidates) >= 4:
                break

    _round_weights(candidates)
    candidate_by_index = {int(item["index"]): item for item in candidates}

    policy_attributes: list[dict[str, Any]] = []
    for index, attribute in enumerate(attributes):
        candidate = candidate_by_index.get(index)
        updated = dict(attribute)
        if candidate is None:
            updated.update(
                {
                    "useForMatching": False,
                    "matchType": "NONE",
                    "matchWeight": 0.0,
                    "normalizationType": "NONE",
                }
            )
        else:
            updated.update(
                {
                    "useForMatching": True,
                    "matchType": candidate["matchType"],
                    "matchWeight": candidate["matchWeight"],
                    "normalizationType": candidate["normalizationType"],
                }
            )
        policy_attributes.append(updated)

    selected = [
        {
            "name": item["name"],
            "category": item["category"],
            "matchType": item["matchType"],
            "matchWeight": item.get("matchWeight", 0.0),
            "normalizationType": item["normalizationType"],
            "reason": item["reason"],
        }
        for item in candidates
    ]

    return {
        "strategy": "AUTOMATIC",
        "generatorVersion": "schema-heuristic-v1",
        "recommendedThreshold": 85.0,
        "selectedAttributeCount": len(selected),
        "selectedAttributes": selected,
        "ignoredTechnicalAttributes": ignored,
        "attributes": policy_attributes,
    }
