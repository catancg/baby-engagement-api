from pydantic import BaseModel, Field, EmailStr
from typing import Literal, Optional, List

Channel = Literal["email", "instagram", "whatsapp", "sms"]
BabyStage = Literal["pregnant", "0_6m", "6_12m", "1_3y", "3y_plus"]

class SignupIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    channel: Channel
    value: str = Field(min_length=3, max_length=200)  # email/phone/ig handle
    baby_stage: Optional[BabyStage] = None
    consent_promotions: bool = True

class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    interests: List[str] = Field(default_factory=list)
    consent_promotions: bool = True

class SignupOut(BaseModel):
    customer_id: str
    identity_id: str
