from typing import Optional, Any
from supabase import create_client, Client
from fastapi import HTTPException, status

import config

supabase_client: Optional[Client] = None

def get_supabase_client() -> Any:
    """
    Dependency to get the Supabase client.
    Initializes the client if it hasn't been already.
    The return type is hinted as 'Any' to simplify FastAPI's OpenAPI schema generation,
    avoiding attempts to create a schema for the complex Supabase Client object.
    The actual returned object will be an instance of supabase.Client.

    Raises:
        HTTPException: If Supabase URL or Key is not configured, or if connection fails.

    Returns:
        Any: An initialized Supabase client instance (actually supabase.Client).
    """
    global supabase_client
    if supabase_client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
            print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in config.py or environment variables.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase configuration missing. Server is not properly configured."
            )
        try:
            supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
            print("Successfully connected to Supabase!")
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to Supabase: {str(e)}"
            )
    return supabase_client

def init_supabase_client():
    """
    Initializes the Supabase client. Can be called at application startup.
    """
    global supabase_client
    if supabase_client is None: 
        get_supabase_client() 
    print("Supabase client initialization check complete.")
