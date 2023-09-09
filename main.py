import asyncio

from aiogram import Bot, Dispatcher

from config_data.conf import conf, get_my_loggers
from handlers import user_handlers, action_handlers


logger, err_log = get_my_loggers()
async def main():
    logger.info('Starting bot')
    bot: Bot = Bot(token=conf.tg_bot.token, parse_mode='HTML')
    dp: Dispatcher = Dispatcher()
    dp.include_router(user_handlers.router)
    dp.include_router(action_handlers.router)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        admins = conf.tg_bot.admin_ids
        if admins:
            await bot.send_message(
                conf.tg_bot.admin_ids[0], f'Бот запущен.')
    except:
        err_log.critical(f'Не могу отравить сообщение {conf.tg_bot.admin_ids[0]}')

    await dp.start_polling(bot, allowed_updates=["message", "inline_query", "my_chat_member", "chat_member", "callback_query"])


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Bot stopped!')