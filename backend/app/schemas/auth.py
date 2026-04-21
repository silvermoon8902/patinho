from datetime import date, datetime, timezone

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    phone: str = Field(min_length=8, max_length=20)
    birth_date: date
    cpf: str | None = Field(default=None, max_length=14)
    accepted_terms: bool = Field(
        default=False,
        description="Must be true — user has read and accepted ToS + Privacy Policy",
    )
    age_acknowledged: bool = Field(
        default=False,
        description="Must be true — user confirms they are 18 years or older",
    )

    @field_validator("birth_date")
    @classmethod
    def validate_age(cls, v: date) -> date:
        today = datetime.now(timezone.utc).date()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Voce precisa ter pelo menos 18 anos para se cadastrar")
        return v

    @field_validator("accepted_terms")
    @classmethod
    def require_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Você precisa aceitar os Termos de Uso e a Política de Privacidade"
            )
        return v

    @field_validator("age_acknowledged")
    @classmethod
    def require_age_ack(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Você precisa confirmar que tem 18 anos ou mais"
            )
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
