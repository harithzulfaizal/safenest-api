from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status, Depends # Added Depends
from supabase import Client # Keep for internal reference if needed

# Direct import
import models # Import Pydantic models from models.py
from database import get_supabase_client # Import the dependency provider

# --- Financial Knowledge Definitions Cache ---
_financial_knowledge_definitions_cache: Optional[Dict[str, Dict[int, str]]] = None

async def get_all_financial_knowledge_definitions_map(
    supabase: Any # This should remain Any
) -> Dict[str, Dict[int, str]]:
    """
    Fetches all financial knowledge definitions from Supabase and caches them.
    The cache is structured as: {'CategoryName': {level_num: 'description'}}
    This function is called by other functions/dependencies.

    Args:
        supabase: Initialized Supabase client (type hinted as Any for FastAPI compatibility).
    """
    global _financial_knowledge_definitions_cache
    if _financial_knowledge_definitions_cache is not None:
        # In a real-world scenario with Depends, caching is handled by FastAPI per request.
        # This global cache here is simpler but has implications for multi-worker setups
        # if not managed carefully (e.g., needs to be populated per worker or be process-safe).
        # For now, we assume it's populated when first called.
        return _financial_knowledge_definitions_cache

    try:
        # supabase is expected to be an actual Supabase Client instance here
        response = supabase.table("financial_knowledge_definitions").select("category, level, description").execute()
        
        definitions_map: Dict[str, Dict[int, str]] = {}
        if response.data:
            for item in response.data:
                category = item.get("category")
                level = item.get("level")
                description = item.get("description")
                if category and level is not None and description: 
                    if category not in definitions_map:
                        definitions_map[category] = {}
                    definitions_map[category][level] = description
        
        _financial_knowledge_definitions_cache = definitions_map
        return _financial_knowledge_definitions_cache
    except Exception as e: 
        print(f"Exception in get_all_financial_knowledge_definitions_map: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while fetching financial knowledge definitions: {str(e)}"
        )

# --- New Wrapper Dependency Function ---
async def get_definitions_map_with_supabase_dependency(
    # This function explicitly depends on get_supabase_client.
    # FastAPI will resolve this dependency and provide the supabase_client.
    # The type hint for supabase_client_instance is Any because get_supabase_client returns Any.
    supabase_client_instance: Any = Depends(get_supabase_client)
) -> Dict[str, Dict[int, str]]:
    """
    A dependency function that provides the definitions_map.
    It explicitly depends on get_supabase_client to obtain the Supabase client,
    and then calls the core logic function.
    This helps clarify the dependency chain for FastAPI's OpenAPI generation.
    """
    # Now call the original function, passing the resolved Supabase client
    return await get_all_financial_knowledge_definitions_map(supabase=supabase_client_instance)


async def fetch_all_financial_knowledge_definitions(
    supabase: Any # Changed from Client to Any
) -> List[models.FinancialKnowledgeDefinition]:
    """
    Fetches all financial knowledge definitions from the database.

    Args:
        supabase: Initialized Supabase client (type hinted as Any).
    """
    try:
        response = supabase.table("financial_knowledge_definitions").select("*").order("category").order("level").execute()
        return [models.FinancialKnowledgeDefinition(**item) for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error in fetch_all_financial_knowledge_definitions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def fetch_user_profile(user_id: int, supabase: Any) -> Optional[models.UserProfile]:
    """
    Fetches a user's profile from the database.

    Args:
        user_id: The ID of the user.
        supabase: Initialized Supabase client (type hinted as Any).
    """
    try:
        response = supabase.table("users").select("*").eq("user_id", user_id).maybe_single().execute()
        if not response.data:
            return None
        return models.UserProfile(**response.data)
    except Exception as e: 
        print(f"Error in fetch_user_profile for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user profile: {str(e)}")

async def check_user_exists(user_id: int, supabase: Any) -> bool:
    """
    Checks if a user exists in the database.

    Args:
        user_id: The ID of the user.
        supabase: Initialized Supabase client (type hinted as Any).
    """
    try:
        response = supabase.table("users").select("user_id").eq("user_id", user_id).maybe_single().execute()
        return response.data is not None
    except Exception as e:
        print(f"Error in check_user_exists for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error while checking user existence: {str(e)}")


async def fetch_user_financial_knowledge(
    user_id: int,
    supabase: Any, 
    definitions_map: Dict[str, Dict[int, str]]
) -> List[models.UserFinancialKnowledgeDetail]:
    """
    Fetches a user's financial knowledge details, enriching them with descriptions.

    Args:
        user_id: The ID of the user.
        supabase: Initialized Supabase client (type hinted as Any).
        definitions_map: Pre-fetched map of financial knowledge definitions.
    """
    try:
        knowledge_response = supabase.table("user_financial_knowledge").select("category, level").eq("user_id", user_id).execute()
        
        result: List[models.UserFinancialKnowledgeDetail] = []
        if knowledge_response.data:
            for item in knowledge_response.data:
                category = item.get("category")
                level = item.get("level")
                if category is None or level is None:
                    print(f"Warning: Skipping financial knowledge item for user {user_id} due to missing category/level: {item}")
                    continue
                description = definitions_map.get(category, {}).get(level)
                result.append(models.UserFinancialKnowledgeDetail(category=category, level=level, description=description))
        return result
    except Exception as e:
        print(f"Error in fetch_user_financial_knowledge for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user financial knowledge: {str(e)}")


async def fetch_user_income(user_id: int, supabase: Any) -> List[models.IncomeDetail]:
    """
    Fetches a user's income details.

    Args:
        user_id: The ID of the user.
        supabase: Initialized Supabase client (type hinted as Any).
    """
    try:
        response = supabase.table("income").select("*").eq("user_id", user_id).execute()
        return [models.IncomeDetail(**item) for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error in fetch_user_income for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user income: {str(e)}")


async def fetch_user_debts(user_id: int, supabase: Any) -> List[models.DebtDetail]:
    """
    Fetches a user's debt details.

    Args:
        user_id: The ID of the user.
        supabase: Initialized Supabase client (type hinted as Any).
    """
    try:
        response = supabase.table("debts").select("*").eq("user_id", user_id).execute()
        return [models.DebtDetail(**item) for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error in fetch_user_debts for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user debts: {str(e)}")


async def fetch_user_expenses(user_id: int, supabase: Any) -> List[models.ExpenseDetail]:
    """
    Fetches a user's expense details, ordered by timestamp.

    Args:
        user_id: The ID of the user.
        supabase: Initialized Supabase client (type hinted as Any).
    """
    try:
        response = supabase.table("expenses").select("*").eq("user_id", user_id).order("timestamp", desc=True).execute()
        return [models.ExpenseDetail(**item) for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error in fetch_user_expenses for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user expenses: {str(e)}")

async def get_comprehensive_user_details_service(
    user_id: int,
    supabase: Any, 
    definitions_map: Dict[str, Dict[int, str]]
) -> models.ComprehensiveUserDetails:
    """
    Service function to assemble comprehensive user details.

    Args:
        user_id: The ID of the user.
        supabase: Initialized Supabase client (type hinted as Any).
        definitions_map: Pre-fetched map of financial knowledge definitions.
    """
    if not await check_user_exists(user_id=user_id, supabase=supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")

    user_details_response = models.ComprehensiveUserDetails()

    profile_data = await fetch_user_profile(user_id=user_id, supabase=supabase)
    user_details_response.profile = profile_data

    knowledge_data = await fetch_user_financial_knowledge(
        user_id=user_id, supabase=supabase, definitions_map=definitions_map
    )
    user_details_response.financial_knowledge = knowledge_data

    income_data = await fetch_user_income(user_id=user_id, supabase=supabase)
    user_details_response.income = income_data

    debts_data = await fetch_user_debts(user_id=user_id, supabase=supabase)
    user_details_response.debts = debts_data

    expenses_data = await fetch_user_expenses(user_id=user_id, supabase=supabase)
    user_details_response.expenses = expenses_data
    
    return user_details_response