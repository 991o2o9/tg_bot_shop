from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, delete
from aiogram.exceptions import TelegramBadRequest

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.manager import Manager
from app.bot.keyboards.inline import admin_menu_keyboard
from app.models.user import User


router = Router(name="admin_managers")


def _is_admin(user_id: int) -> bool:
	# Admins or listed managers have admin access to panel
	admin_id_set = set()
	if settings.admin_ids:
		admin_id_set = {int(x.strip()) for x in settings.admin_ids.split(",") if x.strip()}
	# Managers from DB
	try:
		from app.db.session import SessionLocal as _SL
		import asyncio
		# Use a quick sync check via cached managers list is not available; fallback to simple include check later in handlers
		# Here we only check static admins to keep _is_admin fast; runtime checks will be done in handlers where session exists
	except Exception:
		pass
	return user_id in admin_id_set


class ManagerStates(StatesGroup):
	wait_user_id = State()


async def _safe_edit_cb(callback: CallbackQuery, text: str, reply_markup=None) -> None:
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


@router.callback_query(F.data == "admin:managers")
async def managers_open(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	try:
		await _safe_answer(callback)
	except Exception:
		pass
	# list managers with inline delete buttons
	async with SessionLocal() as session:
		res = await session.execute(select(Manager).order_by(Manager.id))
		mans = list(res.scalars().all())
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	from aiogram.types import InlineKeyboardButton
	builder = InlineKeyboardBuilder()
	if not mans:
		text = "Менеджеры:\nПока не добавлено ни одного менеджера"
	else:
		text = "Менеджеры:"
		for m in mans:
			builder.row(
				InlineKeyboardButton(text=f"👤 {m.user_id}", callback_data="noop"),
				InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:managers:del:{m.user_id}"),
			)
	builder.row(InlineKeyboardButton(text="➕ Добавить", callback_data="admin:managers:add"))
	builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:open"))
	await _safe_edit_cb(callback, text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "admin:managers:add")
async def managers_add_start(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	await state.set_state(ManagerStates.wait_user_id)
	await _safe_edit_cb(callback, "Отправьте user_id менеджера (число). Он должен нажать /start боту.")
	await _safe_answer(callback)


@router.message(ManagerStates.wait_user_id)
async def managers_add_save(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	text = (message.text or "").strip()
	try:
		uid = int(text)
	except ValueError:
		await message.answer("Неверный формат. Отправьте числовой user_id", reply_markup=admin_menu_keyboard().as_markup())
		await state.clear()
		return
	async with SessionLocal() as session:
		async with session.begin():
			res = await session.execute(select(Manager).where(Manager.user_id == uid))
			if res.scalars().first():
				await message.answer("Такой менеджер уже есть", reply_markup=admin_menu_keyboard().as_markup())
				await state.clear()
				return
			m = Manager(user_id=uid)
			session.add(m)
		await session.commit()
	# Also grant admin rights at runtime
	try:
		ids = []
		if settings.admin_ids:
			ids = [x.strip() for x in settings.admin_ids.split(",") if x.strip()]
		if str(uid) not in ids:
			ids.append(str(uid))
		settings.admin_ids = ",".join(ids)
	except Exception:
		pass
	await state.clear()
	await message.answer("Менеджер добавлен", reply_markup=admin_menu_keyboard().as_markup())


@router.message(F.text.startswith("/delmanager"))
async def managers_delete(message: Message) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	parts = (message.text or "").split(maxsplit=1)
	if len(parts) < 2:
		await message.answer("Использование: /delmanager <user_id>", reply_markup=admin_menu_keyboard().as_markup())
		return
	try:
		uid = int(parts[1].strip())
	except ValueError:
		await message.answer("user_id должен быть числом", reply_markup=admin_menu_keyboard().as_markup())
		return
	async with SessionLocal() as session:
		await session.execute(delete(Manager).where(Manager.user_id == uid))
		await session.commit()
	# Also revoke admin rights at runtime
	try:
		if settings.admin_ids:
			ids = [x.strip() for x in settings.admin_ids.split(",") if x.strip()]
			ids = [x for x in ids if x != str(uid)]
			settings.admin_ids = ",".join(ids)
	except Exception:
		pass
	await message.answer("Менеджер удалён", reply_markup=admin_menu_keyboard().as_markup())


@router.callback_query(F.data.startswith("admin:managers:del:"))
async def managers_delete_cb(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	try:
		await _safe_answer(callback)
	except Exception:
		pass
	uid_str = (callback.data or "").rsplit(":", 1)[-1]
	try:
		uid = int(uid_str)
	except ValueError:
		await _safe_edit_cb(callback, "Некорректный user_id", reply_markup=admin_menu_keyboard().as_markup())
		return
	async with SessionLocal() as session:
		await session.execute(delete(Manager).where(Manager.user_id == uid))
		await session.commit()
	# Also revoke admin rights at runtime
	try:
		if settings.admin_ids:
			ids = [x.strip() for x in settings.admin_ids.split(",") if x.strip()]
			ids = [x for x in ids if x != str(uid)]
			settings.admin_ids = ",".join(ids)
	except Exception:
		pass
	# refresh list
	async with SessionLocal() as session:
		res = await session.execute(select(Manager).order_by(Manager.id))
		mans = list(res.scalars().all())
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	from aiogram.types import InlineKeyboardButton
	builder = InlineKeyboardBuilder()
	if not mans:
		text = "Менеджеры:\nПока не добавлено ни одного менеджера"
	else:
		text = "Менеджеры:"
		for m in mans:
			builder.row(
				InlineKeyboardButton(text=f"👤 {m.user_id}", callback_data="noop"),
				InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:managers:del:{m.user_id}"),
			)
	builder.row(InlineKeyboardButton(text="➕ Добавить", callback_data="admin:managers:add"))
	builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:open"))
	await _safe_edit_cb(callback, text + "\nУдалён ✅", reply_markup=builder.as_markup())


