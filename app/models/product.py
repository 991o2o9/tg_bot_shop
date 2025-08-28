from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Category(Base):
	__tablename__ = "categories"

	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(128), unique=True)
	
	# Relationships
	products: Mapped[list["Product"]] = relationship("Product", back_populates="category")


class Product(Base):
	__tablename__ = "products"

	id: Mapped[int] = mapped_column(primary_key=True)
	title: Mapped[str] = mapped_column(String(255))
	description: Mapped[str | None] = mapped_column(Text())
	price: Mapped[float] = mapped_column(Numeric(10, 2))
	bulk_threshold: Mapped[int | None] = mapped_column(nullable=True)
	bulk_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
	stock_qty: Mapped[int] = mapped_column(default=0)
	in_stock: Mapped[bool] = mapped_column(default=True)
	is_deleted: Mapped[bool] = mapped_column(default=False)
	photo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
	category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
	
	# Relationships
	flavors: Mapped[list["Flavor"]] = relationship("Flavor", back_populates="product", cascade="all, delete-orphan")
	category: Mapped["Category | None"] = relationship("Category", back_populates="products")


