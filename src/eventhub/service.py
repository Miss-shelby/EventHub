import os
import uuid
import cloudinary
import cloudinary.uploader
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc
from typing import Sequence
from .schema import CreateEventModel, EventUpdateModel, EventCategory, EventStatus
from .models import EventModel
from src.config import Config

# ---------------------------------------------------------------------------------
# CLOUDINARY CONFIGURATION
# ---------------------------------------------------------------------------------
# Cloudinary stores your images in the cloud and returns a permanent HTTPS URL.
# This URL is what gets saved into the Neon Postgres 'images' array column.
# ---------------------------------------------------------------------------------
cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET,
    secure=True  # Always use HTTPS URLs
)

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
         
    async def create_event(
        self,
        event_data: CreateEventModel,
        session: AsyncSession,
        files: list[UploadFile] | None = None
    ) -> EventModel:
        # Convert the Pydantic model to a plain dict for the DB model
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

        # Create the event record with an empty images list for now
        new_event = EventModel(**event_data_dict, images=[])
        session.add(new_event)
        await session.commit()
        await session.refresh(new_event)

        # If image files were included in the same request, process and save them now
        if files:
            new_event = await self.upload_event_images(str(new_event.uid), files, session)

        return new_event

        
    async def update_event(
        self,
        event_uid: str,
        update_event_data: EventUpdateModel,
        session: AsyncSession,
        files: list[UploadFile] | None = None
    ) -> EventModel | None:
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

            # If new image files were included in the same request, save and append them now
            if files:
                event_to_update = await self.upload_event_images(str(event_to_update.uid), files, session)

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
    # IMAGE UPLOAD HANDLER (Cloudinary)
    # ---------------------------------------------------------------------------------
    # HOW THIS WORKS:
    # 1. We read the image bytes from the uploaded file into memory.
    # 2. We upload those bytes directly to Cloudinary — no disk writes needed.
    # 3. Cloudinary returns a permanent HTTPS URL (e.g. https://res.cloudinary.com/...).
    # 4. We save that URL string into Neon Postgres's ARRAY column: `event.images`.
    # This works on any platform (Vercel, Railway, local) because nothing touches the filesystem.
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

        saved_image_urls: list[str] = []

        for file in files:
            # Validate content type and file extension
            file_ext = os.path.splitext(file.filename or "")[1].lower()
            if file.content_type not in ALLOWED_CONTENT_TYPES and file_ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file format '{file.filename}'. Allowed formats: JPG, PNG, WEBP, GIF."
                )

            try:
                # Read file bytes into memory
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

                # Upload bytes directly to Cloudinary — no disk I/O, works on Vercel
                # public_id: unique name for the file in your Cloudinary media library
                # folder: organises uploads under 'eventhub/' in your Cloudinary dashboard
                # resource_type: 'image' tells Cloudinary to apply image optimisations
                upload_result = cloudinary.uploader.upload(
                    content,
                    public_id=str(uuid.uuid4()),
                    folder="eventhub",
                    resource_type="image",
                    overwrite=False,
                )

                # Cloudinary returns a permanent HTTPS URL — this is what we store in the DB
                image_url = upload_result["secure_url"]
                saved_image_urls.append(image_url)

            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload image '{file.filename}' to Cloudinary: {str(e)}"
                )
            finally:
                await file.close()

        # Step 4: Append new Cloudinary URLs to the existing images array in Neon Postgres
        current_images = list(event.images or [])
        current_images.extend(saved_image_urls)
        event.images = current_images

        # Step 5: Save updated image list to database
        session.add(event)
        await session.commit()
        await session.refresh(event)

        return event

# we need to determine how we can use thi session here in our path handlers and that is where dependency injection comes in 
# dependency injection is a mechanism that fast api uses to allow you share logic across all route handlers that might need it 

# Adding () after a class name means: "build one real object from this blueprint/sample." so when we do new_event_data EventModel(**event_data_dict) we are creating the actual event we want to save to the db using our class blueprint, more like providing the values/argumets for that Db Modelclass we created 



# The simple rule: whenever you're about to save something new to the database, you first need to turn your raw data (a plain dictionary, or data straight from the request) into a real EventModel object — because the database layer only knows how to save proper EventModel objects, not plain dictionaries.