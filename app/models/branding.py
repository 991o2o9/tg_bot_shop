from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class Branding(Base):
	__tablename__ = "branding"

	# singleton row with id=1
	id: Mapped[int] = mapped_column(primary_key=True)
	logo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
	welcome_text: Mapped[str | None]


