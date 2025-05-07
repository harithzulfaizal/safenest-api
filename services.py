# ================================================
# FILE: services.py
# ================================================
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status, Depends
from supabase import Client 
from decimal import Decimal
from datetime import datetime, timedelta # Ensure timedelta is imported for JWT later
from passlib.context import CryptContext

# Import models and database utility
import models 
from database import get_supabase_client 
# Import config for JWT settings if/when needed
# import config # Uncomment if JWT settings from config.py are used

# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    # Ensure hashed_password is not None or empty before verification
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

# --- Financial Knowledge Definitions Cache ---
_financial_knowledge_definitions_cache: Optional[Dict[str, Dict[int, str]]] = None

async def get_all_financial_knowledge_definitions_map(
    supabase: Any 
) -> Dict[str, Dict[int, str]]:
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
        _financial_knowledge_definitions_cache = definitions_map 
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
    return await get_all_financial_knowledge_definitions_map(supabase=supabase_client_instance)

def _convert_decimals_to_float(data: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = float(value)
    return data

# --- User Profile Services (omitted for brevity, assume they are here as before) ---
async def create_user_profile(user_profile_in: models.UserProfileCreate, supabase: Any) -> models.UserProfile:
    try:
        insert_data = user_profile_in.model_dump(exclude_unset=True)
        response = supabase.table("users").insert(insert_data).execute()  
        if not response.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user profile or return data.")
        return models.UserProfile(**response.data[0])
    except Exception as e:
        print(f"Error creating user profile: {e}")
        if "duplicate key value violates unique constraint" in str(e) or "already exists" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User profile creation failed. User ID or other unique field might already exist.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def fetch_user_profile(user_id: int, supabase: Any) -> Optional[models.UserProfile]:
    try:
        response = supabase.table("users").select("*").eq("user_id", user_id).maybe_single().execute()
        if not response.data:
            return None
        return models.UserProfile(**response.data)
    except Exception as e:  
        print(f"Error in fetch_user_profile for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while fetching user profile: {str(e)}")

async def update_user_profile(user_id: int, user_profile_update: models.UserProfileUpdate, supabase: Any) -> Optional[models.UserProfile]:
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
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    try:
        response = supabase.table("users").delete().eq("user_id", user_id).execute()
        return bool(response.data)  
    except Exception as e:
        print(f"Error deleting user profile for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Financial Knowledge Definition Services (omitted for brevity) ---
async def create_financial_knowledge_definition(definition_in: models.FinancialKnowledgeDefinitionCreate, supabase: Any) -> models.FinancialKnowledgeDefinition:
    global _financial_knowledge_definitions_cache 
    try:
        response = supabase.table("financial_knowledge_definitions").insert(definition_in.model_dump()).execute()
        if not response.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create financial knowledge definition.")
        _financial_knowledge_definitions_cache = None 
        return models.FinancialKnowledgeDefinition(**response.data[0])
    except Exception as e:
        print(f"Error creating financial knowledge definition: {e}")
        if "duplicate key value violates unique constraint" in str(e) or "already exists" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Financial knowledge definition creation failed. Possible duplicate (category, level).")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def fetch_all_financial_knowledge_definitions(supabase: Any) -> List[models.FinancialKnowledgeDefinition]:
    try:
        response = supabase.table("financial_knowledge_definitions").select("*").order("category").order("level").execute()
        return [models.FinancialKnowledgeDefinition(**item) for item in response.data] if response.data else []
    except Exception as e:
        print(f"Error in fetch_all_financial_knowledge_definitions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def fetch_financial_knowledge_definition_by_id(definition_id: int, supabase: Any) -> Optional[models.FinancialKnowledgeDefinition]:
    try:
        response = supabase.table("financial_knowledge_definitions").select("*").eq("id", definition_id).maybe_single().execute()
        if not response.data:
            return None
        return models.FinancialKnowledgeDefinition(**response.data)
    except Exception as e:
        print(f"Error fetching financial knowledge definition ID {definition_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

async def update_financial_knowledge_definition(definition_id: int, definition_update: models.FinancialKnowledgeDefinitionUpdate, supabase: Any) -> Optional[models.FinancialKnowledgeDefinition]:
    global _financial_knowledge_definitions_cache 
    existing_def = await fetch_financial_knowledge_definition_by_id(definition_id, supabase)
    if not existing_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Financial knowledge definition with ID {definition_id} not found.")
    try:
        update_data = definition_update.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")
        
        response = supabase.table("financial_knowledge_definitions").update(update_data).eq("id", definition_id).execute()
        _financial_knowledge_definitions_cache = None 
        
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
    global _financial_knowledge_definitions_cache 
    existing_def = await fetch_financial_knowledge_definition_by_id(definition_id, supabase)
    if not existing_def:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Financial knowledge definition with ID {definition_id} not found.")
    try:
        response = supabase.table("financial_knowledge_definitions").delete().eq("id", definition_id).execute()
        _financial_knowledge_definitions_cache = None 
        return bool(response.data)
    except Exception as e:
        print(f"Error deleting financial knowledge definition ID {definition_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- User Financial Knowledge Services (omitted for brevity) ---
async def add_user_financial_knowledge(user_id: int, knowledge_in: models.UserFinancialKnowledgeCreate, supabase: Any, definitions_map: Dict[str, Dict[int, str]]) -> models.UserFinancialKnowledgeDetail:
    if not await check_user_exists(user_id, supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    
    if knowledge_in.category not in definitions_map or knowledge_in.level not in definitions_map.get(knowledge_in.category, {}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid category '{knowledge_in.category}' or level '{knowledge_in.level}'. Not found in definitions.")

    try:
        data_to_upsert = {"user_id": user_id, "category": knowledge_in.category, "level": knowledge_in.level}
        response = supabase.table("user_financial_knowledge").upsert(data_to_upsert, on_conflict="user_id,category").execute()  

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
    try:
        response = supabase.table("users").select("user_id", count='exact').eq("user_id", user_id).execute()  
        return response.count is not None and response.count > 0
    except Exception as e:
        print(f"Error in check_user_exists for user_id {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error while checking user existence: {str(e)}")

# --- Income, Debt, Expense Services (omitted for brevity, assume they are here as before) ---
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
            elif data_to_insert["timestamp"] is None and hasattr(expense_in, 'model_fields') and not expense_in.model_fields["timestamp"].is_required(): 
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

# --- Comprehensive User Details Service (omitted for brevity) ---
async def get_comprehensive_user_details_service(
    user_id: int,
    supabase: Any,  
    definitions_map: Dict[str, Dict[int, str]]
) -> models.ComprehensiveUserDetails:
    if not await check_user_exists(user_id=user_id, supabase=supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")

    user_details_response = models.ComprehensiveUserDetails() # Initialize the response model
    # Fetch all parts of the comprehensive details
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

# --- User Login Services ---
async def register_user_login(login_data: models.UserLoginCreate, supabase: Any) -> models.UserLoginResponse:
    """Registers new login credentials for an existing user. Hashes the password before storing it."""
    user_exists = await check_user_exists(user_id=login_data.user_id, supabase=supabase)
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {login_data.user_id} not found. Cannot create login credentials."
        )
    try:
        hashed_pw = hash_password(login_data.password)
        insert_payload = {
            "user_id": login_data.user_id,
            "email": login_data.email,
            "password_hash": hashed_pw
        }
        response = supabase.table("user_logins").insert(insert_payload).execute()
        if not response.data:
            print(f"Warning: Insert for user_logins (user_id: {login_data.user_id}) returned no data. This might be an RLS issue or insert failure.")
            # Attempt to fetch to confirm, though this path usually indicates an issue if RLS isn't the cause.
            check_response = supabase.table("user_logins").select("*").eq("user_id", login_data.user_id).eq("email", login_data.email).maybe_single().execute()
            if check_response.data:
                 return models.UserLoginResponse(**check_response.data) 
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user login credentials or retrieve confirmation after insert."
            )
        created_login_data = response.data[0]
        return models.UserLoginResponse(**created_login_data)
    except Exception as e:
        print(f"Error registering user login for user_id {login_data.user_id}: {e}")
        if "user_logins_email_key" in str(e) or ("duplicate key value violates unique constraint" in str(e) and "user_logins_email_key" in str(e).lower()):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{login_data.email}' already exists."
            )
        if "violates foreign key constraint" in str(e) and "fk_user" in str(e).lower(): # Check for fk_user constraint name
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Invalid user_id: {login_data.user_id}. Ensure the user exists before adding login credentials."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while registering login: {str(e)}"
        )

async def get_login_by_email(email: str, supabase: Any) -> Optional[models.UserLoginResponse]:
    """Fetches a user's login details by email from the 'user_logins' table."""
    try:
        response = supabase.table("user_logins").select("*").eq("email", email).maybe_single().execute()
        if response.data:
            return models.UserLoginResponse(**response.data) # Use UserLoginResponse as it contains password_hash implicitly
        return None
    except Exception as e:
        print(f"Error fetching login by email '{email}': {e}")
        # Avoid raising HTTPException directly from a low-level getter if it's used internally by other services
        # Let the calling service (like authenticate_user) handle the HTTP response logic.
        return None # Or re-raise a custom service-level exception

async def simple_authenticate_user(email: str, password: str, supabase: Any) -> Optional[models.UserLoginResponse]:
    """
    Authenticates a user by email and password (simple version).
    Returns the user login details (excluding password hash) if successful, otherwise None.
    """
    user_login_details = await get_login_by_email(email=email, supabase=supabase)
    
    if not user_login_details:
        print(f"Authentication failed: No user found with email {email}")
        return None # User not found

    # The UserLoginResponse model doesn't explicitly have password_hash, but the data fetched from DB will.
    # We need to access the raw data from the DB response that get_login_by_email used.
    # A better approach is for get_login_by_email to return a model that includes password_hash or the raw dict.
    # For now, let's re-fetch raw data here for clarity, or adjust get_login_by_email.

    # Let's adjust get_login_by_email to return a more suitable structure or the raw dict for auth purposes.
    # For now, we'll assume user_login_details contains the necessary fields or we re-fetch.
    # To make it work with current get_login_by_email, we need to fetch the hash separately or modify it.

    # Simplified: Re-fetch to get the password_hash directly for verification
    try:
        raw_login_data_response = supabase.table("user_logins").select("user_id, email, password_hash").eq("email", email).maybe_single().execute()
        if not raw_login_data_response.data:
            return None # Should have been caught by get_login_by_email already
        
        stored_password_hash = raw_login_data_response.data.get("password_hash")
        
        if not verify_password(password, stored_password_hash):
            print(f"Authentication failed: Password mismatch for email {email}")
            return None # Password does not match
        
        # If password matches, return the user_login_details (which is a UserLoginResponse model instance)
        # We can update last_login here if desired
        try:
            update_response = supabase.table("user_logins").update({"last_login": datetime.utcnow().isoformat()}).eq("email", email).execute()
            if not update_response.data:
                print(f"Warning: Failed to update last_login for {email}")
        except Exception as e_update:
            print(f"Error updating last_login for {email}: {e_update}")

        return user_login_details # Contains user_id, email, etc. from UserLoginResponse model

    except Exception as e:
        print(f"Error during password verification for email {email}: {e}")
        return None


# --- JWT Token Creation (Placeholder for future full authentication) ---
# from jose import JWTError, jwt # Needs python-jose
# Needs config: JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
#     """Creates a JWT access token."""
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
#     return encoded_jwt
