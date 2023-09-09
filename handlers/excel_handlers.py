import datetime
from pathlib import Path

import pandas as pd
from aiogram import Bot, F, Router
from aiogram.filters import (ADMINISTRATOR, KICKED, LEFT, MEMBER,
                             ChatMemberUpdatedFilter, Command, StateFilter)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (CallbackQuery, ChatInviteLink, ChatMemberUpdated,
                           InlineKeyboardButton, Message, FSInputFile)

from config_data.conf import get_my_loggers, BASE_DIR
from database.db import Channel
from keyboards.keyboards import custom_kb
from services.db_func import find_user_tg_id, find_user_join, get_or_create_user, get_your_channels

logger, err_log = get_my_loggers()

router: Router = Router()


class FSMXls(StatesGroup):
    select = State()


@router.message(F.content_type == 'document')
async def xls(message: Message, state: FSMContext, bot: Bot):
    doc = message.document
    file_path = f'{message.from_user.id}.xlsx'
    await bot.download(file=doc, destination=file_path)
    try:
        with open(file_path, 'rb') as file:
            pd.read_excel(file, engine='openpyxl')
        user = get_or_create_user(message.from_user)
        channels: list[Channel] = get_your_channels(user)
        btn = {}
        for channel in channels:
            btn[f'{channel.title}'] = f'xchannel_{channel.id}'
        await message.answer('Выберите канал для поиска', reply_markup=custom_kb(1, btn))
        await state.set_state(FSMXls.select)
    except Exception as err:
        err_log.error(err)


@router.callback_query(F.data.startswith('xchannel_'))
async def select(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    try:
        channel_id = int(callback.data.split('channel_')[1])
        file_path = f'{callback.from_user.id}.xlsx'
        with open(file_path, 'rb') as file:
            df = pd.read_excel(file, engine='openpyxl')
        tg_ids = df.iloc[:, 0].apply(find_user_tg_id, args=(channel_id,))
        join_times = df.iloc[:, 0].apply(find_user_join, args=(channel_id,))
        df.insert(0, 'ID', tg_ids)
        df['Дата подписки'] = join_times
        delta = []
        for row in df.values:
            try:
                buy_date = row[4]
                buy_date = datetime.datetime.fromisoformat(str(buy_date))
                join_date = row[6]
                period = buy_date.date() - join_date
                delta.append(period)
            except TypeError:
                delta.append(None)
                pass
        df['Время нахождения в канале до покупки, дни'] = delta
        df = df.astype({'Дата покупки': 'str'})
        out_path = BASE_DIR / f'out{callback.from_user.id}.xlsx'
        df.to_excel(out_path, index=False)
        file = FSInputFile(out_path)
        await bot.send_document(chat_id=callback.message.chat.id, document=file)
        input_file = BASE_DIR / f'{callback.from_user.id}.xlsx'
        input_file.unlink()
        file.path.unlink()

    except Exception as err:
        err_log.error(err)


@router.message()
async def echo(message: Message, state: FSMContext, bot: Bot):
    print(message.content_type)


@router.callback_query()
async def echo(callback: CallbackQuery, state: FSMContext):
    print(callback.data)