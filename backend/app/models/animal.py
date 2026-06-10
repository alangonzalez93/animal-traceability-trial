import uuid
from datetime import date

import sqlalchemy as sa
from sqlalchemy import Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base_model import AuditMixin
from app.models.enums import AnimalCategory, AnimalStatus, Breed


class Animal(AuditMixin, Base):
    __tablename__ = "animals"

    tag_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    breed: Mapped[Breed] = mapped_column(Enum(Breed, name="breed"), nullable=False)
    category: Mapped[AnimalCategory] = mapped_column(Enum(AnimalCategory, name="animal_category"), nullable=False)
    status: Mapped[AnimalStatus] = mapped_column(
        Enum(AnimalStatus, name="animal_status"), nullable=False, default=AnimalStatus.ACTIVE
    )
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_lot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lots.id"), nullable=True)

    current_lot: Mapped["Lot | None"] = relationship("Lot", back_populates="animals")  # noqa: F821
    events: Mapped[list["Event"]] = relationship("Event", back_populates="animal")  # noqa: F821
    lot_periods: Mapped[list["AnimalLotPeriod"]] = relationship("AnimalLotPeriod", back_populates="animal")  # noqa: F821

    __table_args__ = (
        Index(
            "idx_animals_current_lot",
            "current_lot_id",
            postgresql_where=sa.text("deleted = false AND status = 'ACTIVE'"),
        ),
    )
