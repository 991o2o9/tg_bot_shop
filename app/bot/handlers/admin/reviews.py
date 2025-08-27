from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.review import Review
from app.bot.keyboards.inline import admin_menu_keyboard


router = Router(name="admin_reviews")
async def _safe_edit_cb(callback: CallbackQuery, text: str, reply_markup=None) -> None:
	try:
		await callback.message.edit_text(text, reply_markup=reply_markup)
	except Exception:
		try:
			await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
		except Exception:
			await callback.message.answer(text, reply_markup=reply_markup)



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
		await callback.answer()
		return
	try:
		await callback.answer()
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
		await callback.answer()
		return
	try:
		await callback.answer()
	except Exception:
		pass
	async with SessionLocal() as session:
		res = await session.execute(select(Review).order_by(Review.created_at.desc()).limit(10))
		reviews = list(res.scalars().all())
	if not reviews:
		await _safe_edit_cb(callback, "Пока нет отзывов", reply_markup=admin_menu_keyboard().as_markup())
		return
	await _safe_edit_cb(callback, f"Всего показано: {len(reviews)}. Последние отзывы отправлены в чат.", reply_markup=admin_menu_keyboard().as_markup())
	for r in reviews:
		try:
			if r.media_type == "photo":
				await callback.message.answer_photo(r.file_id, caption=r.caption or "")
			else:
				await callback.message.answer_video(r.file_id, caption=r.caption or "")
		except Exception:
			pass
	# Добавляем сообщение с клавиатурой внизу, чтобы кнопки были под последним сообщением
	try:
		await callback.message.answer("↩️ Назад в админ-меню", reply_markup=admin_menu_keyboard().as_markup())
	except Exception:
		pass
	# already answered above


