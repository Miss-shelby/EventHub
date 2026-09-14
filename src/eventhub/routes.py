from fastapi import APIRouter, Query, status, Header, Depends, UploadFile, File
from fastapi.exceptions import HTTPException
from typing import Annotated, Sequence
from src.eventhub.schema import (
    EventUpdateModel, 
    EventReadModel, 
    Tags, 
    CreateEventModel, 
    EventCategory, 
    EventStatus
)
from src.eventhub.models import EventModel
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from src.eventhub.service import EventService

event_router = APIRouter()
event_service = EventService()


# ---------------------------------------------------------------------------------
# 1. GET ALL EVENTS (With Multi-field Filtering & Enum Support)
# ---------------------------------------------------------------------------------
@event_router.get(
    '/', 
    response_model=list[EventReadModel],
    status_code=status.HTTP_200_OK,
    summary="Get all events with optional filters"
)
async def get_all_events(
    session: AsyncSession = Depends(get_session), 
    name: Annotated[str | None, Query(description="Search by event name (case-insensitive)")] = None,
    organizer: Annotated[str | None, Query(description="Search by organizer name")] = None,
    location: Annotated[str | None, Query(description="Search by event location")] = None,
    category: Annotated[EventCategory | None, Query(description="Filter by exact category")] = None,
    event_status: Annotated[EventStatus | None, Query(alias="status", description="Filter by event status")] = None,
) -> Sequence[EventModel]:
    events = await event_service.get_all_events(
        session=session,
        name=name,
        organizer=organizer,
        location=location,
        category=category,
        status=event_status,
    )
    return events


# ---------------------------------------------------------------------------------
# 2. CREATE EVENT
# ---------------------------------------------------------------------------------
@event_router.post(
    '/', 
    status_code=status.HTTP_201_CREATED,
    response_model=EventReadModel,
    summary="Create a new event"
)
async def create_event(
    event_data: CreateEventModel,
    session: AsyncSession = Depends(get_session)
) -> EventModel:
    new_event = await event_service.create_event(event_data, session)
    return new_event


# ---------------------------------------------------------------------------------
# 3. GET EVENT BY UID
# ---------------------------------------------------------------------------------
@event_router.get(
    '/{event_uid}', 
    response_model=EventReadModel,
    status_code=status.HTTP_200_OK,
    summary="Get a single event by UID"
)
async def get_event(
    event_uid: str,
    session: AsyncSession = Depends(get_session)
) -> EventModel:
    event = await event_service.get_event(event_uid, session)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Event with UID '{event_uid}' was not found."
        )
    return event


# ---------------------------------------------------------------------------------
# 4. UPDATE EVENT (PATCH)
# ---------------------------------------------------------------------------------
@event_router.patch(
    '/{event_uid}',
    response_model=EventReadModel,
    status_code=status.HTTP_200_OK,
    summary="Partially update an event"
)
async def update_event(
    event_uid: str, 
    event_update_data: EventUpdateModel,
    session: AsyncSession = Depends(get_session)
) -> EventModel:
    updated_event = await event_service.update_event(event_uid, event_update_data, session)
    if updated_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Event with UID '{event_uid}' was not found and could not be updated."
        )
    return updated_event 


# ---------------------------------------------------------------------------------
# 5. DELETE EVENT
# ---------------------------------------------------------------------------------
@event_router.delete(
    '/{event_uid}',
    status_code=status.HTTP_200_OK,
    summary="Delete an event by UID"
)
async def delete_event(
    event_uid: str,
    session: AsyncSession = Depends(get_session)
) -> dict:
    deleted_event = await event_service.delete_event(event_uid, session)
    if deleted_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Event with UID '{event_uid}' was not found and could not be deleted."
        )
    return {
        "status": "success",
        "message": f"Event '{deleted_event.name}' with UID '{event_uid}' was deleted successfully."
    }


# ---------------------------------------------------------------------------------
# IMAGE UPLOADING ROUTE
# ---------------------------------------------------------------------------------
# 1. Accepts actual image binary files (.jpg, .png, .webp, .gif) via multipart/form-data.
# 2. Passes the files to event_service to save them to disk/storage.
# 3. Saves the resulting URL paths inside Neon Postgres's ARRAY column.
# 4. Returns the updated EventReadModel object including the new images.
# ---------------------------------------------------------------------------------
@event_router.post(
    '/{event_uid}/images',
    response_model=EventReadModel,
    status_code=status.HTTP_200_OK,
    summary="Upload image files for an event"
)
async def upload_event_images(
    event_uid: str,
    files: list[UploadFile] = File(..., description="Select one or more image files (.jpg, .png, .webp, .gif)"),
    session: AsyncSession = Depends(get_session)
):
    updated_event = await event_service.upload_event_images(event_uid, files, session)
    return updated_event





# event_router.get('/headers')
# async def get_headers(accept:Annotated[str |None,Header()]  = None,
#                        content_type:Annotated[str |None,Header()]  = None,
#                        user_agent:Annotated[str |None,Header()]  = None,
#                        host:Annotated[str |None,Header()]  = None):
#     request_headers  = {}
#     request_headers['Accept']  = accept
#     request_headers['Content-Type']  =  content_type
#     request_headers['User-Agent']  =  user_agent
#     request_headers['Host']  =  host

#     return request_headers


# {
#   "name": "Blockchain week",
#   "description": "SE Blockchain week",
#   "category": "Tech",
#   "date": "26-08-2019",
#   "time": "7:00",
#   "location": "Awka",
#   "organizer": "Blockhive",
#   "image": ".src/ghgh",
#   "capacity": 100,
#   "registered": 200,
#   "price": 1200,
#   "status": "upcoming"
# }

# Todos:
# use ai to understand the setup
# implement filter by name, category wich will be enum, status will be enum too.
# implement image upload 
# handle error properly expecially date time conversion 
# implement pagination