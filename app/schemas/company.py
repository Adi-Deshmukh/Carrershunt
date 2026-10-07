from pydantic import BaseModel, Field, HttpUrl


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    careers_url: HttpUrl


class CompanyRead(CompanyCreate):
    id: int
    platform: str | None = None
    active: bool = True
