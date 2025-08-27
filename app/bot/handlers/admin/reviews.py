from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, delete
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
		await _safe_answer(callback)
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


@router.callback_query(F.data == "admin:reviews")
async def admin_reviews_list(callback: CallbackQuery) -> None:
	if not _is_admin(callback.from_user.id):  # type: ignore[union-attr]
		await _safe_answer(callback)
		return
	try:
		await _safe_answer(callback)
	except Exception:
		pass
	async with SessionLocal() as session:
		res = await session.execute(select(Review).order_by(Review.created_at.desc()).limit(10))
		reviews = list(res.scalars().all())
	if not reviews:
		await _safe_edit_cb(callback, "Пока нет отзывов", reply_markup=admin_menu_keyboard().as_markup())
		return
	
	# First show numbered list with descriptions
	review_list = []
	for i, r in enumerate(reviews, 1):
		media_type_emoji = "🖼" if r.media_type == "photo" else "🎥"
		caption_text = f" — {r.caption}" if r.caption else ""
		review_list.append(f"{i}. {media_type_emoji} Отзыв #{r.id}{caption_text}")
	
	await _safe_edit_cb(callback, "Список отзывов:\n\n" + "\n".join(review_list))
	
	# Then show each review with delete button
	from aiogram.utils.keyboard import InlineKeyboardBuilder
	from aiogram.types import InlineKeyboardButton
	
	for i, r in enumerate(reviews, 1):
		# Show review media
		try:
			if r.media_type == "photo":
				await callback.message.answer_photo(r.file_id, caption=f"Отзыв #{r.id} (№{i} в списке)")
			else:
				await callback.message.answer_video(r.file_id, caption=f"Отзыв #{r.id} (№{i} в списке)")
		except Exception:
			pass
	
	# Add delete buttons for each review
	builder = InlineKeyboardBuilder()
	for i, r in enumerate(reviews, 1):
		builder.row(
			InlineKeyboardButton(text=f"🗑 Удалить отзыв №{i} (ID: {r.id})", callback_data=f"admin:review:del:{r.id}")
		)
	builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin:open"))
	await callback.message.answer(f"Всего отзывов: {len(reviews)}. Удалите ненужные кнопками ниже:", reply_markup=builder.as_markup())
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
	review_id_str = (callback.data or "").rsplit(":", 1)[-1]
	try:
		review_id = int(review_id_str)
	except ValueError:
		await _safe_edit_cb(callback, "Некорректный ID отзыва", reply_markup=admin_menu_keyboard().as_markup())
		return
	async with SessionLocal() as session:
		await session.execute(delete(Review).where(Review.id == review_id))
		await session.commit()
	await _safe_edit_cb(callback, f"Отзыв #{review_id} удалён ✅", reply_markup=admin_menu_keyboard().as_markup())


