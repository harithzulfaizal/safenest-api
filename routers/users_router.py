# routers/users_router.py
from typing import List, Dict, Any # Added Any
from fastapi import APIRouter, Depends, HTTPException, Path, status
from supabase import Client # Client is still imported for type hinting in services if needed, but not directly for Depends here if causing issues

# Changed from relative imports (e.g., ..models) to direct imports
# assuming 'safenest-api' is the project root and on Python's path.
import models # Import Pydantic models (e.g., models.UserProfile)
import services # Import service functions (e.g., services.fetch_user_profile)
from database import get_supabase_client # Import Supabase client dependency

# Create an APIRouter instance for user-related endpoints.
# All routes defined here will be prefixed with "/users".
router = APIRouter(
    prefix="/users",
    tags=["User Details"] # Group these endpoints under "User Details" in API docs
)

# --- Granular User Detail Endpoints ---

@router.get("/{user_id}/profile",
            response_model=models.UserProfile,
            summary="Get a user's profile",
            description="Retrieves the profile information for a specific user by their ID.")
async def get_user_profile_route(
    user_id: int = Path(..., title="The ID of the user", ge=1, example=1),
    supabase: Any = Depends(get_supabase_client) # Changed Client to Any for the injected dependency
):
    """
    Endpoint to fetch a user's profile.
    Uses the `fetch_user_profile` service function.
    """
    try:
        # Note: The 'supabase' variable here will be an instance of supabase.Client
        # The type hint 'Any' is just for FastAPI's introspection.
        profile = await services.fetch_user_profile(user_id=user_id, supabase=supabase)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User profile with ID {user_id} not found."
            )
        return profile
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_user_profile_route for user_id {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/{user_id}/financial_knowledge",
            response_model=List[models.UserFinancialKnowledgeDetail],
            summary="Get a user's financial knowledge with descriptions",
            description="Retrieves the financial knowledge levels for a specific user, including descriptive text for each level.")
async def get_user_financial_knowledge_route(
    user_id: int = Path(..., title="The ID of the user", ge=1, example=1),
    supabase: Any = Depends(get_supabase_client), # Changed Client to Any
    definitions_map: Dict[str, Dict[int, str]] = Depends(services.get_definitions_map_with_supabase_dependency)
):
    """
    Endpoint to fetch a user's financial knowledge.
    First checks if the user exists, then fetches their knowledge details.
    """
    try:
        if not await services.check_user_exists(user_id=user_id, supabase=supabase):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found. Cannot fetch financial knowledge."
            )
        
        knowledge_details = await services.fetch_user_financial_knowledge(
            user_id=user_id,
            supabase=supabase,
            definitions_map=definitions_map
        )
        return knowledge_details
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_user_financial_knowledge_route for user_id {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/{user_id}/income",
            response_model=List[models.IncomeDetail],
            summary="Get a user's income sources",
            description="Retrieves all recorded income sources for a specific user.")
async def get_user_income_route(
    user_id: int = Path(..., title="The ID of the user", ge=1, example=1),
    supabase: Any = Depends(get_supabase_client) # Changed Client to Any
):
    """Endpoint to fetch user's income details."""
    try:
        if not await services.check_user_exists(user_id=user_id, supabase=supabase):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
        
        income_details = await services.fetch_user_income(user_id=user_id, supabase=supabase)
        return income_details
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_user_income_route for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{user_id}/debts",
            response_model=List[models.DebtDetail],
            summary="Get a user's debts",
            description="Retrieves all recorded debt obligations for a specific user.")
async def get_user_debts_route(
    user_id: int = Path(..., title="The ID of the user", ge=1, example=1),
    supabase: Any = Depends(get_supabase_client) # Changed Client to Any
):
    """Endpoint to fetch user's debt details."""
    try:
        if not await services.check_user_exists(user_id=user_id, supabase=supabase):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")

        debt_details = await services.fetch_user_debts(user_id=user_id, supabase=supabase)
        return debt_details
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_user_debts_route for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{user_id}/expenses",
            response_model=List[models.ExpenseDetail],
            summary="Get a user's expenses",
            description="Retrieves all recorded expenses for a specific user, ordered by timestamp (descending).")
async def get_user_expenses_route(
    user_id: int = Path(..., title="The ID of the user", ge=1, example=1),
    supabase: Any = Depends(get_supabase_client) # Changed Client to Any
):
    """Endpoint to fetch user's expense details."""
    try:
        if not await services.check_user_exists(user_id=user_id, supabase=supabase):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")

        expense_details = await services.fetch_user_expenses(user_id=user_id, supabase=supabase)
        return expense_details
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_user_expenses_route for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# --- Comprehensive User Details Endpoint ---

@router.get("/{user_id}/comprehensive_details",
            response_model=models.ComprehensiveUserDetails,
            tags=["User Details - Comprehensive"], 
            summary="Get all financial information for a specific user",
            description="Retrieves a comprehensive set of financial details for a user, including profile, financial knowledge, income, debts, and expenses.")
async def get_comprehensive_user_details_route(
    user_id: int = Path(..., title="The ID of the user to retrieve", ge=1, example=1),
    supabase: Any = Depends(get_supabase_client), # Changed Client to Any
    definitions_map: Dict[str, Dict[int, str]] = Depends(services.get_definitions_map_with_supabase_dependency)
):
    """
    Endpoint to fetch comprehensive financial details for a user.
    This orchestrates calls to various service functions.
    """
    try:
        comprehensive_details = await services.get_comprehensive_user_details_service(
            user_id=user_id,
            supabase=supabase,
            definitions_map=definitions_map
        )
        return comprehensive_details
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_comprehensive_user_details_route for user_id {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while fetching comprehensive user details: {str(e)}"
        )
