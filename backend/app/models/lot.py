import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base_model import AuditMixin


class Lot(AuditMixin, Base):
    __tablename__ = "lots"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fields.id"), nullable=False)

    field: Mapped["Field"] = relationship("Field", back_populates="lots")  # noqa: F821
    animals: Mapped[list["Animal"]] = relationship("Animal", back_populates="current_lot")  # noqa: F821
    periods: Mapped[list["AnimalLotPeriod"]] = relationship("AnimalLotPeriod", back_populates="lot")  # noqa: F821
