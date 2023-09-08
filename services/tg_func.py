from aiogram import Bot
from aiogram.types import ChatInviteLink


async def create_invite_link(bot: Bot, chat_id, expire_date):
    link: ChatInviteLink = await bot.create_chat_invite_link(
        chat_id=chat_id,
        creates_join_request=False,
        expire_date=expire_date,
        member_limit=1)
    return link
