from pydantic import BaseModel, Field


class ConcernIn(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    category_id: int
    campus: str = ""
    location: str = ""
    urgency: int = Field(2, ge=1, le=4)
    safety_flag: bool = False
    students_affected: int = Field(1, ge=1, le=5000)
    is_public: bool = False


class TrackIn(BaseModel):
    reference: str
    access_code: str


class ConfirmIn(TrackIn):
    resolved: bool
    comment: str = ""


class AddInfoIn(TrackIn):
    message: str = Field(min_length=2, max_length=3000)


class AssignIn(BaseModel):
    delegate_id: int


class UpdateIn(BaseModel):
    message: str = Field(min_length=2, max_length=3000)
    visibility: str = "private"        # public | private | internal
    status: str | None = None          # in_progress | resolved


class UserIn(BaseModel):
    full_name: str
    email: str
    password: str = Field(min_length=8)
    role: str
    portfolio: str = ""
    categories_handled: str = ""
    max_open_load: int = 5
