import uuid
from enum import Enum
from datetime import datetime, time
from pydantic import BaseModel, HttpUrl

# ---------------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------------
class EventStatus(str, Enum):
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"


class EventCategory(str, Enum):
    TECHNOLOGY = "Technology"
    COMMUNITY = "Community"
    MUSIC = "Music"
    WORKSHOP = "Workshop"
    BUSINESS = "Business"
    OTHER = "Other"


# ---------------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------------------------------
class EventReadModel(BaseModel):
    uid: uuid.UUID
    name: str
    description: str
    category: EventCategory
    date: datetime
    event_time: time
    location: str
    organizer: str
    images: list[str] | None = None
    capacity: int
    registered: int
    price: int
    status: EventStatus
    created_at: datetime
    updated_at: datetime 


class CreateEventModel(BaseModel):
    name: str
    description: str
    category: EventCategory
    date: str
    event_time: time
    location: str
    organizer: str
    images: list[str] | None = None
    capacity: int = 100
    registered: int = 0
    price: int = 0
    status: EventStatus = EventStatus.UPCOMING


class EventUpdateModel(BaseModel):
    name: str | None = None
    description: str | None = None
    category: EventCategory | None = None
    date: datetime | None = None
    event_time: time | None = None
    location: str | None = None
    organizer: str | None = None
    images: list[str] | None = None
    capacity: int | None = None
    registered: int | None = None
    price: int | None = None
    status: EventStatus | None = None


class Tags(Enum):
    event = "Event"