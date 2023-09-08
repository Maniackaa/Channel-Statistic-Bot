from aiogram.types import KeyboardButton, ReplyKeyboardMarkup,\
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from database.db import Channel

kb1 = {
    'Остановить мониторинг': 'stop',
    'Сформировать статистику': 'stat',
    'Ваши каналы': 'channels',
    'Сгенерировать новый ключ': 'new_secret',
}


def custom_kb(width: int, buttons_dict: dict) -> InlineKeyboardMarkup:
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    buttons = []
    for key, val in buttons_dict.items():
        callback_button = InlineKeyboardButton(
            text=key,
            callback_data=val)
        buttons.append(callback_button)
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


start_kb = custom_kb(2, kb1)


def channel_kb(width: int, channels: list[Channel]) -> InlineKeyboardMarkup:
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    buttons = []
    for channel in channels:
        callback_button = InlineKeyboardButton(
            text=f'{channel.title} {"✅" if channel.is_active else "❌"}',
            callback_data=f'change_monitoring_{channel.id}')
        buttons.append(callback_button)
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()