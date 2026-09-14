import os
import uuid
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc
from typing import Sequence
from .schema import CreateEventModel, EventUpdateModel, EventCategory, EventStatus
from .models import EventModel

# create functions for all our crud operation 
# we uses seesion to acces database its provided by sqlacademy 
# questions when do we use sqlmodel and sqlmodelalchemy

class EventService:
    async def get_all_events(
        self,
        session: AsyncSession,
        name: str | None = None,
        organizer: str | None = None,
        location: str | None = None,
        category: EventCategory | None = None,
        status: EventStatus | None = None,
    ) -> Sequence[EventModel]:
        statement = select(EventModel)

        # Dynamic query filters
        if name:
            statement = statement.where(EventModel.name.ilike(f"%{name.strip()}%"))
        if organizer:
            statement = statement.where(EventModel.organizer.ilike(f"%{organizer.strip()}%"))
        if location:
            statement = statement.where(EventModel.location.ilike(f"%{location.strip()}%"))
        if category:
            statement = statement.where(EventModel.category == category.value)
        if status:
            statement = statement.where(EventModel.status == status.value)

        statement = statement.order_by(desc(EventModel.created_at))
        result = await session.exec(statement)
        return result.all()
        
    async def get_event(self, event_uuid: str, session: AsyncSession) -> EventModel | None:
        try:
            # Validate UUID format to prevent DB syntax errors
            parsed_uuid = uuid.UUID(str(event_uuid).strip())
        except (ValueError, AttributeError):
            return None

        statement = select(EventModel).where(EventModel.uid == parsed_uuid)
        result = await session.exec(statement)
        return result.first()
         
    async def create_event(self, event_data: CreateEventModel, session: AsyncSession) -> EventModel:
        # converts the eventdata which is in pydantic model to python dict 
        event_data_dict = event_data.model_dump()

        # Parse date string to datetime safely
        raw_date = event_data_dict.get('date')
        if isinstance(raw_date, str):
            try:
                event_data_dict['date'] = datetime.strptime(raw_date.strip(), '%Y-%m-%d')
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid date format '{raw_date}'. Expected format: YYYY-MM-DD (e.g. 2026-10-25)"
                )

        new_event_data = EventModel(**event_data_dict)
        session.add(new_event_data)
        await session.commit()
        await session.refresh(new_event_data)
        return new_event_data

        
    async def update_event(self, event_uid: str, update_event_data: EventUpdateModel, session: AsyncSession) -> EventModel | None:
        # event to update is coming from db and should be in EventModel format 
        event_to_update = await self.get_event(event_uid, session)
        if event_to_update is not None:
            # IMPORTANT: exclude_unset=True ensures we ONLY update fields that were sent in the request,
            # preventing untouched columns (like date, time, images) from being overwritten with None.
            update_data_dict = update_event_data.model_dump(exclude_unset=True)

            # Safely parse date if updated as string
            if 'date' in update_data_dict and isinstance(update_data_dict['date'], str):
                try:
                    update_data_dict['date'] = datetime.strptime(update_data_dict['date'].strip(), '%Y-%m-%d')
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid date format '{update_data_dict['date']}'. Expected format: YYYY-MM-DD"
                    )

            # Safely parse time if updated as string
            if 'event_time' in update_data_dict and isinstance(update_data_dict['event_time'], str):
                try:
                    time_str = update_data_dict['event_time'].strip()
                    if len(time_str.split(':')) == 2:
                        update_data_dict['event_time'] = datetime.strptime(time_str, '%H:%M').time()
                    else:
                        update_data_dict['event_time'] = datetime.strptime(time_str, '%H:%M:%S').time()
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid time format '{update_data_dict['event_time']}'. Expected format: HH:MM:SS or HH:MM"
                    )

            for k, v in update_data_dict.items():
                if v is not None:
                    setattr(event_to_update, k, v)

            session.add(event_to_update)
            await session.commit()
            await session.refresh(event_to_update)
            return event_to_update
        else:
            return None
        
    async def delete_event(self,event_uid:str,session:AsyncSession):
        event_to_delete = await self.get_event(event_uid,session)
        if event_to_delete is not None:
            await session.delete(event_to_delete)
            await session.commit()
            return event_to_delete
        else:
            return None

    # ---------------------------------------------------------------------------------
    # IMAGE UPLOAD HANDLER
    # ---------------------------------------------------------------------------------
    # HOW NEON POSTGRES HANDLES IMAGES:
    # 1. Neon Postgres stores tabular structured data (e.g. TEXT, ARRAY of VARCHAR).
    # 2. Uploading raw MBs of image binary directly into a SQL database slows it down and bloats it.
    # 3. Instead, we:
    #    a) Save the physical image file (.jpg, .png, etc.) onto disk (or Cloudinary/S3 in production).
    #    b) Generate a accessible web URL (e.g., "/static/abc-123.jpg").
    #    c) Save that string into Neon Postgres's ARRAY(String) column: `event.images`.
    # ---------------------------------------------------------------------------------
    async def upload_event_images(
        self,
        event_uid: str,
        files: list[UploadFile],
        session: AsyncSession
    ) -> EventModel:
        # Step 1: Check if the event actually exists in Neon Postgres
        event = await self.get_event(event_uid, session)
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with UID '{event_uid}' was not found"
            )

        # Step 2: Validate that at least one file was uploaded
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files were provided for upload."
            )

        # Step 3: Define allowed image types for security
        ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Megabytes limit per image

        import tempfile
        try:
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
            os.makedirs(upload_dir, exist_ok=True)
        except OSError:
            upload_dir = os.path.join(tempfile.gettempdir(), "uploads")
            os.makedirs(upload_dir, exist_ok=True)


        saved_image_urls: list[str] = []

        for file in files:
            # Check content type and file extension
            file_ext = os.path.splitext(file.filename or "")[1].lower()
            if file.content_type not in ALLOWED_CONTENT_TYPES and file_ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file format '{file.filename}'. Allowed formats: JPG, PNG, WEBP, GIF."
                )

            # Check file size gracefully
            try:
                # Read file contents into memory safely
                content = await file.read()
                if len(content) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Uploaded file '{file.filename}' is empty."
                    )
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File '{file.filename}' exceeds maximum allowed size of 5MB."
                    )

                # Generate a unique filename using UUID to prevent naming conflicts
                unique_filename = f"{uuid.uuid4()}{file_ext if file_ext else '.jpg'}"
                file_destination = os.path.join(upload_dir, unique_filename)

                # Write binary data to disk
                with open(file_destination, "wb") as f:
                    f.write(content)

                # Construct the static URL that the client/frontend can use
                image_url = f"/static/{unique_filename}"
                saved_image_urls.append(image_url)

            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
            except Exception as e:
                # Gracefully catch filesystem or unexpected I/O errors
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process image '{file.filename}': {str(e)}"
                )
            finally:
                # Ensure the temporary uploaded file stream is closed
                await file.close()

        # Step 4: Append new image URLs to the existing list in Neon Postgres
        # Note: Neon stores this as an ARRAY in PostgreSQL (e.g. ['/static/1.jpg', 'https://...'])
        current_images = list(event.images or [])
        current_images.extend(saved_image_urls)
        event.images = current_images

        # Step 5: Save changes in database
        session.add(event)
        await session.commit()
        await session.refresh(event)

        return event

# we need to determine how we can use thi session here in our path handlers and that is where dependency injection comes in 
# dependency injection is a mechanism that fast api uses to allow you share logic across all route handlers that might need it 

# Adding () after a class name means: "build one real object from this blueprint/sample." so when we do new_event_data EventModel(**event_data_dict) we are creating the actual event we want to save to the db using our class blueprint, more like providing the values/argumets for that Db Modelclass we created 



# The simple rule: whenever you're about to save something new to the database, you first need to turn your raw data (a plain dictionary, or data straight from the request) into a real EventModel object — because the database layer only knows how to save proper EventModel objects, not plain dictionaries.