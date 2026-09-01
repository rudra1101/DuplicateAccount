from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database.session import get_db
from app.services.email_service import send_email
from app.services.settings_service import (
    branding_response,
    clear_logo,
    get_application_settings,
    save_logo,
    smtp_settings_response,
    update_smtp_settings,
)


router = APIRouter(prefix="/settings", tags=["Settings"])

ALLOWED_LOGO_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_LOGO_BYTES = 2 * 1024 * 1024


class SmtpSettingsUpdate(BaseModel):
    enabled: bool = False
    host: str = ""
    port: int = Field(default=587, ge=1, le=65535)
    username: str = ""
    password: str | None = None
    fromEmail: str = ""
    useTls: bool = True
    clearPassword: bool = False


class SmtpTestRequest(BaseModel):
    recipient: EmailStr


@router.get(
    "/smtp",
    dependencies=[Depends(require_permission("settings.manage"))],
)
def get_smtp_settings(db: Session = Depends(get_db)):
    return smtp_settings_response(db)


@router.put(
    "/smtp",
    dependencies=[Depends(require_permission("settings.manage"))],
)
def put_smtp_settings(
    payload: SmtpSettingsUpdate,
    db: Session = Depends(get_db),
):
    try:
        update_smtp_settings(
            db,
            enabled=payload.enabled,
            host=payload.host,
            port=payload.port,
            username=payload.username,
            password=payload.password,
            from_email=payload.fromEmail,
            use_tls=payload.useTls,
            clear_password=payload.clearPassword,
        )
        return smtp_settings_response(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/smtp/test",
    dependencies=[Depends(require_permission("settings.manage"))],
)
def test_smtp_settings(payload: SmtpTestRequest):
    try:
        send_email(
            recipients=[str(payload.recipient)],
            subject="IdentityAI SMTP test",
            text_body=(
                "Your IdentityAI SMTP configuration is working correctly."
            ),
        )
        return {"sent": True}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"SMTP test failed: {exc}",
        ) from exc


@router.get("/branding")
def get_branding(db: Session = Depends(get_db)):
    return branding_response(db)


@router.get("/branding/logo")
def get_branding_logo(db: Session = Depends(get_db)):
    settings = get_application_settings(db)
    if settings is None or not settings.logo_data or not settings.logo_mime_type:
        raise HTTPException(status_code=404, detail="Custom logo is not configured.")

    return Response(
        content=settings.logo_data,
        media_type=settings.logo_mime_type,
        headers={"Cache-Control": "no-store"},
    )


@router.put(
    "/branding/logo",
    dependencies=[Depends(require_permission("settings.manage"))],
)
async def upload_branding_logo(
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    mime_type = str(logo.content_type or "").lower()
    if mime_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Logo must be PNG, JPEG, or WebP.",
        )

    data = await logo.read(MAX_LOGO_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Logo file is empty.")
    if len(data) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="Logo must be 2 MB or smaller.")

    save_logo(
        db,
        filename=logo.filename or "logo",
        mime_type=mime_type,
        data=data,
    )
    return branding_response(db)


@router.delete(
    "/branding/logo",
    dependencies=[Depends(require_permission("settings.manage"))],
)
def delete_branding_logo(db: Session = Depends(get_db)):
    clear_logo(db)
    return branding_response(db)
