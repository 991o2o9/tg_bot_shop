from sqlalchemy import BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class Manager(Base):
	__tablename__ = "managers"
	__table_args__ = (
		UniqueConstraint("user_id", name="uq_managers_user_id"),
	)

	id: Mapped[int] = mapped_column(primary_key=True)
	user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


