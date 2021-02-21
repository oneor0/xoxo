import os

import databases
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from xoxo.schemas import UserInDB
from xoxo.password import get_password_hash

DATABASE_URL = os.environ["DATABASE_URL"]

database = databases.Database(DATABASE_URL)

engine = sa.create_engine(DATABASE_URL)

metadata = sa.MetaData()

users = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("username", sa.String, nullable=False),
    sa.Column("password", sa.String, nullable=False),
)

moves = sa.Table(
    "moves",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("row", sa.Integer, nullable=False),
    sa.Column("col", sa.Integer, nullable=False),
    sa.Column("is_ai", sa.Boolean, nullable=False),
    sa.Column("status", sa.String, nullable=False),
    sa.Column("board", ARRAY(sa.Boolean), nullable=False),
    sa.Column(
        "created_at", sa.DateTime, server_default=sa.sql.functions.now(), nullable=False
    ),
    sa.Column("user_id", sa.ForeignKey(users.c.id, ondelete="CASCADE"), nullable=False),
)

metadata.create_all(engine)


async def get_user(username):
    query = users.select().where(users.c.username == username)
    user = await database.fetch_one(query)
    if user:
        return UserInDB(**user)


async def create_user(username, password):
    hashed_password = get_password_hash(password)
    query = users.insert().values(username=username, password=hashed_password)
    await database.execute(query)


async def create_move(**values):
    query = moves.insert().values(**values)
    await database.execute(query)


async def get_last_move(user_id):
    query = (
        moves.select()
        .where(moves.c.user_id == user_id)
        .order_by(sa.desc(moves.c.created_at))
    )
    return await database.fetch_one(query)
