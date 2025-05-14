from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, status, Response, Body

import models
import services
from database import get_supabase_client

router = APIRouter(
    prefix="/users",
    tags=["User Details"]
)

@router.post("",
             response_model=models.UserProfile,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new user profile",
             description="Creates a new user profile. The `user_id` in the response is assigned by the system or database.")
async def create_user_profile_route(
    user_profile_in: models.UserProfileCreate,
    supabase: Any = Depends(get_supabase_client)
):
    """Endpoint to create a user profile. Assumes user_id is auto-generated or handled by DB if not in UserProfileCreate."""
    try:
        created_profile = await services.create_user_profile(user_profile_in=user_profile_in, supabase=supabase)
        return created_profile
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in create_user_profile_route: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{user_id}/profile",
            response_model=models.UserProfile,
            summary="Get a user's profile",
            description="Retrieves the profile information for a specific user by their ID.")
async def get_user_profile_route(
    user_id: int = Path(..., title="The ID of the user", ge=1, example=1),
    supabase: Any = Depends(get_supabase_client)
):
    profile = await services.fetch_user_profile(user_id=user_id, supabase=supabase)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile with ID {user_id} not found."
        )
    return profile

@router.put("/{user_id}/profile",
            response_model=models.UserProfile,
            summary="Update a user's profile",
            description="Updates an existing user's profile information. Only provided fields are changed.")
async def update_user_profile_route(
    user_id: int = Path(..., title="The ID of the user to update", ge=1),
    user_profile_update: models.UserProfileUpdate = Body(...),
    supabase: Any = Depends(get_supabase_client)
):
    updated_profile = await services.update_user_profile(user_id=user_id, user_profile_update=user_profile_update, supabase=supabase)
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile with ID {user_id} not found for update."
        )
    return updated_profile

@router.delete("/{user_id}/profile",
               status_code=status.HTTP_200_OK,
               summary="Delete a user's profile",
               description="Deletes a user's profile and potentially associated data (depending on DB constraints).")
async def delete_user_profile_route(
    user_id: int = Path(..., title="The ID of the user to delete", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    success = await services.delete_user_profile(user_id=user_id, supabase=supabase)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile with ID {user_id} not found for deletion."
        )
    return {"message": f"User profile with ID {user_id} deleted successfully."}

@router.post("/{user_id}/financial_knowledge",
             response_model=models.UserFinancialKnowledgeDetail,
             status_code=status.HTTP_201_CREATED,
             summary="Add or update financial knowledge for a user",
             description="Adds a new financial knowledge entry (category and level) for a user or updates the level if the category already exists for that user. (user_id, category) is treated as a key.")
async def add_or_update_user_financial_knowledge_route(
    user_id: int = Path(..., title="The ID of the user", ge=1),
    knowledge_in: models.UserFinancialKnowledgeCreate = Body(...),
    supabase: Any = Depends(get_supabase_client),
    definitions_map: Dict[str, Dict[int, str]] = Depends(services.get_definitions_map_with_supabase_dependency)
):
    created_or_updated_knowledge = await services.add_user_financial_knowledge(
        user_id=user_id,
        knowledge_in=knowledge_in,
        supabase=supabase,
        definitions_map=definitions_map
    )
    return created_or_updated_knowledge

@router.get("/{user_id}/financial_knowledge",
            response_model=List[models.UserFinancialKnowledgeDetail],
            summary="Get a user's financial knowledge with descriptions")
async def get_user_financial_knowledge_route(
    user_id: int = Path(..., title="The ID of the user", ge=1, example=1),
    supabase: Any = Depends(get_supabase_client),
    definitions_map: Dict[str, Dict[int, str]] = Depends(services.get_definitions_map_with_supabase_dependency)
):
    if not await services.check_user_exists(user_id=user_id, supabase=supabase):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    knowledge_details = await services.fetch_user_financial_knowledge(
        user_id=user_id, supabase=supabase, definitions_map=definitions_map
    )
    return knowledge_details

@router.put("/{user_id}/financial_knowledge/{category}",
            response_model=models.UserFinancialKnowledgeDetail,
            summary="Update a user's financial knowledge level for a category",
            description="Updates the proficiency level for a specific financial knowledge category for a given user.")
async def update_user_financial_knowledge_level_route(
    user_id: int = Path(..., title="The ID of the user", ge=1),
    category: str = Path(..., title="The financial knowledge category to update"),
    knowledge_update: models.UserFinancialKnowledgeUpdate = Body(...),
    supabase: Any = Depends(get_supabase_client),
    definitions_map: Dict[str, Dict[int, str]] = Depends(services.get_definitions_map_with_supabase_dependency)
):
    updated_knowledge = await services.update_user_financial_knowledge_level(
        user_id=user_id,
        category=category,
        knowledge_update=knowledge_update,
        supabase=supabase,
        definitions_map=definitions_map
    )
    if not updated_knowledge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Financial knowledge for category '{category}' not found for user ID {user_id}.")
    return updated_knowledge

@router.delete("/{user_id}/financial_knowledge/{category}",
               status_code=status.HTTP_200_OK,
               summary="Remove a financial knowledge category from a user",
               description="Deletes a specific financial knowledge category entry for a user.")
async def remove_user_financial_knowledge_route(
    user_id: int = Path(..., title="The ID of the user", ge=1),
    category: str = Path(..., title="The financial knowledge category to remove"),
    supabase: Any = Depends(get_supabase_client)
):
    success = await services.remove_user_financial_knowledge(user_id=user_id, category=category, supabase=supabase)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Financial knowledge for category '{category}' not found for user ID {user_id}, or user not found."
        )
    return {"message": f"Financial knowledge category '{category}' removed for user ID {user_id}."}


@router.post("/{user_id}/income",
             response_model=models.IncomeDetail,
             status_code=status.HTTP_201_CREATED,
             summary="Add an income source for a user")
async def create_income_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    income_in: models.IncomeDetailCreate = Body(...),
    supabase: Any = Depends(get_supabase_client)
):
    return await services.create_income_detail(user_id=user_id, income_in=income_in, supabase=supabase)

@router.get("/{user_id}/income",
            response_model=List[models.IncomeDetail],
            summary="Get all income sources for a user")
async def get_user_income_list_route(
    user_id: int = Path(..., title="User ID", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    if not await services.check_user_exists(user_id=user_id, supabase=supabase):
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    return await services.fetch_user_income(user_id=user_id, supabase=supabase)

@router.get("/{user_id}/income/{income_id}",
            response_model=models.IncomeDetail,
            summary="Get a specific income source for a user")
async def get_income_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    income_id: int = Path(..., title="Income Record ID", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    income = await services.fetch_income_detail_by_id(user_id=user_id, income_id=income_id, supabase=supabase)
    if not income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Income record with ID {income_id} not found for user {user_id}.")
    return income

@router.put("/{user_id}/income/{income_id}",
            response_model=models.IncomeDetail,
            summary="Update an income source for a user")
async def update_income_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    income_id: int = Path(..., title="Income Record ID", ge=1),
    income_update: models.IncomeDetailUpdate = Body(...),
    supabase: Any = Depends(get_supabase_client)
):
    updated_income = await services.update_income_detail(user_id=user_id, income_id=income_id, income_update=income_update, supabase=supabase)
    if not updated_income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Income record with ID {income_id} not found for user {user_id} to update.")
    return updated_income

@router.delete("/{user_id}/income/{income_id}",
               status_code=status.HTTP_200_OK,
               summary="Delete an income source for a user")
async def delete_income_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    income_id: int = Path(..., title="Income Record ID", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    success = await services.delete_income_detail(user_id=user_id, income_id=income_id, supabase=supabase)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Income record with ID {income_id} not found for user {user_id} to delete.")
    return {"message": f"Income record ID {income_id} for user {user_id} deleted."}


@router.post("/{user_id}/debts",
             response_model=models.DebtDetail,
             status_code=status.HTTP_201_CREATED,
             summary="Add a debt obligation for a user")
async def create_debt_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    debt_in: models.DebtDetailCreate = Body(...),
    supabase: Any = Depends(get_supabase_client)
):
    return await services.create_debt_detail(user_id=user_id, debt_in=debt_in, supabase=supabase)

@router.get("/{user_id}/debts",
            response_model=List[models.DebtDetail],
            summary="Get all debt obligations for a user")
async def get_user_debts_list_route(
    user_id: int = Path(..., title="User ID", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    if not await services.check_user_exists(user_id=user_id, supabase=supabase):
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    return await services.fetch_user_debts(user_id=user_id, supabase=supabase)

@router.get("/{user_id}/debts/{debt_id}",
            response_model=models.DebtDetail,
            summary="Get a specific debt obligation for a user")
async def get_debt_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    debt_id: int = Path(..., title="Debt Record ID", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    debt = await services.fetch_debt_detail_by_id(user_id=user_id, debt_id=debt_id, supabase=supabase)
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Debt record with ID {debt_id} not found for user {user_id}.")
    return debt

@router.put("/{user_id}/debts/{debt_id}",
            response_model=models.DebtDetail,
            summary="Update a debt obligation for a user")
async def update_debt_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    debt_id: int = Path(..., title="Debt Record ID", ge=1),
    debt_update: models.DebtDetailUpdate = Body(...),
    supabase: Any = Depends(get_supabase_client)
):
    updated_debt = await services.update_debt_detail(user_id=user_id, debt_id=debt_id, debt_update=debt_update, supabase=supabase)
    if not updated_debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Debt record with ID {debt_id} not found for user {user_id} to update.")
    return updated_debt

@router.delete("/{user_id}/debts/{debt_id}",
               status_code=status.HTTP_200_OK,
               summary="Delete a debt obligation for a user")
async def delete_debt_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    debt_id: int = Path(..., title="Debt Record ID", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    success = await services.delete_debt_detail(user_id=user_id, debt_id=debt_id, supabase=supabase)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Debt record with ID {debt_id} not found for user {user_id} to delete.")
    return {"message": f"Debt record ID {debt_id} for user {user_id} deleted."}


@router.post("/{user_id}/expenses",
             response_model=models.ExpenseDetail,
             status_code=status.HTTP_201_CREATED,
             summary="Add an expense record for a user")
async def create_expense_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    expense_in: models.ExpenseDetailCreate = Body(...),
    supabase: Any = Depends(get_supabase_client)
):
    return await services.create_expense_detail(user_id=user_id, expense_in=expense_in, supabase=supabase)

@router.get("/{user_id}/expenses",
            response_model=List[models.ExpenseDetail],
            summary="Get all expense records for a user")
async def get_user_expenses_list_route(
    user_id: int = Path(..., title="User ID", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    if not await services.check_user_exists(user_id=user_id, supabase=supabase):
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
    return await services.fetch_user_expenses(user_id=user_id, supabase=supabase)

@router.get("/{user_id}/expenses/{expense_id}",
            response_model=models.ExpenseDetail,
            summary="Get a specific expense record for a user")
async def get_expense_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    expense_id: int = Path(..., title="Expense Record ID", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    expense = await services.fetch_expense_detail_by_id(user_id=user_id, expense_id=expense_id, supabase=supabase)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense record with ID {expense_id} not found for user {user_id}.")
    return expense

@router.put("/{user_id}/expenses/{expense_id}",
            response_model=models.ExpenseDetail,
            summary="Update an expense record for a user")
async def update_expense_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    expense_id: int = Path(..., title="Expense Record ID", ge=1),
    expense_update: models.ExpenseDetailUpdate = Body(...),
    supabase: Any = Depends(get_supabase_client)
):
    updated_expense = await services.update_expense_detail(user_id=user_id, expense_id=expense_id, expense_update=expense_update, supabase=supabase)
    if not updated_expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense record with ID {expense_id} not found for user {user_id} to update.")
    return updated_expense

@router.delete("/{user_id}/expenses/{expense_id}",
               status_code=status.HTTP_200_OK,
               summary="Delete an expense record for a user")
async def delete_expense_detail_route(
    user_id: int = Path(..., title="User ID", ge=1),
    expense_id: int = Path(..., title="Expense Record ID", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    success = await services.delete_expense_detail(user_id=user_id, expense_id=expense_id, supabase=supabase)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense record with ID {expense_id} not found for user {user_id} to delete.")
    return {"message": f"Expense record ID {expense_id} for user {user_id} deleted."}


@router.get("/{user_id}/comprehensive_details",
            response_model=models.ComprehensiveUserDetails,
            tags=["User Details - Comprehensive"], 
            summary="Get all financial information for a specific user")
async def get_comprehensive_user_details_route(
    user_id: int = Path(..., title="The ID of the user to retrieve", ge=1, example=1),
    supabase: Any = Depends(get_supabase_client),
    definitions_map: Dict[str, Dict[int, str]] = Depends(services.get_definitions_map_with_supabase_dependency)
):
    comprehensive_details = await services.get_comprehensive_user_details_service(
        user_id=user_id,
        supabase=supabase,
        definitions_map=definitions_map
    )
    return comprehensive_details
