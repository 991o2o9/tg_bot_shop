from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


def catalog_keyboard() -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	builder.button(text="🏷️ Каталог", callback_data="catalog:open")
	return builder



def product_qty_keyboard(product_id: int, qty: int = 1, enabled: bool = True) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	builder.row(
		InlineKeyboardButton(text="➖", callback_data=f"qty:dec:{product_id}:{qty}"),
		InlineKeyboardButton(text=f"{qty}", callback_data="noop"),
		InlineKeyboardButton(text="➕", callback_data=f"qty:inc:{product_id}:{qty}"),
	)
	btn_text = "🛒 В корзину" if enabled else "❌ Нет в наличии"
	btn_cb = f"cart:add:{product_id}:{qty}" if enabled else "noop"
	builder.row(InlineKeyboardButton(text=btn_text, callback_data=btn_cb))
	return builder



def categories_keyboard(categories: list[tuple[int, str]]) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	for category_id, category_name in categories:
		builder.button(text=f"📂 {category_name}", callback_data=f"category:{category_id}")
	builder.adjust(2)
	return builder



def products_keyboard(products: list[tuple[int, str]]) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	for product_id, product_title in products:
		builder.button(text=f"📦 {product_title}", callback_data=f"product:{product_id}")
	builder.adjust(1)
	return builder



def admin_categories_keyboard(categories: list[tuple[int, str]]) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	for category_id, category_name in categories:
		builder.button(text=f"📂 {category_name}", callback_data=f"admincat:{category_id}")
	builder.adjust(2)
	return builder



def main_menu_keyboard(is_admin: bool) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	builder.button(text="🏷️ Каталог", callback_data="catalog:open")
	builder.button(text="🛒 Корзина", callback_data="cart:view")
	builder.button(text="ℹ️ О нас", callback_data="info:open")
	if is_admin:
		builder.button(text="⚙️ Админ", callback_data="admin:open")
	builder.adjust(2)
	return builder



def admin_menu_keyboard() -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	builder.row(
		InlineKeyboardButton(text="➕📦 Товар", callback_data="admin:product:add"),
		InlineKeyboardButton(text="➕📂 Категория", callback_data="admin:category:add"),
	)
	builder.row(
		InlineKeyboardButton(text="📋 Категории", callback_data="admin:category:list"),
		InlineKeyboardButton(text="📦 Товары", callback_data="admin:products"),
	)
	builder.row(
		InlineKeyboardButton(text="🗃 Архив товаров", callback_data="admin:products:archived"),
	)
	builder.row(
		InlineKeyboardButton(text="⭐ Добавить отзыв", callback_data="admin:review:add"),
		InlineKeyboardButton(text="🗂 Отзывы", callback_data="admin:reviews"),
	)
	builder.row(
		InlineKeyboardButton(text="📣 Уведомление", callback_data="admin:notify"),
	)
	builder.row(
		InlineKeyboardButton(text="🎨 Брендинг", callback_data="admin:branding"),
	)
	builder.row(
		InlineKeyboardButton(text="👥 Менеджеры", callback_data="admin:managers"),
	)
	builder.row(
		InlineKeyboardButton(text="🏠 Главная", callback_data="nav:home"),
	)
	return builder



def categories_keyboard_with_nav(categories: list[tuple[int, str]]) -> InlineKeyboardBuilder:
	builder = categories_keyboard(categories)
	builder.row(
		InlineKeyboardButton(text="🏠 Главная", callback_data="nav:home"),
	)
	return builder



def products_keyboard_with_nav(products: list[tuple[int, str]], category_id: int) -> InlineKeyboardBuilder:
	builder = products_keyboard(products)
	builder.row(
		InlineKeyboardButton(text="⬅️ К категориям", callback_data="nav:categories"),
		InlineKeyboardButton(text="🏠 Главная", callback_data="nav:home"),
	)
	return builder



def product_view_keyboard(product_id: int, category_id: int | None, qty: int = 1, enabled: bool = True, has_flavors: bool = False) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	
	# Add quantity controls
	builder.row(
		InlineKeyboardButton(text="➖", callback_data=f"qty:dec:{product_id}:{qty}"),
		InlineKeyboardButton(text=f"{qty}", callback_data="noop"),
		InlineKeyboardButton(text="➕", callback_data=f"qty:inc:{product_id}:{qty}"),
	)
	
	# If product has flavors, show flavor selection first and disable add to cart
	if has_flavors:
		builder.row(InlineKeyboardButton(text="🍃 Выбрать вкус", callback_data=f"flavor:select:{product_id}:{qty}"))
		# Add to cart button is disabled until flavor is selected
		builder.row(InlineKeyboardButton(text="❌ Сначала выберите вкус", callback_data="noop"))
	else:
		# Standard add to cart button for products without flavors
		btn_text = "🛒 В корзину" if enabled else "❌ Нет в наличии"
		btn_cb = f"cart:add:{product_id}:{qty}" if enabled else "noop"
		builder.row(InlineKeyboardButton(text=btn_text, callback_data=btn_cb))
	
	if category_id is not None:
		builder.row(
			InlineKeyboardButton(text="⬅️ К товарам", callback_data=f"nav:category:{category_id}"),
			InlineKeyboardButton(text="🏠 Главная", callback_data="nav:home"),
		)
	else:
		builder.row(
			InlineKeyboardButton(text="⬅️ К категориям", callback_data="nav:categories"),
			InlineKeyboardButton(text="🏠 Главная", callback_data="nav:home"),
		)
	return builder



def flavor_selection_keyboard(product_id: int, flavor_id: int, qty: int = 1, enabled: bool = True) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	
	# Add quantity controls
	builder.row(
		InlineKeyboardButton(text="➖", callback_data=f"flavor:qty:dec:{product_id}:{flavor_id}:{qty}"),
		InlineKeyboardButton(text=f"{qty}", callback_data="noop"),
		InlineKeyboardButton(text="➕", callback_data=f"flavor:qty:inc:{product_id}:{flavor_id}:{qty}"),
	)
	
	# Add to cart button with flavor
	btn_text = "🛒 В корзину" if enabled else "❌ Нет в наличии"
	btn_cb = f"flavor:add:{product_id}:{flavor_id}:{qty}" if enabled else "noop"
	builder.row(InlineKeyboardButton(text=btn_text, callback_data=btn_cb))
	
	# Change flavor button
	builder.row(InlineKeyboardButton(text="🍃 Изменить вкус", callback_data=f"flavor:select:{product_id}:{qty}"))
	
	# Back to product button
	builder.row(InlineKeyboardButton(text="⬅️ Назад к товару", callback_data=f"product:{product_id}"))
	
	return builder



def cart_actions_keyboard() -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	builder.row(
		InlineKeyboardButton(text="✅ Оформить", callback_data="cart:checkout"),
		InlineKeyboardButton(text="🧹 Очистить", callback_data="cart:clear"),
	)
	builder.row(
		InlineKeyboardButton(text="🏷️ Каталог", callback_data="catalog:open"),
		InlineKeyboardButton(text="🏠 Главная", callback_data="nav:home"),
	)
	return builder



def admin_products_keyboard(products: list[tuple[int, str]]) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	for product_id, title in products:
		builder.button(text=f"📦 {title}", callback_data=f"adminprod:{product_id}")
	builder.adjust(1)
	builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:open"))
	return builder



def admin_product_edit_keyboard(product_id: int) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	builder.row(
		InlineKeyboardButton(text="✏️ Название", callback_data=f"admin:edit:title:{product_id}"),
		InlineKeyboardButton(text="📝 Описание", callback_data=f"admin:edit:desc:{product_id}"),
	)
	builder.row(
		InlineKeyboardButton(text="🖼 Фото", callback_data=f"admin:edit:photo:{product_id}"),
		InlineKeyboardButton(text="💵 Цена", callback_data=f"admin:edit:price:{product_id}"),
	)
	builder.row(
		InlineKeyboardButton(text="🏷 Категория", callback_data=f"admin:edit:category:{product_id}"),
	)
	builder.row(
		InlineKeyboardButton(text="🍃 Вкусы", callback_data=f"admin:edit:flavors:{product_id}"),
	)
	builder.row(
		InlineKeyboardButton(text="🗃 В архив", callback_data=f"admin:product:delete:{product_id}"),
	)
	builder.row(
		InlineKeyboardButton(text="↩️ Назад", callback_data="admin:products"),
	)
	return builder



def manager_order_keyboard(user_id: int) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	builder.row(
		InlineKeyboardButton(text="✉️ Написать клиенту", url=f"tg://user?id={user_id}"),
	)
	return builder



def info_menu_keyboard() -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	builder.row(
		InlineKeyboardButton(text="ℹ️ О нас", callback_data="info:item:about"),
	)
	builder.row(
		InlineKeyboardButton(text="🎁 Упаковка", callback_data="info:item:packaging"),
	)
	builder.row(
		InlineKeyboardButton(text="💸 Скидки для оптовиков", callback_data="info:item:wholesale"),
	)
	builder.row(
		InlineKeyboardButton(text="📱 Почему запрашиваем телефон и адрес", callback_data="info:item:privacy"),
	)
	builder.row(
		InlineKeyboardButton(text="⭐ Отзывы", callback_data="info:item:reviews"),
	)
	builder.row(
		InlineKeyboardButton(text="🏠 Главная", callback_data="nav:home"),
	)
	return builder



def info_item_keyboard() -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	builder.row(
		InlineKeyboardButton(text="⬅️ К разделу 'ℹ️ О нас'", callback_data="info:open"),
		InlineKeyboardButton(text="🏠 Главная", callback_data="nav:home"),
	)
	return builder


def admin_flavors_keyboard(product_id: int, flavors: list) -> InlineKeyboardBuilder:
	builder = InlineKeyboardBuilder()
	
	# Show current flavors
	if flavors:
		for flavor in flavors:
			builder.button(
				text=f"🍃 {flavor.name} {'✅' if flavor.is_available else '❌'}", 
				callback_data=f"admin:flavor:toggle:{product_id}:{flavor.id}"
			)
		builder.adjust(1)
		builder.row(
			InlineKeyboardButton(text="🗑 Удалить все", callback_data=f"admin:flavor:delete:{product_id}"),
		)
	else:
		builder.button(text="➕ Добавить первый вкус", callback_data=f"admin:flavor:add:{product_id}")
	
	builder.row(
		InlineKeyboardButton(text="➕ Добавить вкус", callback_data=f"admin:flavor:add:{product_id}"),
		InlineKeyboardButton(text="↩️ Назад", callback_data=f"adminprod:{product_id}"),
	)
	
	return builder
