from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status, Depends # Added Depends
from supabase import Client # Keep for internal reference if needed
from decimal import Decimal # Ensure Decimal is imported
from datetime import datetime # Ensure datetime is imported

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
        return _financial_knowledge_definitions_cache

    try:
        response = supabase.table("financial_knowledge_definitions").select("id, category, level, description").execute()
        
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
        
        _financial_knowledge_definitions_cache = definitions_map # Assign to global cache
        return _financial_knowledge_definitions_cache
    except Exception as e:  
        print(f"Exception in get_all_financial_knowledge_definitions_map: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while fetching financial knowledge definitions: {str(e)}"
        )

async def get_definitions_map_with_supabase_dependency(
    supabase_client_instance: Any = Depends(get_supabase_client)
) -> Dict[str, Dict[int, str]]:
    """
    A dependency function that provides the definitions_map.
    """
    return await get_all_financial_knowledge_definitions_map(supabase=supabase_client_instance)

def _convert_decimals_to_float(data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to convert Decimal instances in a dictionary to float."""
    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = float(value)
    return data

# --- User Profile Services ---
async def create_user_profile(user_profile_in: models.UserProfileCreate, supabase: Any) -> models.UserProfile:
    """Creates a new user profile. Assumes user_id might be auto-generated or managed by DB."""
    try:
        insert_data = user_profile_in.model_dump(exclude_unset=True)
        response = supabase.table("users").insert(insert_data).execute() 
        if not response.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user profile or return data.")
        return models.UserProfile(**response.data[0])
    except Exception as e:
        print(f"Error creating user profile: {e}")
        if "duplicate key value violates unique constraint" in str(e) or "already exists" in str(e):
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User profile creation failed. User ID might already exist.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def fetch_user_profile(user_id: int, supabase: Any) -> Optional[models.UserProfile]:
    """Fetches a user's profile from the database."""
    try:
        response = supabase.table("users").select("*").eq("user_id", user_id).maybe_single().execute()
        if not response.data:
            return None
        return models.UserProfile(**response.data)
    except Exception as e:  
        print(f"Error in fetch_user_profile for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user profile: {str(e)}")

async def update_user_profile(user_id: int, user_profile_update: models.UserProfileUpdate, supabase: Any) -> Optional[models.UserProfile]:
    """Updates an existing user's profile."""
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        update_data = user_profile_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")
        response = supabase.table("users").update(update_data).eq("user_id", user_id).execute()
        if not response.data: 
            print(f"Warning: Update for user_id {user_id} executed but no data returned. RLS issue or data unchanged/not found post-update?.")
            updated_profile = await fetch_user_profile(user_id, supabase)
            if updated_profile: 
                 return updated_profile
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"User profile for {user_id} updated, but failed to retrieve confirmation.")
        return models.UserProfile(**response.data[0])
    except Exception as e:
        print(f"Error updating user profile for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def delete_user_profile(user_id: int, supabase: Any) -> bool:
    """Deletes a user's profile. Returns True if successful."""
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        response = supabase.table("users").delete().eq("user_id", user_id).execute()
        return bool(response.data) 
    except Exception as e:
        print(f"Error deleting user profile for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Financial Knowledge Definition Services ---
async def create_financial_knowledge_definition(definition_in: models.FinancialKnowledgeDefinitionCreate, supabase: Any) -> models.FinancialKnowledgeDefinition:
    """Creates a new financial knowledge definition."""
    global _financial_knowledge_definitions_cache # CORRECTED: Moved global declaration to the top
    try:
        response = supabase.table("financial_knowledge_definitions").insert(definition_in.model_dump()).execute()
        if not response.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create financial knowledge definition.")
        _financial_knowledge_definitions_cache = None # Invalidate cache
        return models.FinancialKnowledgeDefinition(**response.data[0])
    except Exception as e:
        print(f"Error creating financial knowledge definition: {e}")
        if "duplicate key value violates unique constraint" in str(e) or "already exists" in str(e):
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Financial knowledge definition creation failed. Possible duplicate (category, level).")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def fetch_all_financial_knowledge_definitions(supabase: Any) -> List[models.FinancialKnowledgeDefinition]:
    """Fetches all financial knowledge definitions from the database."""
    try:
        response = supabase.table("financial_knowledge_definitions").select("*").order("category").order("level").execute()
        return [models.FinancialKnowledgeDefinition(**item) for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error in fetch_all_financial_knowledge_definitions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def fetch_financial_knowledge_definition_by_id(definition_id: int, supabase: Any) -> Optional[models.FinancialKnowledgeDefinition]:
    """Fetches a single financial knowledge definition by its ID."""
    try:
        response = supabase.table("financial_knowledge_definitions").select("*").eq("id", definition_id).maybe_single().execute()
        if not response.data:
            return None
        return models.FinancialKnowledgeDefinition(**response.data)
    except Exception as e:
        print(f"Error fetching financial knowledge definition ID {definition_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def update_financial_knowledge_definition(definition_id: int, definition_update: models.FinancialKnowledgeDefinitionUpdate, supabase: Any) -> Optional[models.FinancialKnowledgeDefinition]:
    """Updates an existing financial knowledge definition."""
    global _financial_knowledge_definitions_cache # CORRECTED: Moved global declaration to the top
    existing_def = await fetch_financial_knowledge_definition_by_id(definition_id, supabase)
    if not existing_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Financial knowledge definition with ID {definition_id} not found.")
    try:
        update_data = definition_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")
        
        response = supabase.table("financial_knowledge_definitions").update(update_data).eq("id", definition_id).execute()
        _financial_knowledge_definitions_cache = None # Invalidate cache
        
        if not response.data:
            updated_def = await fetch_financial_knowledge_definition_by_id(definition_id, supabase) 
            if updated_def: 
                return updated_def
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Financial knowledge definition {definition_id} updated, but failed to retrieve confirmation.")
        return models.FinancialKnowledgeDefinition(**response.data[0])
    except Exception as e:
        print(f"Error updating financial knowledge definition ID {definition_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def delete_financial_knowledge_definition(definition_id: int, supabase: Any) -> bool:
    """Deletes a financial knowledge definition. Returns True if successful."""
    global _financial_knowledge_definitions_cache # CORRECTED: Moved global declaration to the top
    existing_def = await fetch_financial_knowledge_definition_by_id(definition_id, supabase)
    if not existing_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Financial knowledge definition with ID {definition_id} not found.")
    try:
        response = supabase.table("financial_knowledge_definitions").delete().eq("id", definition_id).execute()
        _financial_knowledge_definitions_cache = None # Invalidate cache
        return bool(response.data)
    except Exception as e:
        print(f"Error deleting financial knowledge definition ID {definition_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- User Financial Knowledge Services ---
async def add_user_financial_knowledge(user_id: int, knowledge_in: models.UserFinancialKnowledgeCreate, supabase: Any, definitions_map: Dict[str, Dict[int, str]]) -> models.UserFinancialKnowledgeDetail:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    
    if knowledge_in.category not in definitions_map or knowledge_in.level not in definitions_map.get(knowledge_in.category, {}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid category '{knowledge_in.category}' or level '{knowledge_in.level}'. Not found in definitions.")

    try:
        data_to_upsert = {"user_id": user_id, "category": knowledge_in.category, "level": knowledge_in.level}
        response = supabase.table("user_financial_knowledge").upsert(data_to_upsert).execute() 

        if not response.data: 
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add/update user financial knowledge.")
        
        created_item = response.data[0]
        description = definitions_map.get(created_item["category"], {}).get(created_item["level"])
        return models.UserFinancialKnowledgeDetail(
            user_id=user_id, 
            category=created_item["category"],
            level=created_item["level"],
            description=description
        )
    except Exception as e:
        print(f"Error adding/updating user financial knowledge for user {user_id}, category {knowledge_in.category}: {e}")
        if "duplicate key" in str(e) or "constraint" in str(e): 
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Conflict: User financial knowledge for category '{knowledge_in.category}' may already exist or another constraint violated.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def fetch_user_financial_knowledge(user_id: int, supabase: Any, definitions_map: Dict[str, Dict[int, str]]) -> List[models.UserFinancialKnowledgeDetail]:
    try:
        knowledge_response = supabase.table("user_financial_knowledge").select("user_id, category, level").eq("user_id", user_id).execute()
        
        result: List[models.UserFinancialKnowledgeDetail] = []
        if knowledge_response.data:
            for item in knowledge_response.data:
                category = item.get("category")
                level = item.get("level")
                item_user_id = item.get("user_id")
                if category is None or level is None:
                    print(f"Warning: Skipping financial knowledge item for user {user_id} due to missing category/level: {item}")
                    continue
                description = definitions_map.get(category, {}).get(level)
                result.append(models.UserFinancialKnowledgeDetail(user_id=item_user_id, category=category, level=level, description=description))
        return result
    except Exception as e:
        print(f"Error in fetch_user_financial_knowledge for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user financial knowledge: {str(e)}")

async def update_user_financial_knowledge_level(user_id: int, category: str, knowledge_update: models.UserFinancialKnowledgeUpdate, supabase: Any, definitions_map: Dict[str, Dict[int, str]]) -> Optional[models.UserFinancialKnowledgeDetail]:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")

    if category not in definitions_map or knowledge_update.level not in definitions_map.get(category, {}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid category '{category}' or level '{knowledge_update.level}'. Not found in definitions.")

    try:
        response = supabase.table("user_financial_knowledge").update({"level": knowledge_update.level}).eq("user_id", user_id).eq("category", category).execute()
        if not response.data:
            q_resp = supabase.table("user_financial_knowledge").select("*").eq("user_id", user_id).eq("category", category).maybe_single().execute() 
            if not q_resp.data:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Financial knowledge for category '{category}' not found for user ID {user_id}.")
            updated_item = q_resp.data
        else:
            updated_item = response.data[0]

        description = definitions_map.get(updated_item["category"], {}).get(updated_item["level"])
        return models.UserFinancialKnowledgeDetail(
            user_id=user_id, 
            category=updated_item["category"],
            level=updated_item["level"],
            description=description
        )
    except Exception as e:
        print(f"Error updating user financial knowledge for user {user_id}, category {category}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def remove_user_financial_knowledge(user_id: int, category: str, supabase: Any) -> bool:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        check_response = supabase.table("user_financial_knowledge").select("category", count='exact').eq("user_id", user_id).eq("category", category).execute()
        if not (check_response.count and check_response.count > 0):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Financial knowledge category '{category}' not found for user ID {user_id}.")

        response = supabase.table("user_financial_knowledge").delete().eq("user_id", user_id).eq("category", category).execute()
        return bool(response.data) 
    except HTTPException as http_exc: 
        raise http_exc
    except Exception as e:
        print(f"Error removing user financial knowledge for user {user_id}, category {category}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# --- Generic Helper ---
async def check_user_exists(user_id: int, supabase: Any) -> bool:
    """Checks if a user exists in the database."""
    try:
        response = supabase.table("users").select("user_id", count='exact').eq("user_id", user_id).execute() 
        return response.count is not None and response.count > 0
    except Exception as e:
        print(f"Error in check_user_exists for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error while checking user existence: {str(e)}")

# --- Income Services ---
async def create_income_detail(user_id: int, income_in: models.IncomeDetailCreate, supabase: Any) -> models.IncomeDetail:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        data_to_insert = income_in.model_dump(exclude_unset=True)
        data_to_insert["user_id"] = user_id
        data_to_insert = _convert_decimals_to_float(data_to_insert) 
        response = supabase.table("income").insert(data_to_insert).execute() 
        if not response.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create income detail.")
        return models.IncomeDetail(**response.data[0])
    except Exception as e:
        print(f"Error creating income detail for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def fetch_user_income(user_id: int, supabase: Any) -> List[models.IncomeDetail]:
    if not await check_user_exists(user_id, supabase): 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        response = supabase.table("income").select("*").eq("user_id", user_id).execute()
        return [models.IncomeDetail(**item) for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error in fetch_user_income for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user income: {str(e)}")

async def fetch_income_detail_by_id(user_id: int, income_id: int, supabase: Any) -> Optional[models.IncomeDetail]:
    if not await check_user_exists(user_id, supabase): 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        response = supabase.table("income").select("*").eq("user_id", user_id).eq("income_id", income_id).maybe_single().execute()
        return models.IncomeDetail(**response.data) if response.data else None
    except Exception as e:
        print(f"Error fetching income detail ID {income_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def update_income_detail(user_id: int, income_id: int, income_update: models.IncomeDetailUpdate, supabase: Any) -> Optional[models.IncomeDetail]:
    existing_income = await fetch_income_detail_by_id(user_id, income_id, supabase) 
    if not existing_income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Income record with ID {income_id} not found for user {user_id}.")
    try:
        update_data = income_update.model_dump(exclude_unset=True)
        if not update_data:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")
        update_data = _convert_decimals_to_float(update_data) 
        response = supabase.table("income").update(update_data).eq("user_id", user_id).eq("income_id", income_id).execute()
        if not response.data:
            updated_rec = await fetch_income_detail_by_id(user_id, income_id, supabase) 
            if updated_rec: return updated_rec
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Income record {income_id} for user {user_id} updated, but failed to retrieve confirmation.")
        return models.IncomeDetail(**response.data[0])
    except Exception as e:
        print(f"Error updating income detail ID {income_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def delete_income_detail(user_id: int, income_id: int, supabase: Any) -> bool:
    existing_income = await fetch_income_detail_by_id(user_id, income_id, supabase)
    if not existing_income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Income record with ID {income_id} not found for user {user_id} to delete.")
    try:
        response = supabase.table("income").delete().eq("user_id", user_id).eq("income_id", income_id).execute()
        return bool(response.data)
    except Exception as e:
        print(f"Error deleting income detail ID {income_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Debt Services ---
async def create_debt_detail(user_id: int, debt_in: models.DebtDetailCreate, supabase: Any) -> models.DebtDetail:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        data_to_insert = debt_in.model_dump(exclude_unset=True)
        data_to_insert["user_id"] = user_id
        data_to_insert = _convert_decimals_to_float(data_to_insert) 
        response = supabase.table("debts").insert(data_to_insert).execute() 
        if not response.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create debt detail.")
        return models.DebtDetail(**response.data[0])
    except Exception as e:
        print(f"Error creating debt detail for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def fetch_user_debts(user_id: int, supabase: Any) -> List[models.DebtDetail]:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        response = supabase.table("debts").select("*").eq("user_id", user_id).execute()
        return [models.DebtDetail(**item) for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error in fetch_user_debts for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user debts: {str(e)}")

async def fetch_debt_detail_by_id(user_id: int, debt_id: int, supabase: Any) -> Optional[models.DebtDetail]:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        response = supabase.table("debts").select("*").eq("user_id", user_id).eq("debt_id", debt_id).maybe_single().execute()
        return models.DebtDetail(**response.data) if response.data else None
    except Exception as e:
        print(f"Error fetching debt detail ID {debt_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def update_debt_detail(user_id: int, debt_id: int, debt_update: models.DebtDetailUpdate, supabase: Any) -> Optional[models.DebtDetail]:
    existing_debt = await fetch_debt_detail_by_id(user_id, debt_id, supabase)
    if not existing_debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Debt record with ID {debt_id} not found for user {user_id}.")
    try:
        update_data = debt_update.model_dump(exclude_unset=True)
        if not update_data:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")
        update_data = _convert_decimals_to_float(update_data) 
        response = supabase.table("debts").update(update_data).eq("user_id", user_id).eq("debt_id", debt_id).execute()
        if not response.data:
            updated_rec = await fetch_debt_detail_by_id(user_id, debt_id, supabase) 
            if updated_rec: return updated_rec
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Debt record {debt_id} for user {user_id} updated, but failed to retrieve confirmation.")
        return models.DebtDetail(**response.data[0])
    except Exception as e:
        print(f"Error updating debt detail ID {debt_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def delete_debt_detail(user_id: int, debt_id: int, supabase: Any) -> bool:
    existing_debt = await fetch_debt_detail_by_id(user_id, debt_id, supabase)
    if not existing_debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Debt record with ID {debt_id} not found for user {user_id} to delete.")
    try:
        response = supabase.table("debts").delete().eq("user_id", user_id).eq("debt_id", debt_id).execute()
        return bool(response.data)
    except Exception as e:
        print(f"Error deleting debt detail ID {debt_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Expense Services ---
async def create_expense_detail(user_id: int, expense_in: models.ExpenseDetailCreate, supabase: Any) -> models.ExpenseDetail:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        data_to_insert = expense_in.model_dump(exclude_unset=True)
        data_to_insert["user_id"] = user_id
        
        data_to_insert = _convert_decimals_to_float(data_to_insert)
        
        if "timestamp" in data_to_insert:
            if isinstance(data_to_insert["timestamp"], datetime):
                 data_to_insert["timestamp"] = data_to_insert["timestamp"].isoformat()
            elif data_to_insert["timestamp"] is None and not expense_in.model_fields["timestamp"].is_required():
                 pass 

        response = supabase.table("expenses").insert(data_to_insert).execute() 
        if not response.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create expense detail.")
        return models.ExpenseDetail(**response.data[0])
    except Exception as e:
        print(f"Error creating expense detail for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def fetch_user_expenses(user_id: int, supabase: Any) -> List[models.ExpenseDetail]:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        response = supabase.table("expenses").select("*").eq("user_id", user_id).order("timestamp", desc=True).execute()
        return [models.ExpenseDetail(**item) for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error in fetch_user_expenses for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user expenses: {str(e)}")

async def fetch_expense_detail_by_id(user_id: int, expense_id: int, supabase: Any) -> Optional[models.ExpenseDetail]:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        response = supabase.table("expenses").select("*").eq("user_id", user_id).eq("expense_id", expense_id).maybe_single().execute()
        return models.ExpenseDetail(**response.data) if response.data else None
    except Exception as e:
        print(f"Error fetching expense detail ID {expense_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def update_expense_detail(user_id: int, expense_id: int, expense_update: models.ExpenseDetailUpdate, supabase: Any) -> Optional[models.ExpenseDetail]:
    existing_expense = await fetch_expense_detail_by_id(user_id, expense_id, supabase)
    if not existing_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense record with ID {expense_id} not found for user {user_id}.")
    try:
        update_data = expense_update.model_dump(exclude_unset=True)
        if not update_data:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")
        
        update_data = _convert_decimals_to_float(update_data)
        
        if "timestamp" in update_data and isinstance(update_data["timestamp"], datetime):
            update_data["timestamp"] = update_data["timestamp"].isoformat()
        
        response = supabase.table("expenses").update(update_data).eq("user_id", user_id).eq("expense_id", expense_id).execute()
        if not response.data:
            updated_rec = await fetch_expense_detail_by_id(user_id, expense_id, supabase) 
            if updated_rec: return updated_rec
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Expense record {expense_id} for user {user_id} updated, but failed to retrieve confirmation.")
        return models.ExpenseDetail(**response.data[0])
    except Exception as e:
        print(f"Error updating expense detail ID {expense_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def delete_expense_detail(user_id: int, expense_id: int, supabase: Any) -> bool:
    existing_expense = await fetch_expense_detail_by_id(user_id, expense_id, supabase)
    if not existing_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense record with ID {expense_id} not found for user {user_id} to delete.")
    try:
        response = supabase.table("expenses").delete().eq("user_id", user_id).eq("expense_id", expense_id).execute()
        return bool(response.data)
    except Exception as e:
        print(f"Error deleting expense detail ID {expense_id} for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Comprehensive User Details Service ---
async def get_comprehensive_user_details_service(
    user_id: int,
    supabase: Any,  
    definitions_map: Dict[str, Dict[int, str]]
) -> models.ComprehensiveUserDetails:
    if not await check_user_exists(user_id=user_id, supabase=supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")

    user_details_response = models.ComprehensiveUserDetails()
    profile_data = await fetch_user_profile(user_id=user_id, supabase=supabase)
    user_details_response.profile = profile_data
    knowledge_data = await fetch_user_financial_knowledge(user_id=user_id, supabase=supabase, definitions_map=definitions_map)
    user_details_response.financial_knowledge = knowledge_data
    income_data = await fetch_user_income(user_id=user_id, supabase=supabase)
    user_details_response.income = income_data
    debts_data = await fetch_user_debts(user_id=user_id, supabase=supabase)
    user_details_response.debts = debts_data
    expenses_data = await fetch_user_expenses(user_id=user_id, supabase=supabase)
    user_details_response.expenses = expenses_data
    
    return user_details_response
