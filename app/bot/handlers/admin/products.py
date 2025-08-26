from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.product import Category, Product
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
	from app.bot.keyboards.inline import admin_menu_keyboard as _kb  # local import
	await _safe_edit_cb(callback, "Админ меню", reply_markup=_kb().as_markup())
	await callback.answer()


@router.callback_query(F.data == "admin:product:add")
async def admin_product_add_from_menu(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	await state.clear()
	await state.set_state(ProductCreateStates.title)
	await _safe_edit_cb(callback, "Введите название товара")
	await callback.answer()


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
	await state.set_state(AdminCategoryStates.name)
	await _safe_edit_cb(callback, "Отправьте название категории")
	await callback.answer()


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
	from app.bot.keyboards.inline import admin_menu_keyboard as _kb
	async with SessionLocal() as session:
		result = await session.execute(select(Category).order_by(Category.name))
		cats = list(result.scalars().all())
	text = "Категорий нет" if not cats else "\n".join(f"{c.id}: {c.name}" for c in cats)
	await _safe_edit_cb(callback, text, reply_markup=_kb().as_markup())
	await callback.answer()


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
	await callback.message.edit_text("Выберите категорию", reply_markup=kb.as_markup())
	await callback.answer()


@router.callback_query(ProductCreateStates.category, F.data.startswith("admincat:"))
async def pc_category(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
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
	await callback.message.edit_text("\n".join([x for x in preview if x]))
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
	await callback.message.edit_text("Товар создан ✅", reply_markup=admin_menu_keyboard().as_markup())
	await callback.answer()


# --- Appended: products list and edit handlers ---
from app.bot.keyboards.inline import admin_products_keyboard, admin_product_edit_keyboard


@router.callback_query(F.data == "admin:products")
async def admin_products(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	async with SessionLocal() as session:
		res = await session.execute(select(Product).order_by(Product.title))
		prods = list(res.scalars().all())
	if not prods:
		await callback.message.edit_text("Товаров нет", reply_markup=admin_menu_keyboard().as_markup())
		await callback.answer()
		return
	kb = admin_products_keyboard([(p.id, p.title) for p in prods])
	await _safe_edit_cb(callback, "Выберите товар для редактирования:", reply_markup=kb.as_markup())
	await callback.answer()


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


class ProductEditStates(StatesGroup):
	edit_title = State()
	edit_desc = State()
	edit_price = State()
	edit_stock = State()
	edit_bulk_price = State()
	edit_bulk_threshold = State()


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
	await _safe_edit_cb(callback, "Введите новое описание (или '-' чтобы очистить)")
	await callback.answer()


@router.message(ProductEditStates.edit_desc)
async def edit_desc_save(message: Message, state: FSMContext) -> None:
	data = await state.get_data()
	pid = int(data.get("product_id"))
	desc = None if (message.text or "").strip() == "-" else message.text
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await message.answer("Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			prod.description = desc
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
		price = float(price_text)
	except ValueError:
		await message.answer("Неверная цена")
		return
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await message.answer("Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			prod.price = price
		await session.commit()
	await state.clear()
	await message.answer("Цена обновлена", reply_markup=admin_product_edit_keyboard(pid).as_markup())


@router.callback_query(F.data.startswith("admin:edit:stock:"))
async def edit_stock_start(callback: CallbackQuery, state: FSMContext) -> None:
	_, pid = _parse_edit(callback.data or "")
	await state.set_state(ProductEditStates.edit_stock)
	await state.update_data(product_id=pid)
	await _safe_edit_cb(callback, "Введите остаток на складе (целое число)")
	await callback.answer()


@router.message(ProductEditStates.edit_stock)
async def edit_stock_save(message: Message, state: FSMContext) -> None:
	data = await state.get_data()
	pid = int(data.get("product_id"))
	try:
		qty = int((message.text or "").strip())
	except ValueError:
		await message.answer("Неверное число")
		return
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await message.answer("Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			prod.stock_qty = qty
		await session.commit()
	await state.clear()
	await message.answer("Остаток обновлён", reply_markup=admin_product_edit_keyboard(pid).as_markup())


@router.callback_query(F.data.startswith("admin:edit:bulk_price:"))
async def edit_bulk_price_start(callback: CallbackQuery, state: FSMContext) -> None:
	_, pid = _parse_edit(callback.data or "")
	await state.set_state(ProductEditStates.edit_bulk_price)
	await state.update_data(product_id=pid)
	await _safe_edit_cb(callback, "Введите оптовую цену, например 149.99 (или '-' чтобы очистить)")
	await callback.answer()


@router.message(ProductEditStates.edit_bulk_price)
async def edit_bulk_price_save(message: Message, state: FSMContext) -> None:
	data = await state.get_data()
	pid = int(data.get("product_id"))
	text = (message.text or "").strip()
	bulk_price = None
	if text != "-":
		try:
			bulk_price = float(text.replace(",", "."))
		except ValueError:
			await message.answer("Неверная цена")
			return
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await message.answer("Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			prod.bulk_price = bulk_price
		await session.commit()
	await state.clear()
	await message.answer("Оптовая цена обновлена", reply_markup=admin_product_edit_keyboard(pid).as_markup())


@router.callback_query(F.data.startswith("admin:edit:bulk_threshold:"))
async def edit_bulk_threshold_start(callback: CallbackQuery, state: FSMContext) -> None:
	_, pid = _parse_edit(callback.data or "")
	await state.set_state(ProductEditStates.edit_bulk_threshold)
	await state.update_data(product_id=pid)
	await _safe_edit_cb(callback, "Введите оптовый порог (целое число, '-' чтобы очистить)")
	await callback.answer()


@router.message(ProductEditStates.edit_bulk_threshold)
async def edit_bulk_threshold_save(message: Message, state: FSMContext) -> None:
	data = await state.get_data()
	pid = int(data.get("product_id"))
	text = (message.text or "").strip()
	bulk_threshold = None
	if text != "-":
		try:
			bulk_threshold = int(text)
		except ValueError:
			await message.answer("Неверное число")
			return
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await message.answer("Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			prod.bulk_threshold = bulk_threshold
		await session.commit()
	await state.clear()
	await message.answer("Оптовый порог обновлён", reply_markup=admin_product_edit_keyboard(pid).as_markup())


@router.callback_query(F.data.startswith("admin:product:delete:"))
async def admin_product_delete(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	parts = (callback.data or "").split(":")
	pid = int(parts[-1])
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				from app.bot.keyboards.inline import admin_menu_keyboard as _kb
				await _safe_edit_cb(callback, "Товар не найден", reply_markup=_kb().as_markup())
				await callback.answer()
				return
			await session.delete(prod)
	await _safe_edit_cb(callback, "Товар удалён", reply_markup=admin_menu_keyboard().as_markup())
	await callback.answer()


@router.callback_query(F.data.startswith("admin:edit:toggle_instock:"))
async def edit_toggle_instock(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await callback.answer()
		return
	parts = (callback.data or "").split(":")
	pid = int(parts[-1])
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Product).where(Product.id == pid))
			prod = res.scalars().first()
			if not prod:
				await _safe_edit_cb(callback, "Товар не найден", reply_markup=admin_menu_keyboard().as_markup())
				await callback.answer()
				return
			prod.in_stock = not bool(getattr(prod, "in_stock", True))
		await session.commit()
	await _safe_edit_cb(callback, "Наличие переключено", reply_markup=admin_product_edit_keyboard(pid).as_markup())
	await callback.answer()



