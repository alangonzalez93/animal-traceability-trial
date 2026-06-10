from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base_model import AuditMixin


class Field(AuditMixin, Base):
    __tablename__ = "fields"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    lots: Mapped[list["Lot"]] = relationship("Lot", back_populates="field")  # noqa: F821
