from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=255)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class MeResponse(BaseModel):
    user: UserRead


class TokenExchangeRequest(BaseModel):
    token: str = Field(min_length=10, max_length=255)


class TokenCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=64)


class ApiTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiTokenWithSecret(ApiTokenRead):
    token: str


class TokenCreateResponse(BaseModel):
    token: ApiTokenWithSecret


class TokenListResponse(BaseModel):
    tokens: list[ApiTokenRead]
