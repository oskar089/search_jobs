from datetime import datetime

from pydantic import BaseModel


class PortalSelectors(BaseModel):
    """CSS/XPath selectors for each scraping field on a job portal."""

    job_card: str
    title: str
    company: str
    location: str | None = None
    description: str
    url: str
    salary: str | None = None
    posted_date: str | None = None
    apply_button: str | None = None


class PortalCreate(BaseModel):
    name: str
    base_url: str
    job_listing_url: str
    selectors: PortalSelectors
    scrape_interval_min: int = 60


class PortalUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    job_listing_url: str | None = None
    selectors: PortalSelectors | None = None
    is_enabled: bool | None = None
    scrape_interval_min: int | None = None


class PortalResponse(BaseModel):
    id: str
    name: str
    base_url: str
    job_listing_url: str
    selectors: dict
    is_builtin: bool
    is_enabled: bool
    is_verified: bool
    scrape_interval_min: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
