# main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware

# Import configurations and application metadata
from config import APP_TITLE, APP_DESCRIPTION, APP_VERSION

# Import router modules
from routers import users_router, financial_knowledge_router, insights_router, auth_router

# Import database utility
from database import init_supabase_client

# Create the FastAPI application instance
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION
)

# --- CORS Middleware Configuration ---
# List of origins that are allowed to make requests.
# For development, you might allow your local React app's origin.
# For production, you'd list your actual frontend domain(s).
origins = [
    # "http://localhost:3000",
    "*"  # Your React frontend
    # Add other origins if needed, e.g., your deployed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows specific origins
    allow_credentials=True, # Allows cookies to be included in requests
    allow_methods=["*"],    # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],    # Allows all headers
)
# --- End CORS Middleware Configuration ---


@app.on_event("startup")
async def startup_event():
    print("Application startup: Initializing resources...")
    init_supabase_client()
    print("Application startup complete.")

app.include_router(users_router.router)
app.include_router(financial_knowledge_router.router)
app.include_router(insights_router.router)
app.include_router(auth_router.router)


@app.get("/", summary="Root Endpoint", tags=["General"])
async def read_root():
    return {
        "message": f"Welcome to the {APP_TITLE}",
        "version": APP_VERSION,
        "documentation": "/docs"
    }

if __name__ == "__main__":
    print(f"Starting Uvicorn server for {APP_TITLE} on http://127.0.0.1:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)