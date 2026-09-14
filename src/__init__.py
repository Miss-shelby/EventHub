import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from src.eventhub.routes import event_router
from contextlib import asynccontextmanager
from src.db.main import init_db

import tempfile

# ---------------------------------------------------------------------------------
# DIRECTORY PATHS SETUP
# ---------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

try:
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except OSError:
    UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)


@asynccontextmanager
async def life_span(app:FastAPI):    #What should happen during the life of my server?"
    print(f"Server is running....")
    await init_db()                #sets up/initializes your database
    yield                          #Separates startup from shutdown, so 
    print(f"Server has ended .....")

version = "v1"
app = FastAPI(
    title='EventHub',
    description='A RESTAPI For event services',
    version=version,
    lifespan=life_span #Use my life_span function to manage what happens when this application starts and stops."
)

# ---------------------------------------------------------------------------------
# CORS MIDDLEWARE
# ---------------------------------------------------------------------------------
# Allows frontends running on other domains (e.g. Vercel, Netlify, localhost:3000)
# to make requests without being blocked by browser CORS security.
# ---------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the static directory so uploaded images can be opened in the browser
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# Mount frontend assets (css, js)
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

# Serve the testing dashboard at the root URL
@app.get("/", include_in_schema=False)
async def serve_dashboard():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to EventHub API. Visit /docs for API documentation."}

app.include_router(event_router,prefix= f"/api/{version}/events",tags=['Event']) #connect our routes 



# endpoints needed to create 
# 1. create event (registration) , 2. get all events with search query for filter , 3.get event by id 4. edit created event, 5.delete event 

# uv run fastapi dev src 

# NOTE The main thing this file does is:

# Create the FastAPI app, set up what should happen when the server starts/stops, initialize the database, and connect the event routes.

# Explanation of concepts:
# asynccontextmanager:its a python tool used to create context manager that is used to determine/specify  what to do when serve starts and ends so basically @asynccontextmanager allows us to define startup and shutdown behavior for our FastAPI application.

# yield creates a pause point:And that's why we put things we want before the application starts above yield, and things we want when the application is shutting down below yield.