import asyncio
import logging
from typing import Callable, Dict, Any, Any as AnyType

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ContentType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from .config import get_settings
from .db import get_session_factory, init_db
from .storage import (
    add_message,
    get_last_history,
    get_or_create_user,
    grant_access,
    update_model,
    add_stars,
    save_stars_transaction,
    user_stats,
    last_transactions,
)
from .ai import fetch_completion


settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


class SessionMiddleware(BaseMiddleware):
    def __init__(self, sessionmaker):
        super().__init__()
        self.sessionmaker = sessionmaker

    async def __call__(self, handler: Callable, event: AnyType, data: Dict[str, Any]):
        async with self.sessionmaker() as session:
            data["session"] = session
            return await handler(event, data)




# старт команда
async def handle_start(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id, settings.default_model)
    status = "оплачен" if user.has_access else "не оплачен"
    if user.has_access:
        await message.answer(f"Привет. Доступ уже активирован. Текущая модель: {user.model_name}.")
        return
    text = (
        "Привет. Я бот с OpenRouter. "
        f"Текущая модель: {user.model_name}. "
        f"Доступ: {status}. "
        f"Оплата через /pay за {settings.pay_amount}⭐."
    )
    await message.answer(text)



# помощь команда
async def handle_help(message: Message):
    await message.answer("Доступные команды: /pay, /paytest, /buy, /llama, /gpt, /gemini. После оплаты пиши текст и получишь ответ.")




# получени ии модели(выбор)
async def handle_llama(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id, settings.default_model)
    user = await update_model(session, user, settings.default_model)
    await message.answer("Модель переключена на Llama.")


async def handle_gpt(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id, settings.default_model)
    user = await update_model(session, user, settings.fallback_model)
    await message.answer("Модель переключена на GPT.")


async def handle_gemini(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id, settings.default_model)
    user = await update_model(session, user, settings.gemini_model)
    await message.answer("Модель переключена на Gemini.")






# блок оплаты
async def handle_pay(message: Message, bot: Bot, session):
    user = await get_or_create_user(session, message.from_user.id, settings.default_model)
    if user.has_access:
        await message.answer(f"Доступ уже активирован. Текущая модель: {user.model_name}.")
        return
    prices = [LabeledPrice(label="Доступ к боту (тест)", amount=settings.pay_amount)]
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Доступ к боту (тест)",
        description="Оплата доступа к чат-боту (тестовый платеж Stars)",
        payload="stars-access-test",
        provider_token="",
        currency="XTR",
        prices=prices,
    )


async def handle_pre_checkout(query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(query.id, ok=True)


async def handle_pay_test(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id, settings.default_model)
    await grant_access(session, user)
    await message.answer("Тестовая активация: доступ включен без списания.")


async def handle_successful_payment(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id, settings.default_model)
    payment = message.successful_payment
    payload = payment.invoice_payload or ""
    parts = payload.split("_")
    if payment.currency == "XTR" and payload == "stars-access-test":
        await grant_access(session, user)
        await add_stars(session, user, payment.total_amount)
        await save_stars_transaction(
            session,
            user_id=user.id,
            product_id="access",
            stars_amount=payment.total_amount,
            payload=payload,
            currency=payment.currency,
            charge_id=payment.telegram_payment_charge_id,
        )
        await message.answer(f"Оплата прошла. Доступ активирован. Начислено {payment.total_amount}⭐.")
    else:
        await grant_access(session, user)
        await message.answer("Оплата прошла.")







# текст для отправки в ии
async def handle_text(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id, settings.default_model)
    if not user.has_access:
        await message.answer(f"Нужна оплата. Используй /pay ({settings.pay_amount}⭐).")
        return
    history_rows = await get_last_history(session, user.id, user.model_name, limit=5)
    history = [{"role": row.role, "content": row.content} for row in history_rows]
    history.append({"role": "user", "content": message.text})
    reply = await fetch_completion(history, user.model_name)
    await add_message(session, user.id, "user", message.text, user.model_name)
    await add_message(session, user.id, "assistant", reply, user.model_name)
    await message.answer(reply)




# админ команды блок
async def handle_admin_stats(message: Message, session):
    if message.from_user.id not in settings.admin_ids:
        return
    stats = await user_stats(session)
    await message.answer(f"Пользователи: {stats['users']}\nБаланс суммарно: {stats['stars']}⭐\nТранзакций: {stats['transactions']}")


async def handle_admin_tx(message: Message, session):
    if message.from_user.id not in settings.admin_ids:
        return
    txs = await last_transactions(session, limit=10)
    if not txs:
        await message.answer("Транзакций нет.")
        return
    lines = []
    for tx in txs:
        lines.append(f"{tx.created_at} user={tx.user_id} product={tx.product_id} amount={tx.stars_amount} payload={tx.payload}")
    await message.answer("\n".join(lines))







async def main():
    await init_db()
    bot = Bot(settings.bot_token, parse_mode=None)
    dp = Dispatcher()
    sessionmaker = get_session_factory()
    dp.message.middleware(SessionMiddleware(sessionmaker))
    dp.message.register(handle_start, CommandStart())
    dp.message.register(handle_help, Command("help"))
    dp.message.register(handle_llama, Command("llama"))
    dp.message.register(handle_gpt, Command("gpt"))
    dp.message.register(handle_gemini, Command("gemini"))
    dp.message.register(handle_pay, Command("pay"))
    dp.message.register(handle_pay_test, Command("paytest"))
    dp.message.register(handle_admin_stats, Command("admin_stats"))
    dp.message.register(handle_admin_tx, Command("admin_tx"))
    dp.pre_checkout_query.register(handle_pre_checkout)
    dp.message.register(handle_successful_payment, F.content_type == ContentType.SUCCESSFUL_PAYMENT)
    dp.message.register(handle_text, F.text)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
