import os
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
# We try multiple locations to support both local dev and Docker/deployment
possible_dotenv_paths = [
    os.path.join(os.path.dirname(__file__), '.env'),      # backend root (Docker)
    os.path.join(os.path.dirname(__file__), '..', '.env') # project root (Local)
]
for path in possible_dotenv_paths:
    if os.path.exists(path):
        load_dotenv(path)

from fastapi import FastAPI
from run.routes.search import router as search_router

app = FastAPI(
    title="RAK Tiles AI API",
    version="1.0.0"
)

# Allowed origins for CORS (comma-separated list defined in environment)
# Defaults to localhost for local development
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5174")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# Standard CORS middleware for API accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prefix API routes for versioning and clarity
app.include_router(search_router, prefix="/api")

# Mount static files for product images
image_dir = os.path.join(os.path.dirname(__file__), "data", "page_images")
app.mount("/images", StaticFiles(directory=image_dir), name="images")

@app.get("/")
async def root():
    return {"message": "RAK Tiles API is online"}