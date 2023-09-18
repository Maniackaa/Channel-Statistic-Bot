import asyncio
import datetime
import logging
from typing import Optional

from aiogram.types import Chat
from sqlalchemy import select, insert, update

from config_data.conf import LOGGING_CONFIG, conf, tz
import logging.config

from database.db import User, Session, Channel, Action
from keyboards.keyboards import start_kb



logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot_logger')
err_log = logging.getLogger('errors_logger')


def check_user(tg_id: int | str) -> User:
    """Возвращает найденного пользователя по tg_id"""
    # logger.debug(f'Ищем юзера {tg_id}')
    with Session() as session:
        user: User = session.query(User).filter(User.tg_id == str(tg_id)).first()
        # logger.debug(f'Результат: {user}')
        return user


def get_or_create_user(user, refferal=None) -> Optional[User]:
    """Из юзера ТГ создает User"""
    try:
        old_user = check_user(user.id)
        if old_user:
            logger.debug('Пользователь есть в базе')
            return old_user
        # Создание нового пользователя
        logger.debug('Добавляем пользователя')
        with Session() as session:
            new_user = User(tg_id=user.id,
                            first_name=user.first_name,
                            last_name=user.last_name,
                            full_name=user.full_name,
                            username=user.username,
                            register_date=datetime.datetime.now(tz=tz),
                            referral=refferal
                            )
            session.add(new_user)
            session.commit()
            logger.debug(f'Пользователь создан: {new_user}')
        return new_user
    except Exception as err:
        err_log.error('Пользователь не создан', exc_info=True)


def check_channel(chat: Chat):
    """
    Проверяет создан ли такой канал

    :param chat:
    :param user:
    :return:
    """
    logger.debug(f'Проверяем канал {chat.id}')
    session = Session()
    channel_q = select(Channel).where(Channel.channel_id == chat.id)
    channel = session.execute(channel_q).scalars().all()
    session.close()
    if channel:
        return channel[0]


def get_or_create_channel(chat: Chat, user: User) -> Channel:
    """
    Создает канал для отслеживания

    :param chat:
    :param user:
    :return:
    """
    try:
        logger.debug(f'Проверяем канал {chat.id}. Юзер: {user}')
        session = Session()
        channel_q = select(Channel).where(Channel.channel_id == chat.id)
        channel = session.execute(channel_q).scalars().all()
        print(chat.id)
        print(channel)
        if channel:
            return channel[0]
        logger.debug('Создаем новый канал')
        new_channel = Channel(
            channel_id=chat.id,
            title=chat.title,
            description=chat.description,
            owner_id=user.id
        )
        session.add(new_channel)
        session.commit()
        logger.debug(f'Канал {new_channel} создан')
        session.close()
        return new_channel
    except Exception as err:
        logger.error(err, exc_info=True)
        raise err


def add_join(user: User, channel: Channel, invite_link=None):
    """
    Создает действие присоединения к каналу

    :param user:
    :param channel:
    :param invite_link:
    :return:
    """
    try:
        logger.debug(f'Создаем join юзеру {user} в канал {channel}')
        session = Session()
        join_q = select(Action).where(Action.channel_id == channel.id, Action.user_id == user.id)
        join_action = session.execute(join_q).scalars().all()
        if join_action:
            action = join_action[0]
            action.join_time = datetime.datetime.now(tz=tz)
            action.invite_link = invite_link
            session.commit()
            logger.debug(f'Обновлен join action {action}')
            return action
        new_join = Action(
            user_id=user.id,
            channel_id=channel.id,
            join_time=datetime.datetime.now(tz=tz),
            invite_link=invite_link
        )
        session.add(new_join)
        logger.debug(f'Новое Действие join создано {new_join}')
        session.commit()
        session.close()
        return new_join
    except Exception as err:
        logger.error(err, exc_info=True)
        raise err

def add_left(user: User, channel: Channel):
    """
    Создает действие выхода с канала

    :param chat:
    :param user:
    :return:
    """
    try:
        logger.debug(f'Создаем left юзеру {user} из канал {channel}')
        session = Session()
        left_q = select(Action).where(Action.channel_id == channel.id).where(Action.user_id == user.id)
        left_action = session.execute(left_q).scalars().all()
        if left_action:
            logger.debug(f'left action найдена: {left_action}')
            action = left_action[0]
            action.left_time = datetime.datetime.now(tz=tz)
            session.commit()
            logger.debug(f'Обновлен left action {action}')
            session.close()
            return action
        logger.debug('Создаем left')
        new_left = Action(
            user_id=user.id,
            channel_id=channel.id,
            left_time=datetime.datetime.now(tz=tz)
        )
        session.add(new_left)
        session.commit()
        logger.debug(f'Новое Действие left создано {new_left}')
        session.close()
        return new_left
    except Exception as err:
        logger.error(err, exc_info=True)
        raise err


def get_only_your_channels(user: User):
    """
    Находит ваши каналы
    :return:
    """
    session = Session()
    user_q = select(User).where(User.id == user.id)
    user = session.execute(user_q).scalars().first()
    channels = user.channels
    return channels


def get_your_channels(user: User):
    """
    Находит ваши каналы
    :return:
    """
    session = Session()
    user_q = select(User).where(User.id == user.id)
    user = session.execute(user_q).scalars().first()
    logger.debug(f'user: {user}')
    channels = user.channels
    logger.debug(f'Ищем каналы {user}: {channels}')
    secrets = user.secrets
    logger.debug(f'Ключи: {secrets}')
    if secrets:
        channels2_q = select(Channel).where(Channel.secret.in_(secrets))
        channels2 = session.execute(channels2_q).scalars().all()
        logger.debug(f'Каналы из секретов: {channels2}')
        if channels2:
            channels = channels + channels2
    logger.debug(f'Итого каналы: {channels}')
    return set(channels)


def add_secret(user: User, secret: str):
    try:
        session = Session()
        old_values = user.secrets or []
        logger.debug(f'Старые ключи: {old_values}')
        new_secrets = old_values + [secret]
        logger.debug(f'Новый список: {new_secrets}')
        q = update(User).where(User.id == user.id).values(secrets=set(new_secrets))
        session.execute(q)
        session.commit()
        logger.debug(f'Новые ключи: {user.secrets}')
        logger.debug(f'Добавлен ключ {secret} юзеру {user}')
        session.close()
    except Exception as err:
        logger.error(err)
        err_log.error(err, exc_info=True)


def get_channel_from_id(channel_pk):
    session = Session()
    channel = session.execute(select(Channel).where(Channel.id == channel_pk)).scalars().first()
    session.close()
    return channel


def change_monitoring(channel_pk):
    session = Session()
    q = select(Channel).where(Channel.id == channel_pk)
    channel: Channel = session.execute(q).scalars().one_or_none()
    if channel.is_active:
        channel.is_active = 0
    else:
        channel.is_active = 1
    session.commit()
    session.close()


def find_user_tg_id(login, channel_id):
    try:
        session = Session()
        q = select(Action).where(User.username == login).where(Action.channel_id == channel_id).join(User)
        action: Action = session.execute(q).scalars().one_or_none()
        if action:
            return action.user.tg_id
    except Exception as err:
        raise err


def find_user_join(login, channel_id):
    try:
        logger.debug(f'find_user_join: {login}, {channel_id}')
        session = Session()
        q = select(Action).where(User.username == login).where(Action.channel_id == channel_id).join(User)
        action: Action = session.execute(q).scalars().one_or_none()
        logger.debug(f'action: {action}')
        if action and action.join_time:
            return action.join_time.date()
    except Exception as err:
        logger.debug(err)
        raise err


if __name__ == '__main__':
    pass
    session = Session()
    user = select(User).where(User.id == 1)
    user = session.execute(user).scalars().first()
    print(get_your_channels(user))
    session.close()
