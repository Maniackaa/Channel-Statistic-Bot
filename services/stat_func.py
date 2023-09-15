import datetime
from operator import and_

from sqlalchemy import select, func, or_

from config_data.conf import tz, get_my_loggers
from database.db import Session, Action, User

logger, err_log = get_my_loggers()


def get_all_join(channel_id, start=None, end=None):
    """Всего вступило - это всего вступило пользователей за
выбранный период включительно"""
    session = Session()
    q = select(Action).filter(Action.channel_id == channel_id).where(Action.join_time.is_not(None))
    if start:
        q = q.filter(Action.join_time >= start)
    if end:
        q = q.filter(Action.join_time <= end + datetime.timedelta(days=1))
    all_join = session.execute(q).all()
    if all_join:
        return len(all_join)
    return 0


def get_all_left(channel_id, start=None, end=None):
    """Всего отписалось - это всего отписалось пользователей за
выбранный период"""
    session = Session()
    q = select(Action).filter(Action.channel_id == channel_id).where(Action.left_time.is_not(None))
    if start:
        q = q.filter(Action.left_time >= start)
    if end:
        q = q.filter(Action.left_time <= end + datetime.timedelta(days=1))
    all_join = session.execute(q).all()
    if all_join:
        return len(all_join)
    return 0


def get_new_left(channel_id, start=None, end=None):
    """
    Отписалось из новых подписчиков за период - сколько человек
    отписалось ТОЛЬКО из тех пользователей что ПРИШЕЛ в канал
    за отчетный период
    :return:
    """
    session = Session()
    q = select(Action).filter(
        Action.channel_id == channel_id).where(
        Action.left_time.is_not(None)).filter(
        Action.join_time.is_not(None))
    if start:
        q = q.filter(Action.join_time >= start)
    if end:
        q = q.filter(Action.join_time <= end + datetime.timedelta(days=1))
    new_left = session.execute(q).all()
    if new_left:
        return len(new_left)
    return 0


def get_left_joined(channel_id, start=None, end=None):
    """
    Вступило с учетом отписок только тех кто вступил - здесь
    количество подписок учитывает только отписки тех
    пользователей кто ВСТУПИЛ за этот же отчетный период. А
    третий пункт - учитывает ВСЕ отписки, включая тех людей что
    пришли в канал И ДО отчетного периода
    кто встпуил и не отписался
    :return:
    """
    logger.debug(f'get_left_joined: {channel_id}, {start}, {end}')
    session = Session()

    if start and end:
        q = select(Action).filter(
            Action.channel_id == channel_id).filter(
            Action.join_time.is_not(None)).filter(
            and_(
                Action.join_time >= start,
                Action.join_time <= end)).filter(
            or_(

                Action.left_time.is_(None))
        )
    else:
        q = select(Action).filter(
            Action.channel_id == channel_id).filter(
            Action.join_time.is_not(None)).filter(
            Action.left_time.is_(None)
        )
        logger.debug(q)
    logger.debug(q)
    res = session.execute(q).scalars().all()
    logger.debug(res)
    if res:
        return len(res)
    return 0


def get_proc_new_left(channel_id, start=None, end=None):
    """
    Процент отписок только НОВЫХ подписчиков за период -
    Показывает соотношение людей отписавшихся от канала
    только из тех кто вступил за отчетный период

    :param channel_id:
    :param start:
    :param end:
    :return:
    """
    session = Session()
    incomings_q = select(Action).filter(
        Action.channel_id == channel_id).where(
        Action.join_time.is_not(None))
    if start:
        incomings_q = incomings_q.filter(Action.join_time >= start)
    if end:
        incomings_q = incomings_q.filter(Action.join_time <= end + datetime.timedelta(days=1))
    incomings = session.execute(incomings_q).all()
    if incomings:
        incomings = len(incomings)
    else:
        incomings = 0

    lefs_q = select(Action).filter(
        Action.channel_id == channel_id).where(
        Action.join_time.is_not(None)).filter(
        Action.left_time.is_not(None)
    )
    if start:
        lefs_q = lefs_q.filter(Action.join_time >= start)
    if end:
        lefs_q = lefs_q.filter(Action.join_time <= end + datetime.timedelta(days=1))
    lefts = session.execute(lefs_q).all()
    if lefts:
        lefts = len(lefts)
    else:
        lefts = 0
    if incomings == 0:
        return '-'
    else:
        return round(lefts / incomings * 100)


def get_join_with_login(channel_id, start=None, end=None):
    """
    Подписки с логинами - подписчики канала, которые установили
    себе логины

    :param channel_id:
    :param start:
    :param end:
    :return:
    """
    session = Session()
    incomings_q = select(Action, User.username).filter(
        Action.channel_id == channel_id).where(
        Action.join_time.is_not(None)).join(
        User
    ).filter(User.username.is_not(None))
    if start:
        incomings_q = incomings_q.filter(Action.join_time >= start)
    if end:
        incomings_q = incomings_q.filter(Action.join_time <= end + datetime.timedelta(days=1))
    incomings = session.execute(incomings_q).all()
    print(incomings)
    if incomings:
        return len(incomings)
    return 0


def get_join_without_login(channel_id, start=None, end=None):
    """
    Подписки без логинов - подписчики, которые не установили
    себе логины и имеют только найди

    :param channel_id:
    :param start:
    :param end:
    :return:
    """
    session = Session()
    incomings_q = select(Action, User.username).filter(
        Action.channel_id == channel_id).where(
        Action.join_time.is_not(None)).join(
        User
    ).filter(User.username.is_(None))
    if start:
        incomings_q = incomings_q.filter(Action.join_time >= start)
    if end:
        incomings_q = incomings_q.filter(Action.join_time <= end + datetime.timedelta(days=1))
    incomings = session.execute(incomings_q).all()
    print(incomings)
    if incomings:
        return len(incomings)
    return 0


def get_avg_time_lefted(channel_id, start=None, end=None):
    """
    Среднее время нахождение в канале ОТПИСАШИХСЯ за
    отчетный период - здесь среднее время, которые провели в
    канале те, кто решил отписаться

    :param channel_id:
    :param start:
    :param end:
    :return:
    """
    session = Session()
    avg_time_lefted_q = select(Action.left_time - Action.join_time).filter(
        Action.channel_id == channel_id).where(
        Action.join_time.is_not(None)).where(Action.left_time.is_not(None)).where(Action.left_time > Action.join_time)
    if start:
        avg_time_lefted_q = avg_time_lefted_q.filter(Action.left_time >= start)
    if end:
        avg_time_lefted_q = avg_time_lefted_q.filter(Action.left_time <= end + datetime.timedelta(days=1))
    avg_time_lefted = session.execute(avg_time_lefted_q).scalars().all()
    total_sec = 0
    for row in avg_time_lefted:
        total_sec += row.total_seconds()
    if avg_time_lefted:
        avg_time = total_sec / len(avg_time_lefted)
        print(datetime.timedelta(seconds=avg_time).days)
        return round(avg_time / 60 / 60 / 24, 1)
    return '-'


def get_avg_day_time_lefted(channel_id, start=None, end=None):
    """
    Среднее время нахождение в канале ОТПИСАШИХСЯ за
    отчетный период больше 1 дня

    :param channel_id:
    :param start:
    :param end:
    :return:
    """
    session = Session()
    avg_time_lefted_q = select(Action.left_time - Action.join_time).filter(
        Action.channel_id == channel_id).where(
        Action.join_time.is_not(None)).where(Action.left_time.is_not(None)).filter(
        Action.left_time - Action.join_time >= datetime.timedelta(days=1))
    if start:
        avg_time_lefted_q = avg_time_lefted_q.filter(Action.left_time >= start)
    if end:
        avg_time_lefted_q = avg_time_lefted_q.filter(Action.left_time <= end + datetime.timedelta(days=1))
    avg_time_lefted = session.execute(avg_time_lefted_q).scalars().all()
    total_sec = 0
    for row in avg_time_lefted:
        total_sec += row.total_seconds()
    if avg_time_lefted:
        avg_time = total_sec / len(avg_time_lefted)
        days = int(avg_time / 60 / 60 // 24)
        hours = int((avg_time - days * 24 * 60 * 60) / 60 // 60)
        mins = int((avg_time - days * 24 * 60 * 60 - hours * 60 * 60) // 60)
        res_text = f'{days} дн, {hours} ч, {mins} м.'
        return res_text
    return '-'


def get_avg_time_all(channel_id, start=None, end=None):
    """
    Среднее время удержания всех подписчиков в канале >1 дня за
    период - здесь мы считаем сколько на настоящий момент в
    среднем время провели в канале те люди, кто подписались и
    не отписались и сколько провели в среднем люди времени, что
    уже отписались. Получаем среднее значение удержания
    подписчиков в канале, которые пробыли в нем более одного
    дня.
    :param channel_id:
    :param start:
    :param end:
    :return:
    """
    session = Session()
    if start and end:
        q = select(func.coalesce(Action.left_time, end) - Action.join_time).where(
            Action.channel_id == channel_id).where(
            Action.join_time.is_not(None)).filter(Action.join_time >= start).filter(Action.join_time <= end)
    else:
        q = select(func.coalesce(Action.left_time, datetime.datetime.now(tz=tz)) - Action.join_time).where(
            Action.channel_id == channel_id).where(
            Action.join_time.is_not(None))
    print(q)
    res = session.execute(q).scalars().all()
    print(res)
    total_sec = 0
    for row in res:
        total_sec += row.total_seconds()
    if res:
        avg_time = total_sec / len(res)
        days = int(avg_time / 60 / 60 // 24)
        hours = int((avg_time - days * 24 * 60 * 60) / 60 // 60)
        mins = int((avg_time - days * 24 * 60 * 60 - hours * 60 * 60) // 60)
        res_text = f'{days} дн, {hours} ч, {mins} м.)'
        return res_text
    else:
        return '-'


def incomings_in_period(channel_id, start=None, end=None):
    """ВСТУПИЛИ ЗА УКАЗАННЫЙ ПЕРИОД"""
    logger.debug('"""ВСТУПИЛИ ЗА УКАЗАННЫЙ ПЕРИОД""')
    session = Session()
    incomings_q = select(Action, Action.user).filter(
        Action.channel_id == channel_id).where(
        Action.join_time.is_not(None)).join(
        User
    ).order_by(Action.join_time)
    logger.debug(incomings_q)
    if start:
        incomings_q = incomings_q.filter(Action.join_time >= start)
    if end:
        incomings_q = incomings_q.filter(Action.join_time <= end + datetime.timedelta(days=1))
    logger.debug(incomings_q)
    incomings: list[Action] = session.execute(incomings_q).scalars().all()
    logger.debug(incomings)
    return incomings


def outgoings_in_period(channel_id, start=None, end=None):
    """ВЫШЛИ ЗА УКАЗАННЫЙ ПЕРИОД			"""
    session = Session()
    outgoings_q = select(Action, Action.user).filter(
        Action.channel_id == channel_id).where(
        Action.join_time.is_not(None)).where(
        Action.left_time.is_not(None)).join(
        User
    ).order_by(Action.left_time)
    logger.debug(outgoings_q)
    if start:
        outgoings_q = outgoings_q.filter(Action.left_time >= start)
    if end:
        outgoings_q = outgoings_q.filter(Action.left_time <= end + datetime.timedelta(days=1))
    outgoings: list[Action] = session.execute(outgoings_q).scalars().all()
    logger.debug(outgoings)
    session.close()
    return outgoings


outgoing_users: list[Action] = outgoings_in_period(1)
print(outgoing_users)
for action in outgoing_users:
    print(action.user)
    print(action.user.username)
