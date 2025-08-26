from datetime import datetime
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class Review(Base):
	__tablename__ = "reviews"

	id: Mapped[int] = mapped_column(primary_key=True)
	media_type: Mapped[str] = mapped_column(String(16))  # 'photo' | 'video'
	file_id: Mapped[str] = mapped_column(String(256))
	caption: Mapped[str | None]
	created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


