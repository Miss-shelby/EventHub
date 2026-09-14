from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from src.config import Config
from sqlmodel.ext.asyncio.session import AsyncSession

engine = create_async_engine(
    url=Config.DATABASE_URL,
    echo=True   #Show me the SQL queries you're executing in my terminal."
)

async def init_db():
    async with engine.begin() as conn:
        from src.eventhub.models import EventModel

        await conn.run_sync(SQLModel.metadata.create_all)

# uses that address to open a connection to your database, and gives you one function to test whether that connection work, basically creates a connection to the db 


# create out cord function which serves as dependency injection, you need a session class when you want to create a session function 

async def get_session():
    Session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with Session() as session:
        yield session


# NOTE:SQLModel  is basically a library built using Pydantic + SQLAlchemy, ITS a simpler way of defining and working with database models while still using SQLAlchemy underneath.

# SQLAlchemy is the underlying database toolkit/ORM, It handles things like db engines, connections,sessions, transactions, orm/db commuinication 

# What is an engine?

# Think of the engine as the manager/bridge responsible for communicating with your database.

# You give it your database address:

# Config.DATABASE_URL

# and it knows:

# "Okay, this is the PostgreSQL database I need to communicate with."

# NOTE This file Creates the async database engine, initializes the database tables when FastAPI starts, and creates database sessions that your routes/services can use.