import os
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Points to the .env in your root folder
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

from fastapi import FastAPI
from run.routes.search import router as search_router
app = FastAPI(
    title="RAK Tiles AI API",
    version="1.0.0"
)

# Allowed origins — set ALLOWED_ORIGINS in your environment (comma-separated).
# Example: ALLOWED_ORIGINS=https://your-app.vercel.app
# Falls back to localhost only for local development.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# It is good practice to add a prefix so your URL is /api/search
app.include_router(search_router, prefix="/api")

# Mount static files for product images
image_dir = os.path.join(os.path.dirname(__file__), "data", "page_images")
app.mount("/images", StaticFiles(directory=image_dir), name="images")

@app.get("/")
async def root():
    return {"message": "RAK Tiles API is online"}