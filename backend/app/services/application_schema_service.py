from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db_models.application import ApplicationRecord
from app.db_models.application_schema import ApplicationSchemaRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.schema_attribute import SchemaAttributeRecord
from app.schemas.application_schema import IntegrationApplicationsPayload
from app.services.matching_policy_service import generate_matching_policy


def _attribute_to_dict(attribute: SchemaAttributeRecord) -> dict:
    return {
        "id": attribute.id,
        "name": attribute.name,
        "displayName": attribute.display_name,
        "dataType": attribute.data_type,
        "required": attribute.required,
        "multiValued": attribute.multi_valued,
        "position": attribute.position,
        # Internal duplicate-detection settings are returned for backend/admin
        # compatibility, but the integration UI no longer exposes them.
        "useForMatching": attribute.use_for_matching,
        "matchType": attribute.match_type,
        "matchWeight": attribute.match_weight,
        "normalizationType": attribute.normalization_type,
    }


def _application_to_dict(application: ApplicationRecord) -> dict:
    active_schema = next(
        (schema for schema in application.schemas if schema.is_active),
        application.schemas[0] if application.schemas else None,
    )
    return {
        "id": application.id,
        "integrationId": application.integration_id,
        "name": application.name,
        "displayName": application.display_name,
        "objectType": application.object_type,
        "enabled": application.enabled,
        "schema": (
            {
                "id": active_schema.id,
                "version": active_schema.version,
                "name": active_schema.name,
                "isActive": active_schema.is_active,
                "attributes": [
                    _attribute_to_dict(attribute)
                    for attribute in active_schema.attributes
                ],
            }
            if active_schema is not None
            else None
        ),
    }


def get_applications_for_integration(
    db: Session,
    integration_id: int,
) -> list[dict]:
    applications = list(
        db.scalars(
            select(ApplicationRecord)
            .options(
                selectinload(ApplicationRecord.schemas)
                .selectinload(ApplicationSchemaRecord.attributes)
            )
            .where(ApplicationRecord.integration_id == integration_id)
            .order_by(ApplicationRecord.name.asc())
        ).all()
    )
    return [_application_to_dict(item) for item in applications]


def _schema_input_for_policy(app_input) -> list[dict]:
    """Convert an application schema into the policy engine's input shape.

    Matching fields received from the client are intentionally ignored. The
    backend owns selection, comparison method, normalization and weighting.
    """
    return [
        {
            "name": attribute.name,
            "displayName": attribute.displayName,
            "dataType": attribute.dataType,
            "required": attribute.required,
            "multiValued": attribute.multiValued,
            "position": attribute.position if attribute.position is not None else index,
        }
        for index, attribute in enumerate(app_input.attributes)
    ]


def replace_integration_applications(
    db: Session,
    integration: IntegrationRecord,
    payload: IntegrationApplicationsPayload,
) -> list[dict]:
    existing = list(
        db.scalars(
            select(ApplicationRecord)
            .where(ApplicationRecord.integration_id == integration.id)
        ).all()
    )
    for item in existing:
        db.delete(item)
    db.flush()

    for app_input in payload.applications:
        application = ApplicationRecord(
            integration_id=integration.id,
            name=app_input.name,
            display_name=app_input.displayName,
            object_type=app_input.objectType,
            enabled=app_input.enabled,
        )
        db.add(application)
        db.flush()

        schema = ApplicationSchemaRecord(
            application_id=application.id,
            version=1,
            name=app_input.schemaName or f"{app_input.name} schema",
            is_active=True,
        )
        db.add(schema)
        db.flush()

        # Internal policy generation happens automatically. The application
        # integrator supplies only the source schema; no manual weights or
        # comparison rules are required from the UI.
        policy = generate_matching_policy(_schema_input_for_policy(app_input))
        policy_attributes = policy.get("attributes", [])

        for position, attribute_input in enumerate(app_input.attributes):
            generated = (
                policy_attributes[position]
                if position < len(policy_attributes)
                else {}
            )

            attribute = SchemaAttributeRecord(
                schema_id=schema.id,
                name=attribute_input.name,
                display_name=attribute_input.displayName,
                data_type=attribute_input.dataType,
                required=attribute_input.required,
                multi_valued=attribute_input.multiValued,
                position=(
                    attribute_input.position
                    if attribute_input.position is not None
                    else position
                ),
                use_for_matching=bool(generated.get("useForMatching", False)),
                match_type=str(generated.get("matchType") or "NONE"),
                match_weight=float(generated.get("matchWeight") or 0.0),
                normalization_type=str(
                    generated.get("normalizationType") or "NONE"
                ),
            )
            db.add(attribute)

    db.commit()
    return get_applications_for_integration(db, integration.id)
