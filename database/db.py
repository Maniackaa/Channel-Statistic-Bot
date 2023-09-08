import asyncio
import datetime
import sys
import uuid
from sqlite3 import Timestamp
from time import time

from sqlalchemy import create_engine, ForeignKey, Date, String, DateTime, \
    Float, UniqueConstraint, Integer, MetaData, BigInteger, ARRAY
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import sessionmaker

from config_data.conf import LOGGING_CONFIG, conf, tz
import logging.config

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('bot_logger')
err_log = logging.getLogger('errors_logger')
metadata = MetaData()
db_url = f"postgresql+psycopg2://{conf.db.db_user}:{conf.db.db_password}@{conf.db.db_host}:{conf.db.db_port}/{conf.db.database}"
engine = create_engine(db_url, echo=False)


Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    tg_id: Mapped[str] = mapped_column(String(30))
    username: Mapped[str] = mapped_column(String(50), nullable=True)
    register_date: Mapped[time] = mapped_column(DateTime(timezone=True), nullable=True)
    channels: Mapped[list['Channel']] = relationship(back_populates='owner')
    referral: Mapped[str] = mapped_column(String(20), nullable=True)
    actions: Mapped[list['Action']] = relationship(back_populates='user')
    secrets: Mapped[list] = mapped_column(ARRAY(String(36)), nullable=True)

    def __repr__(self):
        return f'{self.id}. {self.tg_id} {self.username or "-"}'


class Channel(Base):
    __tablename__ = 'channels'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    channel_id: Mapped[int] = mapped_column(BigInteger(), unique=True)
    title: Mapped[str] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(250), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer(), default=1)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    owner: Mapped['User'] = relationship(back_populates='channels')
    secret: Mapped[str] = mapped_column(String(36), nullable=True, default=lambda: uuid.uuid4())

    def __repr__(self):
        return f'Канал {self.id}. {self.title}'

    def set(self, key, value):
        _session = Session()
        channel = _session.query(Channel).filter(Channel.id == self.id).one_or_none()
        setattr(channel, key, value)
        _session.commit()
        logger.debug(f'Изменено значение {key} на {value}')


class Action(Base):
    __tablename__ = 'actions'
    id: Mapped[int] = mapped_column(primary_key=True,
                                    autoincrement=True,
                                    comment='Первичный ключ')
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    user: Mapped['User'] = relationship(back_populates='actions')
    channel_id: Mapped[int] = mapped_column(ForeignKey('channels.id', ondelete='CASCADE'))
    join_time: Mapped[time] = mapped_column(DateTime(timezone=True), nullable=True)
    left_time: Mapped[time] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f'Action {self.id}. {self.join_time} - {self.left_time}'

Base.metadata.create_all(engine)
