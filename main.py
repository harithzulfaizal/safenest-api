import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import APP_TITLE, APP_DESCRIPTION, APP_VERSION
from routers import users_router, financial_knowledge_router, insights_router, auth_router
from database import init_supabase_client

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION
)

# origins = [
#     # "http://localhost:3000",
#     "*" 
#     # Add other origins if needed, e.g., your deployed frontend URL
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
