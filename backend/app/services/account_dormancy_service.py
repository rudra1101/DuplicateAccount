from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.db_models.integration import IntegrationRecord
from app.db_models.source_account import SourceAccountRecord


DORMANCY_MAPPING_CONFIG_KEY = "accountDormancyMappings"

DATE_FORMAT_AUTO = "AUTO"
DATE_FORMAT_ISO_8601 = "ISO_8601"
DATE_FORMAT_UNIX_SECONDS = "UNIX_SECONDS"
DATE_FORMAT_UNIX_MILLISECONDS = "UNIX_MILLISECONDS"
DATE_FORMAT_UNIX_MICROSECONDS = "UNIX_MICROSECONDS"
DATE_FORMAT_UNIX_NANOSECONDS = "UNIX_NANOSECONDS"
DATE_FORMAT_WINDOWS_FILETIME = "WINDOWS_FILETIME"
DATE_FORMAT_CUSTOM = "CUSTOM"

SUPPORTED_DATE_FORMATS = {
    DATE_FORMAT_AUTO,
    DATE_FORMAT_ISO_8601,
    DATE_FORMAT_UNIX_SECONDS,
    DATE_FORMAT_UNIX_MILLISECONDS,
    DATE_FORMAT_UNIX_MICROSECONDS,
    DATE_FORMAT_UNIX_NANOSECONDS,
    DATE_FORMAT_WINDOWS_FILETIME,
    DATE_FORMAT_CUSTOM,
}


@dataclass(frozen=True)
class DormancyConfig:
    attribute: str
    date_format: str
    custom_format: str | None
    threshold_days: int


def _normalize_mapping_name(value: str) -> str:
    return value.strip().casefold()


def dormancy_mappings(configuration: dict[str, Any] | None) -> dict[str, DormancyConfig]:
    raw = (configuration or {}).get(DORMANCY_MAPPING_CONFIG_KEY)
    if not isinstance(raw, dict):
        return {}

    result: dict[str, DormancyConfig] = {}
    for application_name, mapping in raw.items():
        if not isinstance(mapping, dict):
            continue
        attribute = str(mapping.get("attribute") or "").strip()
        if not attribute:
            continue
        date_format = str(mapping.get("dateFormat") or DATE_FORMAT_AUTO).strip().upper()
        if date_format not in SUPPORTED_DATE_FORMATS:
            date_format = DATE_FORMAT_AUTO
        custom_format = str(mapping.get("customFormat") or "").strip() or None
        try:
            threshold_days = int(mapping.get("thresholdDays") or 0)
        except (TypeError, ValueError):
            threshold_days = 0
        if threshold_days <= 0:
            continue
        result[_normalize_mapping_name(str(application_name))] = DormancyConfig(
            attribute=attribute,
            date_format=date_format,
            custom_format=custom_format,
            threshold_days=threshold_days,
        )
    return result


def dormancy_config_for_application(
    configuration: dict[str, Any] | None,
    application_name: str,
) -> DormancyConfig | None:
    return dormancy_mappings(configuration).get(_normalize_mapping_name(application_name))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _numeric_timestamp(value: float, date_format: str) -> datetime:
    if date_format == DATE_FORMAT_UNIX_SECONDS:
        seconds = value
    elif date_format == DATE_FORMAT_UNIX_MILLISECONDS:
        seconds = value / 1_000
    elif date_format == DATE_FORMAT_UNIX_MICROSECONDS:
        seconds = value / 1_000_000
    elif date_format == DATE_FORMAT_UNIX_NANOSECONDS:
        seconds = value / 1_000_000_000
    elif date_format == DATE_FORMAT_WINDOWS_FILETIME:
        seconds = (value - 116_444_736_000_000_000) / 10_000_000
    else:
        absolute = abs(value)
        if absolute >= 1_000_000_000_000_000_000:
            seconds = value / 1_000_000_000
        elif 10_000_000_000_000_000 <= absolute < 1_000_000_000_000_000_000:
            # Windows FILETIME is commonly around 1.3e17 for modern dates.
            seconds = (value - 116_444_736_000_000_000) / 10_000_000
        elif absolute >= 100_000_000_000_000:
            seconds = value / 1_000_000
        elif absolute >= 100_000_000_000:
            seconds = value / 1_000
        else:
            seconds = value
    return datetime.fromtimestamp(seconds, tz=UTC)


def _translate_custom_format(value: str) -> str:
    if "%" in value:
        return value

    replacements = (
        ("yyyy", "%Y"),
        ("yyy", "%Y"),
        ("yy", "%y"),
        ("fff", "%f"),
        ("MM", "%m"),
        ("dd", "%d"),
        ("HH", "%H"),
        ("hh", "%I"),
        ("mm", "%M"),
        ("ss", "%S"),
        ("tt", "%p"),
        ("zzz", "%z"),
    )
    translated = value
    for source, target in replacements:
        translated = translated.replace(source, target)
    return translated


def parse_last_login(
    value: Any,
    *,
    date_format: str = DATE_FORMAT_AUTO,
    custom_format: str | None = None,
) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None

    normalized_format = str(date_format or DATE_FORMAT_AUTO).strip().upper()
    if normalized_format not in SUPPORTED_DATE_FORMATS:
        raise ValueError(f"Unsupported last-login date format: {date_format}")

    if isinstance(value, datetime):
        return _as_utc(value)

    text = str(value).strip()
    if not text:
        return None

    try:
        if normalized_format in {
            DATE_FORMAT_UNIX_SECONDS,
            DATE_FORMAT_UNIX_MILLISECONDS,
            DATE_FORMAT_UNIX_MICROSECONDS,
            DATE_FORMAT_UNIX_NANOSECONDS,
            DATE_FORMAT_WINDOWS_FILETIME,
        }:
            return _numeric_timestamp(float(text), normalized_format)

        if normalized_format == DATE_FORMAT_CUSTOM:
            if not custom_format:
                raise ValueError("A custom last-login date format is required.")
            return _as_utc(datetime.strptime(text, _translate_custom_format(custom_format)))

        if normalized_format == DATE_FORMAT_ISO_8601:
            return _as_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))

        # AUTO: recognize compact calendar values before treating a numeric
        # string as an epoch. This prevents values such as 20240101 from
        # becoming a date in 1970.
        compact_formats = {
            8: "%Y%m%d",
            14: "%Y%m%d%H%M%S",
        }
        if text.isdigit() and len(text) in compact_formats:
            try:
                return _as_utc(datetime.strptime(text, compact_formats[len(text)]))
            except ValueError:
                pass

        # Infer numeric epoch/filetime, then ISO/common source formats.
        try:
            return _numeric_timestamp(float(text), DATE_FORMAT_AUTO)
        except (TypeError, ValueError, OverflowError, OSError):
            pass

        try:
            return _as_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            pass

        for candidate in (
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
            "%Y%m%d%H%M%S",
        ):
            try:
                return _as_utc(datetime.strptime(text, candidate))
            except ValueError:
                continue
    except (ValueError, OverflowError, OSError):
        return None

    return None


def extract_last_login(raw_attributes: dict[str, Any], config: DormancyConfig | None) -> datetime | None:
    if config is None:
        return None
    target = config.attribute.casefold()
    value = None
    for key, candidate in raw_attributes.items():
        if str(key).casefold() == target:
            value = candidate
            break
    return parse_last_login(
        value,
        date_format=config.date_format,
        custom_format=config.custom_format,
    )


def inactive_days(last_login_at: datetime | None, *, now: datetime | None = None) -> int | None:
    if last_login_at is None:
        return None
    reference = _as_utc(now or datetime.now(UTC))
    login = _as_utc(last_login_at)
    return max(0, int((reference - login).total_seconds() // 86400))


def is_dormant(
    account: SourceAccountRecord,
    config: DormancyConfig | None,
    *,
    now: datetime | None = None,
) -> bool:
    if config is None or account.last_login_at is None or not account.active or account.deleted:
        return False
    if (account.status or "").strip().upper() == "INACTIVE":
        return False
    days = inactive_days(account.last_login_at, now=now)
    return days is not None and days >= config.threshold_days


def dormant_account_filter(configuration: dict[str, Any] | None, *, now: datetime | None = None):
    mappings = dormancy_mappings(configuration)
    if not mappings:
        return None

    reference = _as_utc(now or datetime.now(UTC))
    clauses = []
    for application_name, config in mappings.items():
        cutoff = reference - timedelta(days=config.threshold_days)
        clauses.append(
            and_(
                func.lower(SourceAccountRecord.application) == application_name,
                SourceAccountRecord.last_login_at.is_not(None),
                SourceAccountRecord.last_login_at <= cutoff,
                func.upper(func.coalesce(SourceAccountRecord.status, "UNKNOWN")) != "INACTIVE",
            )
        )
    return or_(*clauses) if clauses else None


def recalculate_last_login_for_integration(db: Session, integration_id: int) -> int:
    integration = db.get(IntegrationRecord, integration_id)
    if integration is None:
        return 0
    mappings = dormancy_mappings(integration.configuration)
    rows = list(
        db.scalars(
            select(SourceAccountRecord).where(SourceAccountRecord.integration_id == integration_id)
        ).all()
    )
    changed = 0
    for account in rows:
        config = mappings.get(_normalize_mapping_name(account.application))
        parsed = extract_last_login(account.raw_attributes or {}, config)
        if account.last_login_at != parsed:
            account.last_login_at = parsed
            changed += 1
    if changed:
        db.commit()
    return changed
