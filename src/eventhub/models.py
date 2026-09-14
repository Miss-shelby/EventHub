from sqlmodel import SQLModel,Field,Column
from sqlalchemy import ARRAY, String
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime,time
from pydantic import HttpUrl
import uuid


# create our sqlmodel here  similar to pydantic model

class EventModel(SQLModel, table=True):
    __tablename__  = "events"
    uid: uuid.UUID  = Field(
        sa_column=Column(
            pg.UUID, #→ use PostgreSQL's UUID type
            nullable=False, #→ this cannot be empty
            primary_key=True, # → this is the table's primary key
            default=uuid.uuid4    #   → automatically generate a UUID
        )
    )
    name: str
    description:str
    category: str
    date: datetime
    event_time: time
    location: str
    organizer:str
    # image:str
    images:list[str] = Field(sa_column=Column(ARRAY(String)))
    capacity: int
    registered: int
    price: int
    status:str
    created_at:datetime  = Field(sa_column =Column(pg.TIMESTAMP, default=datetime.now))
    updated_at:datetime = Field(sa_column = Column(pg.TIMESTAMP, default=datetime.now))



    def __repr__(self):
        return f"<Event {self.name}>"



# SQLModel's normal behavior
#         ↓
# "I can figure this out myself"

# sa_column=Column(...)
#         ↓
# "Give me more control over exactly how
# this database column behaves."

# NOTE Pydantic model = what data the API accepts.

# SQLModel/EventModel = how that data is represented in the database.

# PostgreSQL = the actual place where the data is stored and where database-level rules are enforced.

# NOTE We use alembic to run db migration, db migation is useful when we want to edit our alredy created db withouting wiping the entire  data out, expecially when we make chnages in our code that affects the db llike changing model feild name uv add alembic