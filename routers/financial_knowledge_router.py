# routers/financial_knowledge_router.py
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

import models # Import Pydantic models from parent directory's models.py
import services # Import service functions
from database import get_supabase_client # Import Supabase client dependency

# Create an APIRouter instance for financial knowledge related endpoints.
# Tags help group endpoints in the OpenAPI documentation.
router = APIRouter(
    tags=["Financial Knowledge Definitions"],
    prefix="/financial_knowledge_definitions" # Optional: prefix for all routes in this router
)

@router.get("", # Path is relative to the router's prefix, so this becomes /financial_knowledge_definitions
            response_model=List[models.FinancialKnowledgeDefinition],
            summary="Get all financial knowledge definitions",
            description="Retrieves a list of all defined financial knowledge categories, levels, and their descriptions.")
async def list_financial_knowledge_definitions(
    supabase: Client = Depends(get_supabase_client) # Dependency injection for Supabase client
):
    """
    Endpoint to retrieve all financial knowledge definitions.
    It uses the `fetch_all_financial_knowledge_definitions` service function.
    """
    try:
        definitions = await services.fetch_all_financial_knowledge_definitions(supabase=supabase)
        return definitions
    except HTTPException as http_exc:
        # Re-raise HTTPException to ensure FastAPI handles it correctly
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors from the service layer or Supabase client
        print(f"Unexpected error in list_financial_knowledge_definitions endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while retrieving financial knowledge definitions: {str(e)}"
        )

# Example of how the definitions map might be used if needed directly in a router (though it's in services now)
# This is just for illustration, the primary use is within other service functions.
# @router.get("/map",
#             response_model=Dict[str, Dict[int, str]],
#             summary="Get financial knowledge definitions as a map (for internal use/alternative format)",
#             include_in_schema=False) # Hides from OpenAPI docs if it's for internal use
# async def get_financial_knowledge_map(
#     supabase: Client = Depends(get_supabase_client)
# ):
#     try:
#         definitions_map = await services.get_all_financial_knowledge_definitions_map(supabase=supabase)
#         return definitions_map
#     except HTTPException as http_exc:
#         raise http_exc
#     except Exception as e:
#         print(f"Unexpected error in get_financial_knowledge_map endpoint: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"An unexpected error occurred: {str(e)}"
#         )
