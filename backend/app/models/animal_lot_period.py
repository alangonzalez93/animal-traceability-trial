import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AnimalLotPeriod(Base):
    __tablename__ = "animal_lot_periods"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=sa.text("gen_random_uuid()")
    )
    animal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("animals.id"), nullable=False)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lots.id"), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    animal: Mapped["Animal"] = relationship("Animal", back_populates="lot_periods")  # noqa: F821
    lot: Mapped["Lot"] = relationship("Lot", back_populates="periods")  # noqa: F821

    __table_args__ = (
        Index(
            "idx_animal_lot_periods_single_open",
            "animal_id",
            unique=True,
            postgresql_where=sa.text("exited_at IS NULL"),
        ),
        Index("idx_animal_lot_periods_by_animal", "animal_id", "entered_at"),
        Index("idx_animal_lot_periods_by_lot", "lot_id", "entered_at", "exited_at"),
    )
