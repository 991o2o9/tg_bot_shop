from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, update, delete
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.product import Category, Product
from app.models.order import OrderItem
from app.bot.keyboards.inline import admin_categories_keyboard, admin_menu_keyboard


router = Router(name="admin_products")


async def _safe_edit_cb(callback: CallbackQuery, text: str, reply_markup=None) -> None:
	try:
		await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
	except TelegramBadRequest:
		try:
			await callback.message.edit_text(text, reply_markup=reply_markup)
		except TelegramBadRequest:
			await callback.message.answer(text, reply_markup=reply_markup)


def _is_admin(user_id: int) -> bool:
	if not settings.admin_ids:
		return False
	admin_id_set = {int(x.strip()) for x in settings.admin_ids.split(",") if x.strip()}
	return user_id in admin_id_set


@router.message(Command("addproduct"))
async def add_product(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		await message.answer("Нет доступа")
		return
	await state.clear()
	await state.set_state(ProductCreateStates.title)
	await message.answer("Введите название товара")


@router.message(Command("deleteproduct"))
async def delete_product(message: Message) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		await message.answer("Нет доступа")
		return
	await message.answer("Удаление товара: пока заглушка.", reply_markup=admin_menu_keyboard().as_markup())


@router.message(Command("sendall"))
async def send_all(message: Message) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		await message.answer("Нет доступа")
		return
	await message.answer("Рассылка: пока заглушка.", reply_markup=admin_menu_keyboard().as_markup())


@router.callback_query(F.data == "admin:open")
async def admin_open(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	# answer early to avoid stale query problems
	try:
		await callback.answer()
	except Exception:
		pass
	from app.bot.keyboards.inline import admin_menu_keyboard as _kb  # local import
	await _safe_edit_cb(callback, "Админ меню", reply_markup=_kb().as_markup())
	# already answered above


@router.callback_query(F.data == "admin:product:add")
async def admin_product_add_from_menu(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	await state.clear()
	await state.set_state(ProductCreateStates.title)
	await _safe_edit_cb(callback, "Введите название товара")
	# already answered above


@router.message(Command("addcat"))
async def add_category(message: Message) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		await message.answer("Нет доступа")
		return
	parts = [p.strip() for p in (message.text or "").split(maxsplit=1)]
	if len(parts) < 2:
		await message.answer("Использование: /addcat НазваниеКатегории", reply_markup=admin_menu_keyboard().as_markup())
		return
	name = parts[1]
	async with SessionLocal() as session:
		async with session.begin():
			existing = await session.execute(select(Category).where(Category.name == name))
			if existing.scalars().first():
				await message.answer("Такая категория уже существует", reply_markup=admin_menu_keyboard().as_markup())
				return
			category = Category(name=name)
			session.add(category)
		await session.commit()
	await message.answer("Категория добавлена", reply_markup=admin_menu_keyboard().as_markup())


@router.callback_query(F.data == "admin:category:add")
async def admin_category_add_open(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	await state.set_state(AdminCategoryStates.name)
	await _safe_edit_cb(callback, "Отправьте название категории")
	# already answered above


@router.message(Command("listcat"))
async def list_categories(message: Message) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		await message.answer("Нет доступа")
		return
	async with SessionLocal() as session:
		result = await session.execute(select(Category).order_by(Category.name))
		cats = list(result.scalars().all())
	if not cats:
		await message.answer("Категорий нет", reply_markup=admin_menu_keyboard().as_markup())
		return
	text = "\n".join(f"{c.id}: {c.name}" for c in cats)
	await message.answer(text, reply_markup=admin_menu_keyboard().as_markup())


@router.callback_query(F.data == "admin:category:list")
async def admin_category_list(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	async with SessionLocal() as session:
		result = await session.execute(select(Category).order_by(Category.name))
		cats = list(result.scalars().all())
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	builder = InlineKeyboardBuilder()
	if not cats:
		builder.button(text="➕ Добавить", callback_data="admin:category:add")
		builder.button(text="↩️ Назад", callback_data="admin:open")
		builder.adjust(2)
		await _safe_edit_cb(callback, "Категорий нет", reply_markup=builder.as_markup())
		return
	for c in cats:
		builder.button(text=f"📂 {c.name}", callback_data=f"admin:category:open:{c.id}")
	builder.adjust(1)
	builder.button(text="↩️ Назад", callback_data="admin:open")
	await _safe_edit_cb(callback, "Категории:", reply_markup=builder.as_markup())
	# already answered above


class ProductCreateStates(StatesGroup):
	title = State()
	description = State()
	photo = State()
	price = State()
	availability = State()
	category = State()
	save = State()


class AdminCategoryStates(StatesGroup):
	name = State()


class AdminCategoryEditStates(StatesGroup):
	rename = State()


@router.message(AdminCategoryStates.name)
async def admin_category_create_name(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	name = (message.text or "").strip()
	if not name:
		await message.answer("Название не может быть пустым. Введите ещё раз")
		return
	async with SessionLocal() as session:
		async with session.begin():
			existing = await session.execute(select(Category).where(Category.name == name))
			if existing.scalars().first():
				await message.answer("Такая категория уже существует", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			category = Category(name=name)
			session.add(category)
		await session.commit()
	await state.clear()
	await message.answer("Категория добавлена", reply_markup=admin_menu_keyboard().as_markup())


@router.callback_query(F.data.startswith("admin:category:open:"))
async def admin_category_open(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	cid = int((callback.data or "").rsplit(":", 1)[-1])
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	builder = InlineKeyboardBuilder()
	builder.button(text="✏️ Переименовать", callback_data=f"admin:category:rename:{cid}")
	builder.button(text="🗑 Удалить", callback_data=f"admin:category:delete:{cid}")
	builder.button(text="↩️ Назад", callback_data="admin:category:list")
	builder.adjust(2)
	await _safe_edit_cb(callback, f"Категория ID {cid}", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin:category:rename:"))
async def admin_category_rename_start(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	cid = int((callback.data or "").rsplit(":", 1)[-1])
	await state.set_state(AdminCategoryEditStates.rename)
	await state.update_data(category_id=cid)
	await _safe_edit_cb(callback, "Отправьте новое название категории")


@router.message(AdminCategoryEditStates.rename)
async def admin_category_rename_save(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	new_name = (message.text or "").strip()
	if not new_name:
		await message.answer("Название не может быть пустым. Введите ещё раз")
		return
	data = await state.get_data()
	cid = int(data.get("category_id"))
	async with SessionLocal() as session:
		async with session.begin():
			# check duplicate
			exists = await session.execute(select(Category).where(Category.name == new_name))
			if exists.scalars().first():
				await message.answer("Такая категория уже существует", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			res = await session.execute(select(Category).where(Category.id == cid))
			cat = res.scalars().first()
			if not cat:
				await message.answer("Категория не найдена", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			cat.name = new_name
		await session.commit()
	await state.clear()
	await message.answer("Категория переименована", reply_markup=admin_menu_keyboard().as_markup())


@router.callback_query(F.data.startswith("admin:category:delete:"))
async def admin_category_delete(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	cid = int((callback.data or "").rsplit(":", 1)[-1])
	async with SessionLocal() as session:
		async with session.begin():
			# detach products
			await session.execute(update(Product).where(Product.category_id == cid).values(category_id=None))
			# delete category
			await session.execute(delete(Category).where(Category.id == cid))
		await session.commit()
	from app.bot.keyboards.inline import admin_menu_keyboard as _kb
	await _safe_edit_cb(callback, "Категория удалена", reply_markup=_kb().as_markup())


@router.message(ProductCreateStates.title, F.text)
async def pc_title(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	await state.update_data(title=message.text)
	await state.set_state(ProductCreateStates.description)
	await message.answer("Введите описание (или отправьте '-' чтобы пропустить)")


@router.message(ProductCreateStates.description)
async def pc_description(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	desc = None if (message.text or "").strip() == "-" else message.text
	await state.update_data(description=desc)
	await state.set_state(ProductCreateStates.photo)
	await message.answer("Пришлите фото товара (как фото, не как файл). Можно пропустить '-' ")


@router.message(ProductCreateStates.photo, F.photo)
async def pc_photo(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	file_id = message.photo[-1].file_id  # type: ignore[index]
	await state.update_data(photo_file_id=file_id)
	await state.set_state(ProductCreateStates.price)
	await message.answer("Введите цену, например 199.99")


@router.message(ProductCreateStates.photo, F.text)
async def pc_photo_skip(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	if (message.text or "").strip() == "-":
		await state.update_data(photo_file_id=None)
		await state.set_state(ProductCreateStates.price)
		await message.answer("Введите цену, например 199.99")
	else:
		await message.answer("Пришлите фото или '-' для пропуска")


@router.message(ProductCreateStates.price, F.text)
async def pc_price(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	price_text = (message.text or "").replace(",", ".").strip()
	try:
		price = float(price_text)
	except ValueError:
		await message.answer("Неверная цена. Введите ещё раз, например 199.99")
		return
	await state.update_data(price=price)
	# ask availability via inline buttons
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	kb = InlineKeyboardBuilder()
	kb.button(text="✅ В наличии", callback_data="admin:availability:yes")
	kb.button(text="❌ Нет в наличии", callback_data="admin:availability:no")
	kb.adjust(2)
	await state.set_state(ProductCreateStates.availability)
	await message.answer("Товар в наличии?", reply_markup=kb.as_markup())


@router.callback_query(ProductCreateStates.availability, F.data.startswith("admin:availability:"))
async def pc_availability(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	parts = (callback.data or "").split(":")  # type: ignore[union-attr]
	in_stock = parts[-1] == "yes"
	await state.update_data(in_stock=in_stock)
	# proceed to category selection
	async with SessionLocal() as session:
		res = await session.execute(select(Category).order_by(Category.name))
		cats = list(res.scalars().all())
	if not cats:
		await callback.message.edit_text("Сначала создайте категорию: /addcat Название", reply_markup=admin_menu_keyboard().as_markup())
		await state.clear()
		await callback.answer()
		return
	from app.bot.keyboards.inline import admin_categories_keyboard as _kb
	kb = _kb([(c.id, c.name) for c in cats])
	await state.set_state(ProductCreateStates.category)
	await _safe_edit_cb(callback, "Выберите категорию", reply_markup=kb.as_markup())
	# already answered above


@router.callback_query(ProductCreateStates.category, F.data.startswith("admincat:"))
async def pc_category(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	_, cid = callback.data.split(":", 1)  # type: ignore[union-attr]
	await state.update_data(category_id=int(cid))
	await state.set_state(ProductCreateStates.save)
	data = await state.get_data()
	preview = [
		f"<b>{data.get('title')}</b>",
		data.get('description') or "",
		f"Цена: {float(data.get('price', 0)):.2f}",
		f"Категория ID: {data.get('category_id')}",
	]
	await _safe_edit_cb(callback, "\n".join([x for x in preview if x]))
	# persist
	async with SessionLocal() as session:
		async with session.begin():
			product = Product(
				title=data.get('title'),
				description=data.get('description'),
				price=float(data.get('price', 0)),
				category_id=int(data.get('category_id')),
				photo_file_id=data.get('photo_file_id'),
				in_stock=bool(data.get('in_stock', True)),
			)
			session.add(product)
		await session.commit()
	await state.clear()
	await _safe_edit_cb(callback, "Товар создан ✅", reply_markup=admin_menu_keyboard().as_markup())
	# already answered above


# --- Appended: products list and edit handlers ---
from app.bot.keyboards.inline import admin_products_keyboard, admin_product_edit_keyboard
from app.bot.keyboards.inline import admin_menu_keyboard as _admin_menu_kb
from aiogram.types import InlineKeyboardButton


@router.callback_query(F.data == "admin:products")
async def admin_products(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	async with SessionLocal() as session:
		res = await session.execute(select(Product).order_by(Product.title))
		prods = list(res.scalars().all())
	if not prods:
		await _safe_edit_cb(callback, "Товаров нет", reply_markup=admin_menu_keyboard().as_markup())
		return
	kb = admin_products_keyboard([(p.id, p.title) for p in prods])
	await _safe_edit_cb(callback, "Выберите товар для редактирования:", reply_markup=kb.as_markup())
	# already answered above
@router.callback_query(F.data == "admin:products:archived")
async def admin_products_archived(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	async with SessionLocal() as session:
		res = await session.execute(select(Product).where(getattr(Product, "is_deleted", False) == True).order_by(Product.title))
		prods = list(res.scalars().all())
	if not prods:
		await _safe_edit_cb(callback, "Архив пуст", reply_markup=_admin_menu_kb().as_markup())
		return
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	builder = InlineKeyboardBuilder()
	for p in prods:
		builder.button(text=f"📦 {p.title}", callback_data=f"admin:arch:open:{p.id}")
	builder.adjust(1)
	builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:open"))
	await _safe_edit_cb(callback, "Архив товаров", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin:arch:open:"))
async def admin_archived_open(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	pid = int((callback.data or "").rsplit(":", 1)[-1])
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	builder = InlineKeyboardBuilder()
	builder.row(InlineKeyboardButton(text="♻️ Восстановить", callback_data=f"admin:arch:restore:{pid}"))
	builder.row(InlineKeyboardButton(text="🗑 Удалить навсегда", callback_data=f"admin:arch:delete:{pid}"))
	builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:products:archived"))
	await _safe_edit_cb(callback, f"Товар #{pid} в архиве", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin:arch:restore:"))
async def admin_archived_restore(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	pid = int((callback.data or "").rsplit(":", 1)[-1])
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await _safe_edit_cb(callback, "Товар не найден", reply_markup=_admin_menu_kb().as_markup())
				return
			prod.is_deleted = False  # type: ignore[attr-defined]
			# не включаем автоматически в продажу, админ решит сам
	await _safe_edit_cb(callback, "Товар восстановлен", reply_markup=_admin_menu_kb().as_markup())


@router.callback_query(F.data.startswith("admin:arch:delete:"))
async def admin_archived_delete_permanently(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	pid = int((callback.data or "").rsplit(":", 1)[-1])
	from sqlalchemy import delete as sa_delete
	async with SessionLocal() as session:
		async with session.begin():
			# удалить связанные позиции заказов, чтобы не нарушить FK
			await session.execute(sa_delete(OrderItem).where(OrderItem.product_id == pid))
			# удалить сам товар
			await session.execute(sa_delete(Product).where(Product.id == pid))
		await session.commit()
	# вернуться к списку архива
	async with SessionLocal() as session:
		res = await session.execute(select(Product).where(getattr(Product, "is_deleted", False) == True).order_by(Product.title))
		prods = list(res.scalars().all())
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	builder = InlineKeyboardBuilder()
	if not prods:
		builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:open"))
		await _safe_edit_cb(callback, "Архив пуст", reply_markup=builder.as_markup())
		return
	for p in prods:
		builder.button(text=f"📦 {p.title}", callback_data=f"admin:arch:open:{p.id}")
	builder.adjust(1)
	builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:open"))
	await _safe_edit_cb(callback, "Товар удалён навсегда", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("adminprod:"))
async def admin_product_open(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	_, pid = callback.data.split(":", 1)  # type: ignore[union-attr]
	product_id = int(pid)
	kb = admin_product_edit_keyboard(product_id)
	# try show product photo with caption
	async with SessionLocal() as session:
		res = await session.execute(select(Product).where(Product.id == product_id))
		prod = res.scalars().first()
	if prod and getattr(prod, "photo_file_id", None):
		caption_lines = [f"<b>{prod.title}</b>"]
		if prod.description:
			caption_lines.append(prod.description)
		try:
			await callback.message.delete()
			await callback.message.answer_photo(prod.photo_file_id, caption="\n".join(caption_lines), reply_markup=kb.as_markup())
		except Exception:
			await _safe_edit_cb(callback, f"Редактирование товара ID {product_id}", reply_markup=kb.as_markup())
	else:
		await _safe_edit_cb(callback, f"Редактирование товара ID {product_id}", reply_markup=kb.as_markup())
	await callback.answer()


@router.callback_query(F.data.startswith("admin:product:delete:"))
async def admin_product_delete(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	pid_str = (callback.data or "").rsplit(":", 1)[-1]
	try:
		pid = int(pid_str)
	except ValueError:
		await _safe_edit_cb(callback, "Некорректный ID товара", reply_markup=admin_menu_keyboard().as_markup())
		return
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await _safe_edit_cb(callback, "Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				return
			# мягкое удаление: помечаем как удалённый
			if hasattr(prod, "is_deleted"):
				setattr(prod, "is_deleted", True)
			else:
				# если поля нет, просто скрываем из наличия
				if hasattr(prod, "in_stock"):
					setattr(prod, "in_stock", False)
		await session.commit()
	# после удаления вернёмся к списку товаров
	async with SessionLocal() as session:
		res = await session.execute(select(Product).where(getattr(Product, "is_deleted", False) == False).order_by(Product.title))
		prods = list(res.scalars().all())
	from app.bot.keyboards.inline import admin_products_keyboard as _prods_kb
	if not prods:
		await _safe_edit_cb(callback, "Товар удалён. Товаров нет", reply_markup=admin_menu_keyboard().as_markup())
		return
	kb = _prods_kb([(p.id, p.title) for p in prods])
	await _safe_edit_cb(callback, "Товар удалён", reply_markup=kb.as_markup())


class ProductEditStates(StatesGroup):
	edit_title = State()
	edit_desc = State()
	edit_price = State()
	edit_stock = State()
	edit_bulk_price = State()
	edit_bulk_threshold = State()
	edit_photo = State()
	edit_category = State()


class NotifyStates(StatesGroup):
	notify_text = State()


def _parse_edit(data: str) -> tuple[str, int]:
	parts = data.split(":")
	return parts[2], int(parts[3])


@router.callback_query(F.data.startswith("admin:edit:title:"))
async def edit_title_start(callback: CallbackQuery, state: FSMContext) -> None:
	_, pid = _parse_edit(callback.data or "")
	await state.set_state(ProductEditStates.edit_title)
	await state.update_data(product_id=pid)
	await _safe_edit_cb(callback, "Введите новое название")
	await callback.answer()


@router.message(ProductEditStates.edit_title)
async def edit_title_save(message: Message, state: FSMContext) -> None:
	data = await state.get_data()
	pid = int(data.get("product_id"))
	new_title = (message.text or "").strip()
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await message.answer("Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			prod.title = new_title
		await session.commit()
	await state.clear()
	await message.answer("Название обновлено", reply_markup=admin_product_edit_keyboard(pid).as_markup())


@router.callback_query(F.data.startswith("admin:edit:desc:"))
async def edit_desc_start(callback: CallbackQuery, state: FSMContext) -> None:
	_, pid = _parse_edit(callback.data or "")
	await state.set_state(ProductEditStates.edit_desc)
	await state.update_data(product_id=pid)
	await _safe_edit_cb(callback, "Отправьте новое описание (или '-' чтобы очистить)")
	await callback.answer()


@router.message(ProductEditStates.edit_desc)
async def edit_desc_save(message: Message, state: FSMContext) -> None:
	data = await state.get_data()
	pid = int(data.get("product_id"))
	text = (message.text or "").strip()
	new_desc = None if text == "-" else text
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await message.answer("Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			prod.description = new_desc
		await session.commit()
	await state.clear()
	await message.answer("Описание обновлено", reply_markup=admin_product_edit_keyboard(pid).as_markup())


@router.callback_query(F.data.startswith("admin:edit:price:"))
async def edit_price_start(callback: CallbackQuery, state: FSMContext) -> None:
	_, pid = _parse_edit(callback.data or "")
	await state.set_state(ProductEditStates.edit_price)
	await state.update_data(product_id=pid)
	await _safe_edit_cb(callback, "Введите новую цену, например 199.99")
	await callback.answer()


@router.message(ProductEditStates.edit_price)
async def edit_price_save(message: Message, state: FSMContext) -> None:
	data = await state.get_data()
	pid = int(data.get("product_id"))
	price_text = (message.text or "").replace(",", ".").strip()
	try:
		new_price = float(price_text)
	except ValueError:
		await message.answer("Неверная цена. Введите ещё раз, например 199.99")
		return
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await message.answer("Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			prod.price = new_price
		await session.commit()
	await state.clear()
	await message.answer("Цена обновлена", reply_markup=admin_product_edit_keyboard(pid).as_markup())


@router.callback_query(F.data.startswith("admin:edit:photo:"))
async def edit_photo_start(callback: CallbackQuery, state: FSMContext) -> None:
	_, pid = _parse_edit(callback.data or "")
	await state.set_state(ProductEditStates.edit_photo)
	await state.update_data(product_id=pid)
	await _safe_edit_cb(callback, "Отправьте новое фото товара (как фото, не как файл)")
	await callback.answer()


@router.message(ProductEditStates.edit_photo, F.photo)
async def edit_photo_save(message: Message, state: FSMContext) -> None:
	data = await state.get_data()
	pid = int(data.get("product_id"))
	file_id = message.photo[-1].file_id  # type: ignore[index]
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await message.answer("Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			prod.photo_file_id = file_id
		await session.commit()
	await state.clear()
	await message.answer("Фото обновлено", reply_markup=admin_product_edit_keyboard(pid).as_markup())


@router.callback_query(F.data.startswith("admin:edit:category:"))
async def edit_category_start(callback: CallbackQuery, state: FSMContext) -> None:
	_, pid = _parse_edit(callback.data or "")
	await state.set_state(ProductEditStates.edit_category)
	await state.update_data(product_id=pid)
	async with SessionLocal() as session:
		res = await session.execute(select(Category).order_by(Category.name))
		cats = list(res.scalars().all())
	if not cats:
		await _safe_edit_cb(callback, "Сначала создайте категорию", reply_markup=admin_menu_keyboard().as_markup())
		await state.clear()
		await callback.answer()
		return
	kb = admin_categories_keyboard([(c.id, c.name) for c in cats])
	await _safe_edit_cb(callback, "Выберите новую категорию", reply_markup=kb.as_markup())
	await callback.answer()


@router.callback_query(ProductEditStates.edit_category, F.data.startswith("admincat:"))
async def edit_category_save(callback: CallbackQuery, state: FSMContext) -> None:
	parts = (callback.data or "").split(":")  # type: ignore[union-attr]
	cid = int(parts[-1])
	data = await state.get_data()
	pid = int(data.get("product_id"))
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await _safe_edit_cb(callback, "Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				await callback.answer()
				return
			prod.category_id = cid
		await session.commit()
	await state.clear()
	await _safe_edit_cb(callback, "Категория обновлена", reply_markup=admin_product_edit_keyboard(pid).as_markup())
	await callback.answer()


@router.callback_query(F.data == "admin:notify")
async def admin_notify_open_callback(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	await state.clear()
	await state.set_state(NotifyStates.notify_text)
	await _safe_edit_cb(callback, "Введите текст уведомления (будет отправлен всем пользователям)")


@router.message(NotifyStates.notify_text)
async def admin_notify_send(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	text = (message.text or "").strip()
	if not text:
		await message.answer("Текст пуст. Отправьте текст уведомления")
		return
	from app.models.user import User as AppUser
	async with SessionLocal() as session:
		res = await session.execute(select(AppUser.id))
		user_ids = [row[0] for row in res.all()]
	sent = 0
	errors = 0
	for uid in user_ids:
		try:
			await message.bot.send_message(uid, text)
			sent += 1
		except Exception:
			errors += 1
	await state.clear()
	await message.answer(f"Отправлено: {sent}. Ошибок: {errors}", reply_markup=admin_menu_keyboard().as_markup())



