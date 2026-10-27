import re
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal['applicant', 'reviewer', 'admin', 'evaluator']
Category = Literal['identity', 'document', 'video']
class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
class Credentials(Model):
    username: str = Field(pattern=r'^[a-zA-Z0-9_]{3,24}$')
    password: str = Field(min_length=1, max_length=128)
    @field_validator('password', mode='before')
    @classmethod
    def retain_password(cls, value):
        # Password whitespace is significant; override string trimming below.
        return value
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
class Registration(Credentials):
    password: str = Field(min_length=8, max_length=128)
class Profile(Model):
    full_name: str = Field(min_length=1, max_length=500)
    identity_number: str = Field(min_length=1, max_length=500)
    date_of_birth: str = Field(min_length=1, max_length=500)
    email: str = Field(min_length=1, max_length=500)
    phone: str = Field(min_length=1, max_length=500)
    address: str = Field(min_length=1, max_length=500)
    occupation: str = Field(min_length=1, max_length=500)
    account_purpose: str = Field(min_length=1, max_length=500)
    @field_validator('identity_number')
    @classmethod
    def identity(cls, value):
        if not re.fullmatch(r'DUMMY-[A-Z0-9-]{3,40}', value, re.I):
            raise ValueError('Gunakan nomor identitas berawalan DUMMY-.')
        return value
    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        if not re.fullmatch(r'[^@\s]+@example\.(com|org|net)', value):
            raise ValueError('Gunakan email @example.com/org/net.')
        return value
    @field_validator('phone')
    @classmethod
    def phone_valid(cls, value):
        if not re.fullmatch(r'0800\d{6,10}', value):
            raise ValueError('Gunakan nomor dummy 0800 dengan 10–14 digit.')
        return value
    @field_validator('date_of_birth')
    @classmethod
    def birth_valid(cls, value):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) or date.fromisoformat(value) >= date.today():
            raise ValueError('Tanggal harus valid dan di masa lalu.')
        return value
class Versioned(Model):
    version: int = Field(ge=1, strict=True)
class SaveProfile(Versioned):
    profile: Profile
class Action(Versioned):
    action: Literal['submit', 'resubmit', 'withdraw', 'start-review', 'request-revision', 'accept', 'reject']
    note: str | None = Field(default=None, max_length=500)
    synthetic_acknowledged: bool | None = Field(default=None, strict=True)
class Assignment(Versioned):
    reviewer_id: str = Field(min_length=1, max_length=36)
class LabInput(Model):
    kind: Literal['benchmark', 'verification']
    fixture: Literal['personal-json', 'identity-png', 'document-pdf', 'video-mp4']
    repetitions: int = Field(default=30, ge=30, le=100, strict=True)
    warmups: Literal[2] = 2
