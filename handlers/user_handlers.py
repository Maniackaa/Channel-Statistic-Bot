import datetime
import uuid

from aiogram import Router, Bot, F
from aiogram.filters import Command, ChatMemberUpdatedFilter, MEMBER, LEFT, ADMINISTRATOR, KICKED, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, ChatInviteLink, \
    InlineKeyboardButton, ChatMemberUpdated, FSInputFile, Chat, ChatJoinRequest

from aiogram.fsm.context import FSMContext
import pandas as pd

from config_data.conf import tz, get_my_loggers

from database.db import Channel, User, Action
from keyboards.keyboards import start_kb, custom_kb, channel_kb
from lexicon.lexicon import LEXICON_RU
from services.db_func import get_or_create_user, get_your_channels, add_secret, check_channel, get_channel_from_id, \
    get_only_your_channels, change_monitoring
from services.stat_func import get_all_join, get_all_left, get_new_left, get_proc_new_left, get_join_with_login, \
    get_join_without_login, get_avg_time_lefted, get_avg_day_time_lefted, get_avg_time_all, \
    incomings_in_period, outgoings_in_period

logger, err_log = get_my_loggers()

router: Router = Router()


class FSMStat(StatesGroup):
    start_period = State()
    end_period = State()
    select = State()


class FSMSecret(StatesGroup):
    select = State()


@router.message(Command(commands=["start"]))
async def process_start_command(message: Message, state: FSMContext, bot: Bot):
    logger.debug(f'/start {message.from_user.id}')
    await state.clear()
    referal = message.text[7:]
    new_user = get_or_create_user(message.from_user, referal)
    await message.answer(LEXICON_RU['start_text'], reply_markup=start_kb)


@router.callback_query(F.data == 'channels')
async def channels(callback: CallbackQuery):
    try:
        logger.debug('channels')
        user = get_or_create_user(callback.from_user)
        logger.debug(f'user: {user}')
        your_channels = get_your_channels(user)
        if your_channels:
            channel_text = '\n'.join([f'{channel.title}: <code>{channel.secret}</code> {"✅" if channel.is_active else "❌"}'  for channel in your_channels])
            text = f'Ваши каналы:\n{channel_text}'
        else:
            text = 'У вас нет каналов'
        logger.debug(f'{text}')
        await callback.message.edit_text(text, reply_markup=start_kb)
    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)


@router.callback_query(F.data == 'stat')
async def stat(callback: CallbackQuery):
    btn = {'За всё время': 'all_time',
           'За период': 'part_time'}
    await callback.message.answer('Выберете период:', reply_markup=custom_kb(1, btn))
    await callback.message.delete()


@router.callback_query(F.data == 'part_time')
async def part_time(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer('Введите начало периода в формате ДД.ММ.ГГГГ')
    await state.set_state(FSMStat.start_period)


@router.message(StateFilter(FSMStat.start_period))
async def start_period(message: Message, state: FSMContext, bot: Bot):
    date_text = message.text.strip()
    try:
        date = datetime.datetime.strptime(date_text, '%d.%m.%Y')
        await state.update_data(start_period=date)
        await message.answer('Введите конец периода в формате ДД.ММ.ГГГГ')
        await state.set_state(FSMStat.end_period)
    except ValueError:
        await message.answer('Не верный формат даты.\nВведите начало периода в формате ДД.ММ.ГГГГ')


@router.message(StateFilter(FSMStat.end_period))
async def end_period(message: Message, state: FSMContext, bot: Bot):
    date_text = message.text.strip()
    try:
        date = datetime.datetime.strptime(date_text, '%d.%m.%Y')
        await state.update_data(end_period=date)
        user = get_or_create_user(message.from_user)
        channels: list[Channel] = get_your_channels(user)
        print(channels)
        btn = {}
        for channel in channels:
            btn[f'{channel.title}'] = f'channel_{channel.id}'
        await message.answer('Выберите канал', reply_markup=custom_kb(1, btn))
        await state.set_state(FSMStat.select)
    except ValueError:
        await message.answer('Не верный формат даты.\nВведите конец периода в формате ДД.ММ.ГГГГ')
    except Exception as err:
        raise err


@router.callback_query(F.data == 'all_time')
async def all_time(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user = get_or_create_user(callback.from_user)
    channels: list[Channel] = get_your_channels(user)
    btn = {}
    for channel in channels:
        btn[f'{channel.title}'] = f'channel_{channel.id}'
    await callback.message.answer('Выберите канал', reply_markup=custom_kb(1, btn))
    await state.set_state(FSMStat.select)
    await callback.message.delete()


@router.callback_query(F.data.startswith('channel_'), StateFilter(FSMStat.select))
async def stat(callback: CallbackQuery, state: FSMContext, bot: Bot):
    logger.debug('stat')
    logger.debug(callback.data)
    channel_id = int(callback.data.split('channel_')[1])
    data = await state.get_data()
    logger.debug(f'data: {data}')
    channel = get_channel_from_id(channel_id)
    logger.debug(f'channel: {channel}')
    if data:
        text = f'Отчет за период {data["start_period"].strftime("%d.%m.%Y")} - {data["end_period"].strftime("%d.%m.%Y")} по каналу {channel.title}:\n'
        period = f'{data["start_period"].strftime("%d.%m.%Y")} - {data["end_period"].strftime("%d.%m.%Y")}'
    else:
        text = f'Отчет за весь период по каналу {channel.title}:\n'
        period = f'Весь период'
    start = data.get('start_period')
    end = data.get('end_period')
    all_join = get_all_join(channel_id, start, end)
    text += f'Всего вступило: {all_join}\n'
    all_left = get_all_left(channel_id, start, end)
    text += f'Всего отписалось: {all_left}\n'
    text += f'Вступило с учетом всех отписок: {all_join - all_left}\n'
    if all_join != 0:
        text += f'Общий процент отписок за период: {round(all_left/all_join*100, 2)} %\n'
        all_proc = round(all_left/all_join*100, 2)
    else:
        text += f'Общий процент отписок за период: -\n'
        all_proc = '-'
    new_left = get_new_left(channel_id, start, end)
    text += f'Отписалось из новых подписчиков за период: {new_left}\n'
    text += f'Вступило новых за вычетом отписок: {all_join - new_left}\n'
    proc_new_left = get_proc_new_left(channel_id, start, end)
    text += f'Процент отписок только НОВЫХ подписчиков за период: {proc_new_left} %\n'
    join_with_login = get_join_with_login(channel_id, start, end)
    text += f'Подписки с логинами: {join_with_login}\n'
    join_without_login = get_join_without_login(channel_id, start, end)
    text += f'Подписки без логинов: {join_without_login}\n'
    avg_time_lefted = get_avg_time_lefted(channel_id, start, end)
    text += f'Среднее время нахождение в канале ОТПИСАВШИХСЯ за отчетный период: {avg_time_lefted} дн.\n'
    avg_day_time_lefted = get_avg_day_time_lefted(channel_id, start, end)
    text += f'Среднее время нахождение в канале ОТПИСАВШИХСЯ за отчетный период больше 1 дня: {avg_day_time_lefted} ч.\n'
    avg_time_all = get_avg_time_all(channel_id, start, end)
    text += f'Среднее время удержания всех подписчиков в канале >1 дня за период: {avg_time_all}'
    await callback.message.answer(text)

    df = pd.DataFrame(columns=['Наименование', 'Показатель', 'Дата', 'Доп инфо', '-'])
    df.loc[len(df.index)] = ['Отчетный период', period] + ['', '', '']
    df.loc[len(df.index)] = ['Всего вступило', all_join] + ['', '', '']
    df.loc[len(df.index)] = ['Всего отписалось', all_left] + ['', '', '']
    df.loc[len(df.index)] = ['Вступило с учетом всех отписок', (all_join - all_left)] + ['', '', '']
    df.loc[len(df.index)] = ['Общий процент отписок за период', all_proc] + ['', '', '']
    df.loc[len(df.index)] = ['Отписалось из новых подписчиков за период', new_left] + ['', '', '']
    df.loc[len(df.index)] = ['Вступило новых за вычетом отписок', all_join - new_left] + ['', '', '']
    df.loc[len(df.index)] = ['Процент отписок только НОВЫХ подписчиков за период', proc_new_left] + ['', '', '']
    df.loc[len(df.index)] = ['Подписки с логинами', join_with_login] + ['', '', '']
    df.loc[len(df.index)] = ['Подписки без логинов', join_without_login] + ['', '', '']
    df.loc[len(df.index)] = ['Среднее время нахождения в канале ОТПИСАШИХСЯ за отчетный период', f'{avg_time_lefted} ч.'] + ['', '', '']
    df.loc[len(df.index)] = ['Среднее время нахождения в канале ОТПИСАШИХСЯ за отчетный период больше 1 дня', f'{avg_day_time_lefted} ч.'] + ['', '', '']
    df.loc[len(df.index)] = ['Среднее время удержания всех подписчиков в канале >1 дня за период', avg_time_all] + ['', '', '']


    df.loc[len(df.index)] = [''] * 5
    df.loc[len(df.index)] = ['Имя', 'Username', 'Дата вступления', 'Ссылка-инвайт', '-']
    incoming_users: list[Action] = incomings_in_period(channel_id, start, end)
    for action in incoming_users:
        df.loc[len(df.index)] = [action.user.full_name,
                                       action.user.username,
                                       action.join_time.strftime("%d.%m.%Y"),
                                       action.invite_link or '',
                                       ' ']

    df.loc[len(df.index)] = [''] * 5
    df.loc[len(df.index)] = ['Имя', 'Username', 'Дата отписки', 'Время нахождения в канале', 'Ссылка-инвайт']
    outgoing_users: list[Action] = outgoings_in_period(channel_id, start, end)
    for action in outgoing_users:
        df.loc[len(df.index)] = [
            action.user.full_name,
            action.user.username,
            action.left_time.strftime("%d.%m.%Y"),
            action.left_time - action.join_time if action.left_time and action.join_time else 'неизвестно',
            action.invite_link or ''
        ]

    df_file = f'{callback.from_user.id}.xlsx'
    df.to_excel(df_file, index=False)
    doc = FSInputFile(df_file)
    await bot.send_document(chat_id=callback.from_user.id, document=doc)
    await state.clear()
    await callback.message.delete()

    # invite_link = await bot.export_chat_invite_link(-1001697211543)
    # await callback.message.answer(invite_link)
    # result: ChatInviteLink = await bot.create_chat_invite_link(-1001697211543, member_limit=100)
    # print(result)
    # await callback.message.answer(result.invite_link)


@router.message(F.text.regexp(r"[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}").as_("digits"))
async def secret(message: Message, state: FSMContext, bot: Bot):
    logger.debug(f'Прислан код {message.text}')
    user = get_or_create_user(message.from_user)
    add_secret(user, message.text)
    your_channels = get_your_channels(user)
    logger.debug(f'Теперь каналы: {your_channels}')
    text = f'Ключ {message.text} добавлен.\n'
    if your_channels:
        channel_text = '\n'.join([f'{channel.title}: <code>{channel.secret}</code> {"✅" if channel.is_active else "❌"}'  for channel in your_channels])
        text += f'Ваши каналы:\n{channel_text}'
    else:
        text = 'У вас нет каналов'

    await message.answer(text)


@router.callback_query(F.data == 'new_secret')
async def new_secret(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = get_or_create_user(callback.from_user)
    channels: list[Channel] = get_only_your_channels(user)
    btn = {}
    for channel in channels:
        btn[f'{channel.title}'] = f'channel_{channel.id}'
    await callback.message.answer('Выберите канал', reply_markup=custom_kb(1, btn))
    await state.set_state(FSMSecret.select)


@router.callback_query(F.data.startswith('channel_'), StateFilter(FSMSecret.select))
async def select(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split('channel_')[1])
    channel = get_channel_from_id(channel_id)
    new_uuid = uuid.uuid4()
    channel.set('secret', new_uuid)
    await callback.message.answer(f'Новый ключ канала {channel.title}:\n<code>{new_uuid}</code>')
    await state.clear()
    await callback.message.delete()


@router.callback_query(F.data == 'stop')
async def stop(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = get_or_create_user(callback.from_user)
    channels: list[Channel] = get_your_channels(user)
    await callback.message.answer('Изменить мониторинг', reply_markup=channel_kb(1, channels))


@router.callback_query(F.data.startswith('change_monitoring_'))
async def change(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split('change_monitoring_')[1])
    change_monitoring(channel_id)
    user = get_or_create_user(callback.from_user)
    channels: list[Channel] = get_your_channels(user)
    await callback.message.edit_reply_markup(reply_markup=channel_kb(1, channels))



@router.chat_join_request()
async def as_admin(event: ChatJoinRequest, bot: Bot):
    logger.debug('ChatJoinRequest')
    print(event)




@router.chat_member()
async def as_admin(event, bot: Bot):

    print('chat_member')
    print(event)

@router.message()
async def secret(message):
    print(message)
    print('echo')