from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
	first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
	last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
	phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
	is_admin: Mapped[bool] = mapped_column(default=False)


