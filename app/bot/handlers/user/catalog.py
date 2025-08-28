from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.inline import (
	catalog_keyboard,
	categories_keyboard,
	products_keyboard,
	product_qty_keyboard,
	categories_keyboard_with_nav,
	products_keyboard_with_nav,
	product_view_keyboard,
    main_menu_keyboard,
    info_menu_keyboard,
    flavor_selection_keyboard,
)
from app.db.session import SessionLocal
from app.models.order import Order, OrderItem
from app.models.product import Category, Product
from app.models.user import User
from app.core.config import settings


router = Router(name="user_catalog")


async def _safe_edit(callback: CallbackQuery, text: str, reply_markup=None) -> None:
	try:
		await callback.message.edit_text(text, reply_markup=reply_markup)
	except TelegramBadRequest:
		await callback.message.answer(text, reply_markup=reply_markup)


async def _safe_answer(callback: CallbackQuery) -> None:
	"""Safely call callback.answer() with error handling for old queries."""
	try:
		await callback.answer()
	except TelegramBadRequest:
		pass  # Ignore old query errors


@router.message(CommandStart())
async def start(message: Message) -> None:
	user_id = message.from_user.id
	from app.core.config import settings as _settings 
	is_admin = False
	if _settings.admin_ids:
		try:
			is_admin = user_id in {int(x.strip()) for x in _settings.admin_ids.split(",") if x.strip()}
		except Exception:
			is_admin = False
	# ensure user exists in DB
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(User).where(User.id == user_id))
			if res.scalars().first() is None:
				session.add(User(
					id=user_id,
					first_name=message.from_user.first_name if message.from_user else None, last_name=message.from_user.last_name if message.from_user else None,
				))
	from app.core.config import settings as __settings
	from sqlalchemy import select as _select
	from app.models.branding import Branding as _Branding
	logo_id = __settings.logo_file_id
	welcome_text = __settings.welcome_text or "Добро пожаловать! Выберите раздел ниже, чтобы начать покупки."
	try:
		async with SessionLocal() as session:
			res = await session.execute(_select(_Branding).where(_Branding.id == 1))
			b = res.scalars().first()
			if b:
				logo_id = b.logo_file_id or logo_id
				welcome_text = b.welcome_text or welcome_text
	except Exception:
		pass
	if logo_id:
		try:
			await message.answer_photo(logo_id, caption=welcome_text, reply_markup=main_menu_keyboard(is_admin).as_markup())
		except Exception:
			await message.answer(welcome_text, reply_markup=main_menu_keyboard(is_admin).as_markup())
	else:
		await message.answer(welcome_text, reply_markup=main_menu_keyboard(is_admin).as_markup())


@router.callback_query(F.data == "catalog:open")
async def open_catalog(callback: CallbackQuery) -> None:
	async with SessionLocal() as session:
		categories = await _load_categories(session)
	if not categories:
		await _safe_edit(callback, "Категории пока не добавлены.")
	else:
		kb = categories_keyboard_with_nav([(c.id, c.name) for c in categories])
		await _safe_edit(callback, "Выберите категорию:", reply_markup=kb.as_markup())
	await _safe_answer(callback)


async def _load_categories(session: AsyncSession) -> list[Category]:
	result = await session.execute(select(Category).order_by(Category.name))
	return list(result.scalars().all())


@router.callback_query(F.data.startswith("category:"))
async def open_category(callback: CallbackQuery) -> None:
	# data format: category:<category_id>
	parts = (callback.data or "").split(":")
	category_id = int(parts[1])
	async with SessionLocal() as session:
		products = await _load_products_by_category(session, category_id)
	if not products:
		await _safe_edit(callback, "В этой категории пока нет товаров.")
	else:
		kb = products_keyboard_with_nav([(p.id, p.title) for p in products], category_id)
		await _safe_edit(callback, "Выберите товар:", reply_markup=kb.as_markup())
	await _safe_answer(callback)


async def _load_products_by_category(session: AsyncSession, category_id: int) -> list[Product]:
	result = await session.execute(
		select(Product).where(
			Product.category_id == category_id,
			Product.in_stock == True,
			getattr(Product, "is_deleted", False) == False
		).order_by(Product.title)
	)
	return list(result.scalars().all())


@router.callback_query(F.data.startswith("product:"))
async def open_product(callback: CallbackQuery) -> None:
	# data format: product:<product_id>
	parts = (callback.data or "").split(":")
	product_id = int(parts[1])
	async with SessionLocal() as session:
		product = await _load_product(session, product_id)
	if not product:
		await _safe_edit(callback, "Товар не найден.")
		await _safe_answer(callback)
		return
	
	# Check if product has flavors
	from app.models.flavor import Flavor
	flavors_res = await session.execute(select(Flavor).where(Flavor.product_id == product_id, Flavor.is_available == True))
	flavors = list(flavors_res.scalars().all())
	
	qty = 1
	text_lines = _product_text(product, qty)
	
	# Add flavors info right after description
	if flavors:
		text_lines.insert(3, "")  # Add empty line after description
		text_lines.insert(4, "🍃 <b>Доступные вкусы:</b>")
		for flavor in flavors:
			text_lines.insert(5, f"• {flavor.name}")
		text_lines.insert(5 + len(flavors), "")  # Add empty line after flavors
		text_lines.insert(6 + len(flavors), "Выберите вкус и количество, затем добавьте в корзину")
	
	kb = product_view_keyboard(product.id, product.category_id, qty, enabled=getattr(product, "in_stock", True), has_flavors=bool(flavors))
	if product.photo_file_id:
		try:
			await callback.message.delete()
			await callback.message.answer_photo(product.photo_file_id, caption="\n".join(text_lines), reply_markup=kb.as_markup())
		except TelegramBadRequest:
			await callback.message.edit_text("\n".join(text_lines), reply_markup=kb.as_markup())
	else:
		await callback.message.edit_text("\n".join(text_lines), reply_markup=kb.as_markup())
	await _safe_answer(callback)


def _calc_price(product: Product, qty: int) -> float:
	base_price = float(product.price)
	if product.bulk_threshold and product.bulk_price and qty >= product.bulk_threshold:
		return float(product.bulk_price)
	return base_price


def _product_text(product: Product, qty: int) -> list[str]:
	lines = [f"<b>{product.title}</b>", ""]
	if product.description:
		lines.append(product.description)
		lines.append("")
	
	# Add flavors info if available (this will be populated by the calling function)
	# The flavors are added by the open_product function after calling this function
	
	unit_price = _calc_price(product, qty)
	lines.append(f"Цена: <b>{unit_price:.2f}</b>")
	if qty > 1:
		lines.append(f"Итого: <b>{unit_price*qty:.2f}</b>")
	avail = "Есть" if getattr(product, "in_stock", True) else "Нет"
	lines.extend(["", f"Наличие: <b>{avail}</b>"])
	return lines


def _product_with_flavor_text(product: Product, flavor, qty: int) -> list[str]:
	"""Generate product text with selected flavor information"""
	lines = [f"<b>{product.title}</b>", ""]
	if product.description:
		lines.append(product.description)
		lines.append("")
	
	# Add selected flavor info
	lines.append("🍃 <b>Выбранный вкус:</b>")
	lines.append(f"• {flavor.name}")
	lines.append("")
	
	unit_price = _calc_price(product, qty)
	lines.append(f"Цена: <b>{unit_price:.2f}</b>")
	if qty > 1:
		lines.append(f"Итого: <b>{unit_price*qty:.2f}</b>")
	avail = "Есть" if getattr(product, "in_stock", True) else "Нет"
	lines.extend(["", f"Наличие: <b>{avail}</b>"])
	lines.append("")
	lines.append("Выберите количество и добавьте в корзину:")
	return lines


@router.callback_query(F.data.startswith("cart:add:"))
async def cart_add(callback: CallbackQuery) -> None:
	# data format: cart:add:<product_id>:<qty>
	parts = (callback.data or "").split(":")
	product_id = int(parts[2])
	qty = int(parts[3]) if len(parts) > 3 else 1
	user_id = callback.from_user.id 
	async with SessionLocal() as session:
		async with session.begin():
			res_user = await session.execute(select(User).where(User.id == user_id))
			if res_user.scalars().first() is None:
				session.add(User(id=user_id))
		result = await session.execute(
			select(Order).where(Order.user_id == user_id, Order.status == "new")
		)
		order = result.scalars().first()
		if not order:
			order = Order(user_id=user_id, status="new")
			session.add(order)
			await session.flush()
		# add or update item
		prod_res = await session.execute(select(Product).where(Product.id == product_id))
		product = prod_res.scalars().first()
		if not product:
			await callback.answer("Товар не найден", show_alert=True)
			return
		
		# Check if product has flavors - if yes, don't allow adding without flavor
		from app.models.flavor import Flavor
		flavors_res = await session.execute(select(Flavor).where(Flavor.product_id == product_id, Flavor.is_available == True))
		flavors = list(flavors_res.scalars().all())
		
		if flavors:
			await callback.answer("Для этого товара необходимо выбрать вкус!", show_alert=True)
			return
		
		item_res = await session.execute(
			select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.product_id == product_id, OrderItem.flavor_id.is_(None))
		)
		item = item_res.scalars().first()
		if item:
			# If item already exists without flavor, check if product now has flavors
			if flavors:
				await callback.answer("Для этого товара необходимо выбрать вкус! Удалите товар из корзины и добавьте заново с выбором вкуса.", show_alert=True)
				return
			item.quantity += qty
		else:
			unit = _calc_price(product, qty)
			item = OrderItem(order_id=order.id, product_id=product_id, quantity=qty, unit_price=unit)
			session.add(item)
		await session.commit()
	
	# Show confirmation message with "Go to cart" button
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	from aiogram.types import InlineKeyboardButton
	
	confirmation_text = f"✅ Товар '{product.title}' добавлен в корзину!\n\nКоличество: {qty}\nЦена: {float(product.price):.2f}"
	
	builder = InlineKeyboardBuilder()
	builder.row(InlineKeyboardButton(text="🛒 Перейти в корзину", callback_data="cart:view"))
	builder.row(InlineKeyboardButton(text="🏷️ Продолжить покупки", callback_data="catalog:open"))
	
	await callback.message.answer(confirmation_text, reply_markup=builder.as_markup())
	await _safe_answer(callback)


@router.callback_query(F.data.startswith("qty:"))
async def qty_change(callback: CallbackQuery) -> None:
	# data: qty:<inc|dec>:<product_id>:<qty>
	parts = (callback.data or "").split(":")
	action = parts[1]
	product_id = int(parts[2])
	qty = int(parts[3]) if len(parts) > 3 else 1
	qty = qty + 1 if action == "inc" else max(1, qty - 1)
	
	async with SessionLocal() as session:
		product = await _load_product(session, product_id)
		if not product:
			await callback.answer("Товар не найден", show_alert=True)
			return
		
		# Check if product has flavors
		from app.models.flavor import Flavor
		flavors_res = await session.execute(select(Flavor).where(Flavor.product_id == product_id, Flavor.is_available == True))
		flavors = list(flavors_res.scalars().all())
		has_flavors = bool(flavors)
	
	text_lines = _product_text(product, qty)
	
	# Add flavors info right after description (same logic as in open_product)
	if has_flavors:
		# Find the right position to insert flavors info
		# If there's a description, insert after it; otherwise, insert after title
		if product.description:
			insert_pos = 3  # After description
		else:
			insert_pos = 2  # After title
		
		text_lines.insert(insert_pos, "")  # Add empty line
		text_lines.insert(insert_pos + 1, "🍃 <b>Доступные вкусы:</b>")
		for flavor in flavors:
			text_lines.insert(insert_pos + 2, f"• {flavor.name}")
		text_lines.insert(insert_pos + 2 + len(flavors), "")  # Add empty line after flavors
		text_lines.insert(insert_pos + 3 + len(flavors), "Выберите вкус и количество, затем добавьте в корзину")
	
	kb = product_view_keyboard(product.id, product.category_id, qty, enabled=getattr(product, "in_stock", True), has_flavors=has_flavors)
	
	try:
		await callback.message.edit_caption(caption="\n".join(text_lines), reply_markup=kb.as_markup())
	except TelegramBadRequest:
		await _safe_edit(callback, "\n".join(text_lines), reply_markup=kb.as_markup())
	await _safe_answer(callback)


@router.callback_query(F.data == "nav:home")
async def nav_home(callback: CallbackQuery) -> None:
	# Answer early to avoid "query is too old" if subsequent ops take time
	try:
		await _safe_answer(callback)
	except Exception:
		pass
	user_id = callback.from_user.id  
	is_admin = False
	if settings.admin_ids:
		try:
			is_admin = user_id in {int(x.strip()) for x in settings.admin_ids.split(",") if x.strip()}
		except Exception:
			is_admin = False	
	from app.core.config import settings as __settings
	from app.models.branding import Branding as _Branding
	logo_id = __settings.logo_file_id
	welcome_text = __settings.welcome_text or "Добро пожаловать! Выберите раздел ниже, чтобы начать покупки."
	try:
		async with SessionLocal() as session:
			res = await session.execute(select(_Branding).where(_Branding.id == 1))
			b = res.scalars().first()
			if b:
				logo_id = b.logo_file_id or logo_id
				welcome_text = b.welcome_text or welcome_text
	except Exception:
		pass
	if logo_id:
		# Always ensure the main screen shows the logo image
		try:
			await callback.message.delete()
		except Exception:
			pass
		try:
			await callback.message.answer_photo(logo_id, caption=welcome_text, reply_markup=main_menu_keyboard(is_admin).as_markup())
		except TelegramBadRequest:
			await _safe_edit(callback, welcome_text, reply_markup=main_menu_keyboard(is_admin).as_markup())
	else:
		await _safe_edit(callback, welcome_text, reply_markup=main_menu_keyboard(is_admin).as_markup())


@router.callback_query(F.data == "info:open")
async def info_open(callback: CallbackQuery) -> None:
	await _safe_edit(callback, "Раздел: ℹ️ О нас\n\nВыберите тему:", reply_markup=info_menu_keyboard().as_markup())
	await _safe_answer(callback)


@router.callback_query(F.data.startswith("info:item:"))
async def info_item(callback: CallbackQuery) -> None:
	key = (callback.data or "").split(":", 2)[-1]  # type: ignore[union-attr]
	from app.bot.keyboards.inline import info_item_keyboard
	texts: dict[str, str] = {
		"about": (
			"<b>О нас</b>\n\n"
			"Мы — команда, которая любит качественные товары и честный сервис. "
			"Собираем ассортимент, проверяем поставщиков и быстро доставляем. "
			"Наша цель — чтобы ваш опыт покупки был простым, удобным и приятным."
		),
		"packaging": (
			"<b>Упаковка</b>\n\n"
			"Мы упаковываем товары в неприметные коробки без опознавательных знаков. "
			"Содержимое не указано на упаковке. Бережная защита от повреждений во время доставки."
		),
		"wholesale": (
			"<b>Скидки для оптовых покупателей</b>\n\n"
			"При крупных заказах действуют персональные условия. "
			"Скидки зависят от объёма и регулярности закупок. Напишите нам для расчёта."
		),
		"privacy": (
			"<b>Почему мы запрашиваем телефон и адрес</b>\n\n"
			"Эти данные нужны для подтверждения заказа и корректной доставки. "
			"Телефон — чтобы уточнить детали, адрес — чтобы доставить вовремя. "
			"Мы не передаём данные третьим лицам и используем их только для выполнения заказа."
		),
	}
	if key == "reviews":
		from sqlalchemy import select
		from app.db.session import SessionLocal
		from app.models.review import Review
		async with SessionLocal() as session:
			res = await session.execute(select(Review).order_by(Review.created_at.desc()).limit(10))
			reviews = list(res.scalars().all())
		if not reviews:
			await _safe_edit(callback, "Пока нет отзывов", reply_markup=info_item_keyboard().as_markup())
			await _safe_answer(callback)
			return
		for r in reviews:
			try:
				if r.media_type == "photo":
					await callback.message.answer_photo(r.file_id, caption=r.caption or "")
				else:
					await callback.message.answer_video(r.file_id, caption=r.caption or "")
			except Exception:
				pass
		await callback.message.answer("Это последние отзывы", reply_markup=info_item_keyboard().as_markup())
		await _safe_answer(callback)
		return
	text = texts.get(key, "Раздел не найден")
	await _safe_edit(callback, text, reply_markup=info_item_keyboard().as_markup())
	await _safe_answer(callback)


@router.callback_query(F.data == "nav:categories")
async def nav_categories(callback: CallbackQuery) -> None:
	async with SessionLocal() as session:
		categories = await _load_categories(session)
	if not categories:
		await _safe_edit(callback, "Категории пока не добавлены.")
		await _safe_answer(callback)
		return
	kb = categories_keyboard_with_nav([(c.id, c.name) for c in categories])
	await _safe_edit(callback, "Выберите категорию:", reply_markup=kb.as_markup())
	await _safe_answer(callback)


@router.callback_query(F.data.startswith("nav:category:"))
async def nav_category(callback: CallbackQuery) -> None:
	# answer early so the spinner stops immediately
	try:
		await _safe_answer(callback)
	except Exception:
		pass
	parts = (callback.data or "").split(":")  # type: ignore[union-attr]
	category_id = int(parts[-1])
	async with SessionLocal() as session:
		# Get category name first
		cat_res = await session.execute(select(Category).where(Category.id == category_id))
		category = cat_res.scalars().first()
		if not category:
			await _safe_edit(callback, "Категория не найдена.")
			try:
				await _safe_answer(callback)
			except TelegramBadRequest:
				pass
			return
		
		# Get products
		res = await session.execute(
			select(Product)
			.where(Product.category_id == category_id, Product.is_deleted == False)
			.order_by(Product.title)
		)
		products = list(res.scalars().all())
	
	if not products:
		await _safe_edit(callback, "В этой категории пока нет товаров.")
		try:
			await _safe_answer(callback)
		except TelegramBadRequest:
			pass  # Ignore old query errors
		return
	
	from app.bot.keyboards.inline import products_keyboard_with_nav as _kb
	kb = _kb([(p.id, p.title) for p in products], category_id)
	# If current message is a photo (product view), always replace with a text message
	if callback.message.photo:
		try:
			await callback.message.delete()
		except Exception:
			pass
		await callback.message.answer("Выберите товар:", reply_markup=kb.as_markup())
	else:
		await _safe_edit(callback, "Выберите товар:", reply_markup=kb.as_markup())
	try:
		await _safe_answer(callback)
	except TelegramBadRequest:
		pass  # Ignore old query errors


async def _load_product(session: AsyncSession, product_id: int) -> Product | None:
	result = await session.execute(select(Product).where(Product.id == product_id, getattr(Product, "is_deleted", False) == False))
	return result.scalars().first()


# --- Cart view and clear ---
from app.bot.keyboards.inline import cart_actions_keyboard


@router.callback_query(F.data == "cart:view")
async def cart_view(callback: CallbackQuery) -> None:
	user_id = callback.from_user.id  # type: ignore[union-attr]
	async with SessionLocal() as session:
		res = await session.execute(select(Order).where(Order.user_id == user_id, Order.status == "new"))
		order = res.scalars().first()
		if not order:
			await _safe_edit(callback, "Корзина пуста", reply_markup=cart_actions_keyboard().as_markup())
			await _safe_answer(callback)
			return
		
		# Load order items with products and flavors
		from app.models.flavor import Flavor
		res_items = await session.execute(
			select(OrderItem, Product, Flavor)
			.join(Product, Product.id == OrderItem.product_id)
			.outerjoin(Flavor, Flavor.id == OrderItem.flavor_id)
			.where(OrderItem.order_id == order.id)
		)
		pairs = list(res_items.all())
		
		# Create list of (OrderItem, Product, Flavor) tuples
		items_with_flavors = []
		for item, product, flavor in pairs:
			if flavor:
				item.flavor = flavor
			items_with_flavors.append((item, product))
		
		text = _format_cart(order, items_with_flavors)
	await _safe_edit(callback, text, reply_markup=cart_actions_keyboard().as_markup())
	await _safe_answer(callback)


def _format_cart(order: Order, items: list[tuple[OrderItem, Product]]) -> str:
	total = 0.0
	lines: list[str] = ["🛒 <b>КОРЗИНА</b>", ""]
	
	for i, (item, product) in enumerate(items, 1):
		unit = _calc_price(product, item.quantity)
		sum_ = unit * item.quantity
		total += sum_
		
		# Add item number and separator
		lines.append(f"<b>{i}.</b>")
		lines.append(f"📦 {product.title}")
		
		# Add flavor information if available
		if hasattr(item, 'flavor') and item.flavor:
			lines.append(f"🍃 Вкус: {item.flavor.name}")
		
		lines.append(f"   Количество: {item.quantity}")
		lines.append(f"   Цена за шт: {unit:.2f}")
		lines.append(f"   Сумма: <b>{sum_:.2f}</b>")
		
		# Add separator between items (except after last item)
		if i < len(items):
			lines.append("")
	
	# Add total section
	lines.append("")
	lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
	lines.append(f"<b>ИТОГО: {total:.2f}</b>")
	
	return "\n".join(lines)


@router.callback_query(F.data == "cart:clear")
async def cart_clear(callback: CallbackQuery) -> None:
	user_id = callback.from_user.id  # type: ignore[union-attr]
	async with SessionLocal() as session:
		res = await session.execute(select(Order.id).where(Order.user_id == user_id, Order.status == "new"))
		order_id = res.scalars().first()
		if order_id is not None:
			await session.execute(delete(OrderItem).where(OrderItem.order_id == order_id))
			await session.commit()
	await _safe_edit(callback, "Корзина очищена", reply_markup=cart_actions_keyboard().as_markup())
	await _safe_answer(callback)


class CheckoutStates(StatesGroup):
	phone = State()
	confirm = State()


@router.callback_query(F.data == "cart:checkout")
async def checkout_start(callback: CallbackQuery, state: FSMContext) -> None:
	await state.clear()
	await state.set_state(CheckoutStates.phone)
	# Offer contact sharing via reply keyboard
	kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
	try:
		await callback.message.answer("Отправьте телефон или нажмите '📱 Поделиться контактом'", reply_markup=kb)
	except Exception:
		await _safe_edit(callback, "Отправьте телефон или нажмите '📱 Поделиться контактом'")
	await _safe_answer(callback)


@router.message(CheckoutStates.phone, F.contact)
async def checkout_phone_contact(message: Message, state: FSMContext) -> None:
	phone = getattr(message.contact, "phone_number", "") if getattr(message, "contact", None) else ""
	if not phone:
		await message.answer("Не удалось получить контакт. Введите номер вручную")
		return
	await state.update_data(phone=phone)
	await state.set_state(CheckoutStates.confirm)
	await message.answer("Подтвердите оформление заказа: отправьте 'Да' или 'Нет'", reply_markup=ReplyKeyboardRemove())


@router.message(CheckoutStates.phone)
async def checkout_phone(message: Message, state: FSMContext) -> None:
	phone = (message.text or "").strip()
	if not phone:
		await message.answer("Введите телефон")
		return
	await state.update_data(phone=phone)
	user_id = message.from_user.id  # type: ignore[union-attr]
	# save phone to user profile
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(User).where(User.id == user_id))
			u = res.scalars().first()
			if u:
				u.first_name = message.from_user.first_name if message.from_user else u.first_name  # type: ignore[union-attr]
				u.last_name = message.from_user.last_name if message.from_user else u.last_name  # type: ignore[union-attr]
				u.phone = phone
	await state.set_state(CheckoutStates.confirm)
	await message.answer("Подтвердите оформление заказа: отправьте 'Да' или 'Нет'", reply_markup=ReplyKeyboardRemove())


@router.message(CheckoutStates.confirm)
async def checkout_confirm(message: Message, state: FSMContext) -> None:
	if (message.text or "").strip().lower() not in {"да", "yes", "y", "ok"}:
		await message.answer("Отменено")
		await state.clear()
		return
	data = await state.get_data()
	user_id = message.from_user.id  # type: ignore[union-attr]
	async with SessionLocal() as session:
		# load cart
		res = await session.execute(select(Order).where(Order.user_id == user_id, Order.status == "new"))
		order = res.scalars().first()
		if not order:
			await message.answer("Корзина пуста")
			await state.clear()
			return
		res_items = await session.execute(
			select(OrderItem, Product)
				.join(Product, Product.id == OrderItem.product_id)
				.where(OrderItem.order_id == order.id)
		)
		pairs = list(res_items.all())
		if not pairs:
			await message.answer("Корзина пуста")
			await state.clear()
			return
		order.status = "submitted"
		order.customer_name = None  # type: ignore[assignment]
		order.customer_phone = data.get("phone")  # type: ignore[assignment]
		await session.commit()
	await state.clear()
	from app.bot.keyboards.inline import main_menu_keyboard as _main_kb
	await message.answer("Заказ оформлен ✅", reply_markup=_main_kb(is_admin=False).as_markup())
	text_lines = [f"Новый заказ #{order.id}", f"Телефон: {data.get('phone')}", ""]
	for item, product in pairs:
		text_lines.append(
			f"{product.title} — {item.quantity} x {float(item.unit_price):.2f} = {float(item.unit_price) * item.quantity:.2f}"
		)
	text = "\n".join(text_lines)
	from app.models.manager import Manager
	async with SessionLocal() as session:
		res = await session.execute(select(Manager.user_id))
		manager_ids = [row[0] for row in res.all()]
	if not manager_ids and getattr(settings, "manager_chat_id", None):
		manager_ids = [int(settings.manager_chat_id)]
	from app.bot.keyboards.inline import manager_order_keyboard
	kb = manager_order_keyboard(user_id)
	for mid in manager_ids:
		try:
			await message.bot.send_message(mid, text, reply_markup=kb.as_markup())
		except Exception:
			pass


@router.callback_query(F.data.startswith("flavor:select:"))
async def flavor_select(callback: CallbackQuery) -> None:
	# data format: flavor:select:<product_id>:<qty>
	parts = (callback.data or "").split(":")
	product_id = int(parts[2])
	qty = int(parts[3]) if len(parts) > 3 else 1
	
	async with SessionLocal() as session:
		product = await _load_product(session, product_id)
		if not product:
			await _safe_edit(callback, "Товар не найден.")
			await _safe_answer(callback)
			return
		
		# Get available flavors
		from app.models.flavor import Flavor
		flavors_res = await session.execute(select(Flavor).where(Flavor.product_id == product_id, Flavor.is_available == True))
		flavors = list(flavors_res.scalars().all())
		
		if not flavors:
			await _safe_edit(callback, "Вкусы не найдены.")
			await _safe_answer(callback)
			return
	
	# Create flavor selection keyboard
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	from aiogram.types import InlineKeyboardButton
	
	builder = InlineKeyboardBuilder()
	for flavor in flavors:
		# Pass current quantity to preserve it when selecting flavor
		builder.row(InlineKeyboardButton(text=f"🍃 {flavor.name}", callback_data=f"flavor:choose:{product_id}:{flavor.id}:{qty}"))
	
	builder.row(InlineKeyboardButton(text="⬅️ Назад к товару", callback_data=f"product:{product_id}"))
	
	await _safe_edit(callback, f"Выберите вкус для товара '{product.title}':", reply_markup=builder.as_markup())
	await _safe_answer(callback)


@router.callback_query(F.data.startswith("flavor:choose:"))
async def flavor_choose(callback: CallbackQuery) -> None:
	# data format: flavor:choose:<product_id>:<flavor_id>:<qty>
	parts = (callback.data or "").split(":")
	product_id = int(parts[2])
	flavor_id = int(parts[3])
	qty = int(parts[4]) if len(parts) > 4 else 1
	
	async with SessionLocal() as session:
		# Get product and flavor
		product = await _load_product(session, product_id)
		from app.models.flavor import Flavor
		flavor_res = await session.execute(select(Flavor).where(Flavor.id == flavor_id, Flavor.product_id == product_id))
		flavor = flavor_res.scalars().first()
		
		if not product or not flavor:
			await callback.answer("Товар или вкус не найден", show_alert=True)
			return
	
	# Show product with selected flavor and quantity controls
	text_lines = _product_with_flavor_text(product, flavor, qty)
	kb = flavor_selection_keyboard(product_id, flavor_id, qty=qty, enabled=getattr(product, "in_stock", True))
	
	# Check if message has photo or just text
	if callback.message.photo:
		# If message has photo, update caption
		try:
			await callback.message.edit_caption(caption="\n".join(text_lines), reply_markup=kb.as_markup())
		except TelegramBadRequest:
			# If edit_caption fails, try to send new photo message
			try:
				await callback.message.delete()
				# Use product photo if available, otherwise use current message photo
				photo_to_use = product.photo_file_id if product.photo_file_id else callback.message.photo[-1].file_id
				await callback.message.bot.send_photo(
					chat_id=callback.message.chat.id,
					photo=photo_to_use, 
					caption="\n".join(text_lines), 
					reply_markup=kb.as_markup()
				)
			except Exception:
				await _safe_edit(callback, "\n".join(text_lines), reply_markup=kb.as_markup())
	else:
		# If message is just text, but product has photo, send photo message
		if product.photo_file_id:
			try:
				await callback.message.delete()
				await callback.message.bot.send_photo(
					chat_id=callback.message.chat.id,
					photo=product.photo_file_id, 
					caption="\n".join(text_lines), 
					reply_markup=kb.as_markup()
				)
			except Exception:
				await _safe_edit(callback, "\n".join(text_lines), reply_markup=kb.as_markup())
		else:
			# If message is just text, update text
			await _safe_edit(callback, "\n".join(text_lines), reply_markup=kb.as_markup())
	
	await _safe_answer(callback)


@router.callback_query(F.data.startswith("flavor:qty:"))
async def flavor_qty_change(callback: CallbackQuery) -> None:
	# data: flavor:qty:<inc|dec>:<product_id>:<flavor_id>:<qty>
	parts = (callback.data or "").split(":")
	action = parts[2]
	product_id = int(parts[3])
	flavor_id = int(parts[4])
	qty = int(parts[5])
	
	if action == "inc":
		qty += 1
	elif action == "dec":
		qty = max(1, qty - 1)
	
	async with SessionLocal() as session:
		product = await _load_product(session, product_id)
		from app.models.flavor import Flavor
		flavor_res = await session.execute(select(Flavor).where(Flavor.id == flavor_id, Flavor.product_id == product_id))
		flavor = flavor_res.scalars().first()
		
		if not product or not flavor:
			await callback.answer("Товар или вкус не найден", show_alert=True)
			return
	
	# Update keyboard with new quantity
	text_lines = _product_with_flavor_text(product, flavor, qty)
	kb = flavor_selection_keyboard(product_id, flavor_id, qty=qty, enabled=getattr(product, "in_stock", True))
	
	# Check if message has photo or just text
	if callback.message.photo:
		# If message has photo, update caption
		try:
			await callback.message.edit_caption(caption="\n".join(text_lines), reply_markup=kb.as_markup())
		except TelegramBadRequest:
			# If edit_caption fails, try to send new photo message
			try:
				await callback.message.delete()
				# Use product photo if available, otherwise use current message photo
				photo_to_use = product.photo_file_id if product.photo_file_id else callback.message.photo[-1].file_id
				await callback.message.bot.send_photo(
					chat_id=callback.message.chat.id,
					photo=photo_to_use, 
					caption="\n".join(text_lines), 
					reply_markup=kb.as_markup()
				)
			except Exception:
				await _safe_edit(callback, "\n".join(text_lines), reply_markup=kb.as_markup())
	else:
		# If message is just text, update text
		try:
			await callback.message.edit_text("\n".join(text_lines), reply_markup=kb.as_markup())
		except TelegramBadRequest:
			await _safe_edit(callback, "\n".join(text_lines), reply_markup=kb.as_markup())
	
	await _safe_answer(callback)


@router.callback_query(F.data.startswith("flavor:add:"))
async def flavor_add_to_cart(callback: CallbackQuery) -> None:
	# data format: flavor:add:<product_id>:<flavor_id>:<qty>
	parts = (callback.data or "").split(":")
	product_id = int(parts[2])
	flavor_id = int(parts[3])
	qty = int(parts[4]) if len(parts) > 4 else 1
	
	async with SessionLocal() as session:
		# Get product and flavor
		product = await _load_product(session, product_id)
		from app.models.flavor import Flavor
		flavor_res = await session.execute(select(Flavor).where(Flavor.id == flavor_id, Flavor.product_id == product_id))
		flavor = flavor_res.scalars().first()
		
		if not product or not flavor:
			await callback.answer("Товар или вкус не найден", show_alert=True)
			return
		
		# Add to cart with flavor
		user_id = callback.from_user.id
		
		# Check if user exists, create if not
		res_user = await session.execute(select(User).where(User.id == user_id))
		if res_user.scalars().first() is None:
			session.add(User(id=user_id))
			await session.flush()
		
		# Get or create order
		result = await session.execute(
			select(Order).where(Order.user_id == user_id, Order.status == "new")
		)
		order = result.scalars().first()
		if not order:
			order = Order(user_id=user_id, status="new")
			session.add(order)
			await session.flush()
		
		# Check if item with same product and flavor already exists
		item_res = await session.execute(
			select(OrderItem).where(
				OrderItem.order_id == order.id, 
				OrderItem.product_id == product_id,
				OrderItem.flavor_id == flavor_id
			)
		)
		item = item_res.scalars().first()
		
		if item:
			item.quantity += qty
		else:
			unit = _calc_price(product, qty)
			item = OrderItem(
				order_id=order.id, 
				product_id=product_id, 
				flavor_id=flavor_id,
				quantity=qty, 
				unit_price=unit
			)
			session.add(item)
		
		await session.commit()
	
	# Show confirmation message
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	from aiogram.types import InlineKeyboardButton
	
	confirmation_text = f"✅ Товар '{product.title}' (вкус: {flavor.name}) добавлен в корзину!\n\nКоличество: {qty}\nЦена: {float(product.price):.2f}"
	
	builder = InlineKeyboardBuilder()
	builder.row(InlineKeyboardButton(text="🛒 Перейти в корзину", callback_data="cart:view"))
	builder.row(InlineKeyboardButton(text="🏷️ Продолжить покупки", callback_data="catalog:open"))
	
	await callback.message.bot.send_message(
		chat_id=callback.message.chat.id,
		text=confirmation_text, 
		reply_markup=builder.as_markup()
	)
	await _safe_answer(callback)


