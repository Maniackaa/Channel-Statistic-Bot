import datetime

from aiogram import Router, Bot, F
from aiogram.filters import Command, ChatMemberUpdatedFilter, MEMBER, LEFT, ADMINISTRATOR, KICKED
from aiogram.types import CallbackQuery, Message, ChatInviteLink, \
    InlineKeyboardButton, ChatMemberUpdated

from aiogram.fsm.context import FSMContext
from aiogram.utils.deep_linking import create_start_link, decode_payload
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config_data.conf import LOGGING_CONFIG, conf, tz
import logging.config

from database.db import Channel
from keyboards.keyboards import start_kb, custom_kb
from lexicon.lexicon import LEXICON_RU
from services.db_func import get_or_create_user, get_or_create_channel, add_join, add_left, check_channel

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot_logger')
err_log = logging.getLogger('errors_logger')

router: Router = Router()


# Действия юзеров
@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEFT))
@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def user_kick(event: ChatMemberUpdated, bot: Bot):
    print('USER KICKED or LEFT')
    try:
        chat = event.chat
        user = event.old_chat_member.user
        logger.info(f'Юзер {user.username} {user.id} KICKED/LEFT с канала {chat.id} {chat.title} ')
        user = get_or_create_user(user)
        channel = check_channel(chat)
        if channel and channel.is_active:
            add_left(user, channel)

    except Exception as err:
        err_log.error(err, exc_info=True)


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def user_join(event: ChatMemberUpdated, bot: Bot):
    print('USER MEMBER')
    try:
        chat = event.chat
        member = event.new_chat_member.user
        logger.info(f'Юзер {member.username} {member.id} присоединился к каналу {chat.id} {chat.title} ')
        user = get_or_create_user(member)
        channel: Channel = check_channel(chat)
        if channel and channel.is_active:
            add_join(user, channel)

    except Exception as err:
        err_log.error(err, exc_info=True)
        raise err


# Действия бота
@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def as_member(event: ChatMemberUpdated, bot: Bot):
    print('MY event MEMBER')
    try:
        chat = event.chat
        owner = event.from_user
        logger.info(f'Бот добавлен в канал {chat.id} {chat.title} как MEMBER  пользователем {owner.username} {owner.id}')
        channel = check_channel(chat)
        if channel:
            await bot.send_message(chat_id=channel.owner.tg_id,
                                   text=f'Бот сменил статус на MEMEBER в чате {chat.id} {chat.title} пользователем {owner.username} {owner.id}')
    except Exception as err:
        err_log.error(err, exc_info=True)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=(LEFT | KICKED)))
async def left(event: ChatMemberUpdated, bot: Bot):
    print('MY event LEFT')
    try:
        print(event)
        chat = event.chat
        owner = event.from_user
        logger.info(f'Бот удален с канала {chat.id} {chat.title} пользователем {owner.username} {owner.id}')
        channel = check_channel(chat)
        if channel:
            print(channel.channel_id, channel.owner)
            await bot.send_message(chat_id=channel.owner.tg_id, text=f'Бот удален с канала {chat.id} {chat.title} пользователем {owner.username} {owner.id}')
    except Exception as err:
        err_log.error(err, exc_info=True)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR))
async def as_admin(event: ChatMemberUpdated, bot: Bot):
    print('MY event ADMINISTRATOR')
    try:
        chat = event.chat
        owner = event.from_user
        logger.info(f'Бот добавлен в канал {chat.id} {chat.title} как ADMINISTRATOR пользователем {owner.username} {owner.id}')
        # Добавляем канал в базу
        user = get_or_create_user(owner)
        channel = get_or_create_channel(chat, user)
        print(channel)
        await bot.send_message(chat_id=owner.id, text=f'Вы добавили бота как администратор в канал/группу {chat.title}\n\nСекретный ключ: {channel.secret}')
    except Exception as err:
        err_log.error(err, exc_info=True)
        raise err
