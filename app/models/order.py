from datetime import datetime
from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Order(Base):
	__tablename__ = "orders"

	id: Mapped[int] = mapped_column(primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
	created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
	status: Mapped[str] = mapped_column(default="new")
	customer_name: Mapped[str | None]
	customer_phone: Mapped[str | None]

	items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
	__tablename__ = "order_items"

	id: Mapped[int] = mapped_column(primary_key=True)
	order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
	product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
	quantity: Mapped[int]
	unit_price: Mapped[float] = mapped_column(Numeric(10, 2))

	order: Mapped[Order] = relationship(back_populates="items")


