import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EventType


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=sa.text("gen_random_uuid()")
    )
    animal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("animals.id"), nullable=False)
    type: Mapped[EventType] = mapped_column(Enum(EventType, name="event_type"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    animal: Mapped["Animal"] = relationship("Animal", back_populates="events")  # noqa: F821

    __table_args__ = (
        CheckConstraint(
            "type IN ('BIRTH','MOVE','DEATH','SALE','RECLASSIFICATION','WEIGHT','VACCINATION')",
            name="chk_events_type",
        ),
        CheckConstraint(
            "type != 'MOVE' OR (jsonb_exists(payload,'from_lot_id') AND jsonb_exists(payload,'to_lot_id'))",
            name="chk_events_move",
        ),
        CheckConstraint(
            "type != 'WEIGHT' OR jsonb_exists(payload,'weight_kg')",
            name="chk_events_weight",
        ),
        CheckConstraint(
            "type != 'VACCINATION' OR jsonb_exists(payload,'vaccine_name')",
            name="chk_events_vaccination",
        ),
        CheckConstraint(
            "type != 'RECLASSIFICATION' OR jsonb_exists(payload,'new_category')",
            name="chk_events_reclassification",
        ),
        Index("idx_events_by_animal", "animal_id", "occurred_at"),
        # CAST() is used here instead of :: to avoid asyncpg prepared-statement parsing issues.
        # PostgreSQL normalizes both to the same expression, so queries using ::numeric will still hit this index.
        Index(
            "idx_events_weight",
            sa.text("CAST(payload->>'weight_kg' AS numeric)"),
            postgresql_where=sa.text("type = 'WEIGHT'"),
        ),
        Index("idx_events_vaccination", "animal_id", postgresql_where=sa.text("type = 'VACCINATION'")),
        Index("idx_events_move", "animal_id", postgresql_where=sa.text("type = 'MOVE'")),
        Index("idx_events_weight_adg", "animal_id", "occurred_at", postgresql_where=sa.text("type = 'WEIGHT'")),
    )
