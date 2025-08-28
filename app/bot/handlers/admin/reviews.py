from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, delete, func
from aiogram.exceptions import TelegramBadRequest

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.review import Review
from app.bot.keyboards.inline import admin_menu_keyboard


router = Router(name="admin_reviews")
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


def _is_admin(user_id: int) -> bool:
	if not settings.admin_ids:
		return False
	admin_id_set = {int(x.strip()) for x in settings.admin_ids.split(",") if x.strip()}
	return user_id in admin_id_set


class ReviewStates(StatesGroup):
	wait_media = State()
	wait_caption = State()


@router.callback_query(F.data == "admin:review:add")
async def review_add_open(callback: CallbackQuery, state: FSMContext) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	try:
		await _safe_answer(callback)
	except Exception:
		pass
	await state.clear()
	await state.set_state(ReviewStates.wait_media)
	await _safe_edit_cb(callback, "Отправьте фото или видео отзыва (как фото/видео, не как файл)")
	# already answered above


@router.message(ReviewStates.wait_media, F.photo | F.video)
async def review_capture_media(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	if message.photo:
		file_id = message.photo[-1].file_id  # type: ignore[index]
		media_type = "photo"
	else:
		file_id = message.video.file_id  # type: ignore[union-attr]
		media_type = "video"
	await state.update_data(file_id=file_id, media_type=media_type)
	await state.set_state(ReviewStates.wait_caption)
	await message.answer("Добавьте подпись к отзыву (или отправьте '-' чтобы пропустить)")


@router.message(ReviewStates.wait_caption)
async def review_save(message: Message, state: FSMContext) -> None:
	if not _is_admin(message.from_user.id):  # type: ignore[union-attr]
		return
	data = await state.get_data()
	caption = None if (message.text or "").strip() == "-" else message.text
	async with SessionLocal() as session:
		async with session.begin():
			rev = Review(media_type=data["media_type"], file_id=data["file_id"], caption=caption)
			session.add(rev)
		await session.commit()
	await state.clear()
	await message.answer("Отзыв добавлен", reply_markup=admin_menu_keyboard().as_markup())


async def _show_review_page(callback: CallbackQuery, offset: int) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	try:
		await _safe_answer(callback)
	except Exception:
		pass
	async with SessionLocal() as session:
		# total count
		cnt_res = await session.execute(select(func.count(Review.id)))
		total = int(cnt_res.scalar() or 0)
		if total == 0:
			await _safe_edit_cb(callback, "Пока нет отзывов", reply_markup=admin_menu_keyboard().as_markup())
			return
		# clamp offset
		offset = max(0, min(offset, max(0, total - 1)))
		# load one review by offset
		rev_res = await session.execute(
			select(Review).order_by(Review.created_at.desc()).offset(offset).limit(1)
		)
		rev = rev_res.scalars().first()
	
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	from aiogram.types import InlineKeyboardButton
	b = InlineKeyboardBuilder()
	# nav buttons
	prev_off = max(0, offset - 1)
	next_off = min(total - 1, offset + 1)
	if offset > 0:
		b.button(text="◀️ Пред", callback_data=f"admin:reviews:page:{prev_off}")
	if offset < total - 1:
		b.button(text="▶️ След", callback_data=f"admin:reviews:page:{next_off}")
	b.adjust(2)
	# delete + back
	b.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:review:del:{getattr(rev,'id',0)}:{offset}"))
	b.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:open"))

	# render
	caption = f"Отзыв {offset+1} из {total}\n" + (rev.caption or "")
	try:
		if rev.media_type == "photo":
			await callback.message.delete()
			await callback.message.answer_photo(rev.file_id, caption=caption, reply_markup=b.as_markup())
		else:
			await callback.message.delete()
			await callback.message.answer_video(rev.file_id, caption=caption, reply_markup=b.as_markup())
	except Exception:
		await _safe_edit_cb(callback, caption or "Отзыв", reply_markup=b.as_markup())


@router.callback_query(F.data == "admin:reviews")
async def admin_reviews_open(callback: CallbackQuery) -> None:
	await _show_review_page(callback, 0)


@router.callback_query(F.data.startswith("admin:reviews:page:"))
async def admin_reviews_page(callback: CallbackQuery) -> None:
	parts = (callback.data or "").split(":")
	offset = int(parts[-1]) if parts and parts[-1].isdigit() else 0
	await _show_review_page(callback, offset)
	# already answered above


@router.callback_query(F.data.startswith("admin:review:del:"))
async def admin_review_delete(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	try:
		await _safe_answer(callback)
	except Exception:
		pass
	parts = (callback.data or "").split(":")
	review_id = int(parts[-2]) if len(parts) >= 2 else 0
	offset = int(parts[-1]) if parts and parts[-1].isdigit() else 0
	async with SessionLocal() as session:
		await session.execute(delete(Review).where(Review.id == review_id))
		await session.commit()
	# After delete, stay on the same offset index (now shows next item automatically)
	await _show_review_page(callback, max(0, offset))


