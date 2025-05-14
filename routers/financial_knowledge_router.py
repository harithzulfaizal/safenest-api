from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Path

import models
import services
from database import get_supabase_client

router = APIRouter(
    tags=["Financial Knowledge Definitions"],
    prefix="/financial_knowledge_definitions"
)

@router.post("",
             response_model=models.FinancialKnowledgeDefinition,
             status_code=status.HTTP_201_CREATED,
             summary="Create a new financial knowledge definition",
             description="Adds a new financial knowledge category, level, and description to the system.")
async def create_financial_knowledge_definition_route(
    definition_in: models.FinancialKnowledgeDefinitionCreate,
    supabase: Any = Depends(get_supabase_client)
):
    """Endpoint to create a new financial knowledge definition."""
    try:
        created_definition = await services.create_financial_knowledge_definition(definition_in=definition_in, supabase=supabase)
        return created_definition
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in create_financial_knowledge_definition_route: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("",
            response_model=List[models.FinancialKnowledgeDefinition],
            summary="Get all financial knowledge definitions",
            description="Retrieves a list of all defined financial knowledge categories, levels, and their descriptions.")
async def list_financial_knowledge_definitions_route(
    supabase: Any = Depends(get_supabase_client)
):
    """Endpoint to retrieve all financial knowledge definitions."""
    try:
        definitions = await services.fetch_all_financial_knowledge_definitions(supabase=supabase)
        return definitions
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in list_financial_knowledge_definitions_route: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/{definition_id}",
            response_model=models.FinancialKnowledgeDefinition,
            summary="Get a specific financial knowledge definition by ID",
            description="Retrieves a single financial knowledge definition by its unique ID.")
async def get_financial_knowledge_definition_route(
    definition_id: int = Path(..., title="The ID of the financial knowledge definition", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    """Endpoint to retrieve a specific financial knowledge definition."""
    try:
        definition = await services.fetch_financial_knowledge_definition_by_id(definition_id=definition_id, supabase=supabase)
        if not definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial knowledge definition with ID {definition_id} not found."
            )
        return definition
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in get_financial_knowledge_definition_route for ID {definition_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.put("/{definition_id}",
            response_model=models.FinancialKnowledgeDefinition,
            summary="Update a financial knowledge definition",
            description="Updates an existing financial knowledge definition by its ID. Only provided fields are updated.")
async def update_financial_knowledge_definition_route(
    definition_id: int = Path(..., title="The ID of the definition to update", ge=1),
    definition_update: models.FinancialKnowledgeDefinitionUpdate = ...,
    supabase: Any = Depends(get_supabase_client)
):
    """Endpoint to update a financial knowledge definition."""
    try:
        updated_definition = await services.update_financial_knowledge_definition(
            definition_id=definition_id,
            definition_update=definition_update,
            supabase=supabase
        )
        if not updated_definition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial knowledge definition with ID {definition_id} not found for update."
            )
        return updated_definition
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error updating financial knowledge definition ID {definition_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.delete("/{definition_id}",
               status_code=status.HTTP_200_OK, # Or 204 No Content if nothing is returned
               summary="Delete a financial knowledge definition",
               description="Deletes a financial knowledge definition by its ID.")
async def delete_financial_knowledge_definition_route(
    definition_id: int = Path(..., title="The ID of the definition to delete", ge=1),
    supabase: Any = Depends(get_supabase_client)
):
    """Endpoint to delete a financial knowledge definition."""
    try:
        success = await services.delete_financial_knowledge_definition(definition_id=definition_id, supabase=supabase)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Financial knowledge definition with ID {definition_id} not found for deletion."
            )
        return {"message": f"Financial knowledge definition with ID {definition_id} deleted successfully."}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error deleting financial knowledge definition ID {definition_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# @router.get("/map",
#             response_model=Dict[str, Dict[int, str]],
#             summary="Get financial knowledge definitions as a map",
#             include_in_schema=False) 
# async def get_financial_knowledge_map(
#     supabase: Any = Depends(get_supabase_client) 
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
