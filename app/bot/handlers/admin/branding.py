from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from aiogram.exceptions import TelegramBadRequest

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.branding import Branding
from app.bot.keyboards.inline import admin_menu_keyboard


router = Router(name="admin_branding")
async def _safe_edit_cb(callback: CallbackQuery, text: str, reply_markup=None) -> None:
	try:
		await callback.message.edit_text(text, reply_markup=reply_markup)
	except TelegramBadRequest:
		await callback.message.answer(text, reply_markup=reply_markup)


async def _safe_answer(callback: CallbackQuery) -> None:
	"""Safely call callback.answer() with error handling for old queries."""
	try:
		await _safe_answer(callback)
	except TelegramBadRequest:
		pass  # Ignore old query errors


def _is_admin(user_id: int) -> bool:
	if not settings.admin_ids:
		return False
	admin_id_set = {int(x.strip()) for x in settings.admin_ids.split(",") if x.strip()}
	return user_id in admin_id_set


class BrandingStates(StatesGroup):
	wait_logo = State()
	wait_text = State()


async def _get_or_create_branding() -> Branding:
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Branding).where(Branding.id == 1))
			branding = res.scalars().first()
			if branding is None:
				branding = Branding(id=1, logo_file_id=None, welcome_text=None)
				session.add(branding)
		return branding


@router.callback_query(F.data == "admin:branding")
async def open_branding(callback: CallbackQuery) -> None:
	# answer early to avoid stale query
	try:
		await _safe_answer(callback)
	except Exception:
		pass
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	# show current settings
	async with SessionLocal() as session:
		res = await session.execute(select(Branding).where(Branding.id == 1))
		branding = res.scalars().first()
	text_lines = ["Брендинг"]
	if branding and branding.welcome_text:
		text_lines.append(f"Текущий текст: {branding.welcome_text}")
	if branding and branding.logo_file_id:
		text_lines.append("Логотип: установлен")
	else:
		text_lines.append("Логотип: не задан")
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	builder = InlineKeyboardBuilder()
	builder.button(text="🖼 Задать логотип", callback_data="admin:branding:set_logo")
	builder.button(text="✏️ Изменить приветствие", callback_data="admin:branding:set_text")
	builder.button(text="↩️ Назад", callback_data="admin:open")
	builder.adjust(2)
	await _safe_edit_cb(callback, "\n".join(text_lines), reply_markup=builder.as_markup())
	# already answered above


@router.callback_query(F.data == "admin:branding:set_logo")
async def branding_set_logo(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	await state.set_state(BrandingStates.wait_logo)
	await _safe_edit_cb(callback, "Отправьте фото логотипа (как фото)")
	await _safe_answer(callback)


@router.message(BrandingStates.wait_logo, F.photo)
async def branding_save_logo(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	file_id = message.photo[-1].file_id  # type: ignore[index]
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Branding).where(Branding.id == 1))
			branding = res.scalars().first()
			if branding is None:
				branding = Branding(id=1)
				session.add(branding)
			branding.logo_file_id = file_id
		await session.commit()
	await state.clear()
	await message.answer("Логотип обновлён", reply_markup=admin_menu_keyboard().as_markup())


@router.callback_query(F.data == "admin:branding:set_text")
async def branding_set_text(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	await state.set_state(BrandingStates.wait_text)
	await _safe_edit_cb(callback, "Отправьте новый приветственный текст")
	await _safe_answer(callback)


@router.message(BrandingStates.wait_text)
async def branding_save_text(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	text = (message.text or "").strip()
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Branding).where(Branding.id == 1))
			branding = res.scalars().first()
			if branding is None:
				branding = Branding(id=1)
				session.add(branding)
			branding.welcome_text = text
		await session.commit()
	await state.clear()
	await message.answer("Приветственный текст обновлён", reply_markup=admin_menu_keyboard().as_markup())


