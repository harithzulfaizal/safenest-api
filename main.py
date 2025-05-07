# main.py
import uvicorn
from fastapi import FastAPI

# Import configurations and application metadata
from config import APP_TITLE, APP_DESCRIPTION, APP_VERSION

# Import router modules
from routers import users_router, financial_knowledge_router, insights_router

# Import database utility (optional, if you want to initialize client on startup)
from database import init_supabase_client #, close_supabase_client

# Create the FastAPI application instance
# Title, description, and version are taken from config.py for centralized management.
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION
)

# --- Event Handlers (Optional) ---
@app.on_event("startup")
async def startup_event():
    """
    Actions to perform when the application starts.
    For example, initializing database connections, loading caches, etc.
    """
    print("Application startup: Initializing resources...")
    init_supabase_client() # Initialize Supabase client (optional, as it's lazy-loaded by Depends)
    # You could also pre-warm the financial knowledge definitions cache here if desired:
    # from .services import get_all_financial_knowledge_definitions_map
    # from .database import get_supabase_client as get_client_for_startup # Avoid circular if not careful
    # try:
    #     # This is a bit tricky due to async context and dependency injection outside a request.
    #     # A simpler way is to let the first request to relevant endpoints populate the cache.
    #     # Or, create a dedicated non-request-bound function to fetch and cache.
    #     print("Attempting to pre-warm financial knowledge definitions cache...")
    #     # client = get_client_for_startup() # This would re-trigger init if not careful with global state
    #     # await get_all_financial_knowledge_definitions_map(client)
    #     # print("Financial knowledge definitions cache pre-warmed (if data available).")
    # except Exception as e:
    #     print(f"Could not pre-warm cache during startup: {e}")
    print("Application startup complete.")

# @app.on_event("shutdown")
# async def shutdown_event():
#     """
#     Actions to perform when the application shuts down.
#     For example, closing database connections, releasing resources.
#     """
#     print("Application shutdown: Cleaning up resources...")
#     # await close_supabase_client() # If you implement a close method for Supabase client
#     print("Application shutdown complete.")

# --- Include Routers ---
# Include the user-related routes from the users_router module.
# All routes in users_router will be available under the prefix defined within that router (e.g., /users).
app.include_router(users_router.router)

# Include the financial knowledge definition routes.
# Routes in financial_knowledge_router will be available under its defined prefix.
app.include_router(financial_knowledge_router.router)

app.include_router(insights_router.router)

# --- Root Endpoint (Optional) ---
@app.get("/", summary="Root Endpoint", tags=["General"])
async def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {
        "message": f"Welcome to the {APP_TITLE}",
        "version": APP_VERSION,
        "documentation": "/docs"
    }

if __name__ == "__main__":
    print(f"Starting Uvicorn server for {APP_TITLE} on http://127.0.0.1:8000")
    print("Access API docs (Swagger UI) at http://127.0.0.1:8000/docs")
    print("Access ReDoc at http://0.0.0.0:8000/redoc")
 
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

