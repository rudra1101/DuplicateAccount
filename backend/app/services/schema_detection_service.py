from __future__ import annotations

import csv
import io
from typing import Any

from app.connectors.factory import ConnectorFactory


def _infer_type(values: list[str]) -> str:
    cleaned = [value.strip() for value in values if value is not None and value.strip() != ""]
    if not cleaned:
        return "string"

    lowered = {value.lower() for value in cleaned}
    if lowered.issubset({"true", "false", "yes", "no", "0", "1"}):
        return "boolean"

    try:
        for value in cleaned:
            int(value)
        return "number"
    except ValueError:
        pass

    try:
        for value in cleaned:
            float(value)
        return "number"
    except ValueError:
        return "string"


def detect_delimited_schema(
    *,
    connector_type: str,
    configuration: dict[str, Any],
    sample_size: int = 100,
) -> dict[str, Any]:
    connector = ConnectorFactory.create(
        connector_type=connector_type,
        configuration=configuration,
    )

    with connector:
        connector_file = connector.fetch_file()

    delimiter = str(configuration.get("delimiter", ","))
    if delimiter == "\\t":
        delimiter = "\t"

    encoding = str(configuration.get("encoding", "utf-8-sig"))
    text = connector_file.content.decode(encoding, errors="replace")

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("The selected CSV file does not contain a header row.")

    headers = [str(name).strip() for name in reader.fieldnames if name and str(name).strip()]
    if not headers:
        raise ValueError("The selected CSV file does not contain usable column names.")

    samples: dict[str, list[str]] = {header: [] for header in headers}
    row_count = 0

    for row in reader:
        row_count += 1
        for header in headers:
            value = row.get(header)
            if value is not None:
                samples[header].append(str(value))
        if row_count >= sample_size:
            break

    attributes = []
    for position, header in enumerate(headers):
        values = samples.get(header, [])
        non_empty = [value for value in values if value.strip() != ""]
        required = bool(values) and len(non_empty) == len(values)
        attributes.append(
            {
                "name": header,
                "displayName": header,
                "dataType": _infer_type(values),
                "required": required,
                "multiValued": False,
                "position": position,
                "useForMatching": False,
                "matchType": "NONE",
                "matchWeight": 0,
                "normalizationType": "NONE",
            }
        )

    return {
        "filename": connector_file.filename,
        "sourcePath": connector_file.source_path,
        "sampledRows": row_count,
        "attributes": attributes,
    }
