from pydantic import BaseModel, Field


class JobScheduleCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=255,
    )

    cronExpression: str = Field(
        min_length=5,
        max_length=100,
    )

    timezone: str = Field(
        default="Asia/Kolkata",
        min_length=2,
        max_length=100,
    )

    enabled: bool = True


class JobScheduleUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    cronExpression: str | None = Field(
        default=None,
        min_length=5,
        max_length=100,
    )

    timezone: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    enabled: bool | None = None