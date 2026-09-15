import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.database.base import Base
from app.services.settings_service import (
    DEFAULT_BRANDING_BACKGROUND,
    DEFAULT_BRANDING_NAVIGATION,
    DEFAULT_BRANDING_PRIMARY,
    DEFAULT_BRANDING_SECONDARY,
    branding_response,
    reset_branding_palette,
    update_branding_palette,
)


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_branding_response_uses_platform_defaults_before_configuration():
    with _session() as db:
        response = branding_response(db)
        assert response["primaryColor"] == DEFAULT_BRANDING_PRIMARY
        assert response["secondaryColor"] == DEFAULT_BRANDING_SECONDARY
        assert response["navigationColor"] == DEFAULT_BRANDING_NAVIGATION
        assert response["backgroundColor"] == DEFAULT_BRANDING_BACKGROUND


def test_branding_palette_is_persisted_and_normalized():
    with _session() as db:
        update_branding_palette(
            db,
            primary_color="#1122aa",
            secondary_color="#bb33cc",
            navigation_color="#101820",
            background_color="#f7f8f9",
        )
        response = branding_response(db)
        assert response["primaryColor"] == "#1122AA"
        assert response["secondaryColor"] == "#BB33CC"
        assert response["navigationColor"] == "#101820"
        assert response["backgroundColor"] == "#F7F8F9"


def test_branding_palette_rejects_invalid_color():
    with _session() as db:
        with pytest.raises(ValueError, match="six-digit hex color"):
            update_branding_palette(
                db,
                primary_color="blue",
                secondary_color="#1976D2",
                navigation_color="#0F172A",
                background_color="#F5F7FA",
            )


def test_branding_palette_can_be_reset():
    with _session() as db:
        update_branding_palette(
            db,
            primary_color="#112233",
            secondary_color="#223344",
            navigation_color="#334455",
            background_color="#445566",
        )
        reset_branding_palette(db)
        response = branding_response(db)
        assert response["primaryColor"] == DEFAULT_BRANDING_PRIMARY
        assert response["secondaryColor"] == DEFAULT_BRANDING_SECONDARY
        assert response["navigationColor"] == DEFAULT_BRANDING_NAVIGATION
        assert response["backgroundColor"] == DEFAULT_BRANDING_BACKGROUND
