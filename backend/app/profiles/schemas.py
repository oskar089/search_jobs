from pydantic import BaseModel


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    target_roles: list[str] = []
    tech_stack: list[str] = []
    experience_level: str
    min_salary: int | None = None
    max_salary: int | None = None
    locations: list[str] = []
    remote_only: bool = False
    languages: list[str] = []
    is_active: bool = True

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    target_roles: list[str] | None = None
    tech_stack: list[str] | None = None
    experience_level: str | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    locations: list[str] | None = None
    remote_only: bool | None = None
    languages: list[str] | None = None
    is_active: bool | None = None
