import enum
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Text, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base

class ChannelType(str, enum.Enum):
    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"
    instagram = "instagram"

class ConsentPurpose(str, enum.Enum):
    promotions = "promotions"
    transactional = "transactional"
    loyalty = "loyalty"
    timeline = "timeline"

class ConsentStatus(str, enum.Enum):
    granted = "granted"
    revoked = "revoked"

class OutboxStatus(str, enum.Enum):
    queued = "queued"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"
    blocked_by_consent = "blocked_by_consent"

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=True)
    country = Column(Text, nullable=False, default="AR")
    source = Column(Text, nullable=False, default="qr")
    status = Column(Text, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    identities = relationship("CustomerIdentity", back_populates="customer", cascade="all, delete-orphan")
    consents = relationship("Consent", back_populates="customer", cascade="all, delete-orphan")

class CustomerIdentity(Base):
    __tablename__ = "customer_identities"

    id = Column(UUID(as_uuid=True), primary_key=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    channel = Column(Enum(ChannelType, name="channel_type"), nullable=False)
    value = Column(Text, nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    customer = relationship("Customer", back_populates="identities")

class Consent(Base):
    __tablename__ = "consents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    channel = Column(Enum(ChannelType, name="channel_type"), nullable=False)
    purpose = Column(Enum(ConsentPurpose, name="consent_purpose"), nullable=False)
    status = Column(Enum(ConsentStatus, name="consent_status"), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    proof = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    customer = relationship("Customer", back_populates="consents")
