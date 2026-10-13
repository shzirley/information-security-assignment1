from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Algorithm = Literal['AES', 'RC4', 'DES']
Category = Literal['identity', 'document', 'video']
class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')
class Credentials(Model):
    username: str = Field(pattern=r'^[a-zA-Z0-9_]{3,24}$')
    password: str = Field(min_length=1, max_length=128)
class Registration(Credentials):
    password: str = Field(min_length=8, max_length=128)
class PersonalFields(Model):
    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(default='', max_length=254)
    phone: str = Field(default='', max_length=24)
    address: str = Field(default='', max_length=500)
    date_of_birth: str = Field(default='', max_length=10)
    identity_number: str = Field(default='', max_length=64)

    @field_validator('full_name')
    @classmethod
    def name(cls, value):
        if not value.strip():
            raise ValueError('Nama lengkap wajib diisi.')
        return value.strip()
    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        if value and ('@' not in value or '.' not in value.split('@')[-1] or any(c.isspace() for c in value)):
            raise ValueError('Format email tidak valid.')
        return value
    @field_validator('date_of_birth')
    @classmethod
    def date_valid(cls, value):
        if value:
            date.fromisoformat(value)
        return value
class Decrypt(Model):
    algorithm: Algorithm
class Source(Model):
    type: Literal['file', 'personal_data']
    id: str = Field(min_length=1, max_length=36)
class BenchmarkInput(Model):
    source: Source
    repetitions: int = Field(ge=10, le=30, strict=True)
    warmups: Literal[2] = 2
class DownloadInput(Model):
    file_id: str = Field(min_length=1, max_length=36)
    repetitions: int = Field(ge=10, le=30, strict=True)
class Attempt(Model):
    algorithm: Algorithm
    repetition: int = Field(ge=1, le=30, strict=True)
    elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    received_bytes: int = Field(ge=0, le=25_000_000, strict=True)
    success: bool
    error_code: str | None = Field(default=None, max_length=100)
class DownloadResults(Model):
    attempts: list[Attempt] = Field(max_length=90)
    browser: str = Field(default='', max_length=1000)
