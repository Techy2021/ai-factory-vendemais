from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class Lead(BaseModel):
    deal_id: str | None = Field(
        default=None, description="Identificador do negocio, quando disponivel."
    )
    company_name: str | None = None
    industry: str | None = None
    size_employees: str | None = None
    tech_stack: list[str] | None = Field(
        default=None,
        description="Tecnologias; texto de origem e preservado como um unico item.",
    )
    icp_match_score: (
        Annotated[int, Field(ge=0, le=100)]
        | Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
        | None
    ) = None
    enriched_at: datetime | None = None

    @field_validator("tech_stack", mode="before")
    @classmethod
    def normalize_tech_stack(cls, value: object) -> object:
        if isinstance(value, str):
            return [value]
        return value


class LeadsResponse(BaseModel):
    items: list[Lead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class MetricsResponse(BaseModel):
    leads_total: int = Field(ge=0)
    average_score: float | None = Field(default=None, ge=0, le=100)
    missing_score_count: int = Field(ge=0)
    unique_deals: int = Field(ge=0)


class ErrorResponse(BaseModel):
    code: str
    message: str
