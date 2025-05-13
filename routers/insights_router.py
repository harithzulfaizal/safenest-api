# ================================================
# FILE: routers/insights_router.py
# ================================================
import asyncio
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
import traceback # Added for more detailed error logging

from fastapi import APIRouter, Depends, HTTPException, Path, status, Body
import os
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool # type: ignore
from pydantic_ai.providers.google_gla import GoogleGLAProvider # type: ignore
from pydantic_ai.models.gemini import GeminiModel # type: ignore

import services
import models as app_models # Renamed to avoid conflict if 'models' is used by pydantic_ai
from database import get_supabase_client

from core.prompts import financial_analysis_prompt_template, prioritization_prompt, debt_prompt, savings_prompt
from core.tools import execute_python_code

# Ensure GEMINI_API_KEY is set in your environment variables
# For example, you can load it from a .env file using python-dotenv in your main.py or config.py
# from dotenv import load_dotenv
# load_dotenv()

# Initialize the Gemini Model
# It's good practice to handle potential missing API key error during startup or here
try:
    gemini_api_key = os.environ['GEMINI_API_KEY']
    if not gemini_api_key:
        raise KeyError("GEMINI_API_KEY environment variable not set or empty.")
    model = GeminiModel('gemini-2.0-flash', provider=GoogleGLAProvider(api_key=gemini_api_key))
except KeyError as e:
    print(f"CRITICAL ERROR: {e}. Please set the GEMINI_API_KEY environment variable.")
    # You might want to raise an exception here to prevent the app from starting without the key,
    # or handle it in a way that AI features are gracefully disabled.
    # For this example, we'll let it potentially fail later if model is used without being initialized.
    model = None # Or some placeholder that indicates AI is not available

# from pydantic_ai.models.openai import OpenAIModel
# from pydantic_ai.providers.openai import OpenAIProvider
# model = OpenAIModel('gpt-4o', provider=OpenAIProvider(api_key=os.environ['OPENAI_API_KEY']))

router = APIRouter(
    prefix="/users/{user_id}/insights",
    tags=["User Insights"],
)

async def _fetch_user_financial_data(
    user_id: int,
    supabase: Any,
    definitions_map: Dict[str, Dict[int, str]]
) -> Dict[str, Any]:
    """
    Helper function to fetch all necessary financial data for a user.
    This is used by the financial report generation endpoint.
    """
    try:
        print(f"Fetching data for user_id: {user_id} for financial report.")
        profile = await services.fetch_user_profile(user_id=user_id, supabase=supabase)
        if not profile:
            print(f"User profile not found for user_id: {user_id}.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")

        financial_knowledge_list = await services.fetch_user_financial_knowledge(
            user_id=user_id, supabase=supabase, definitions_map=definitions_map
        )
        income_details_list = await services.fetch_user_income(user_id=user_id, supabase=supabase)
        debt_details_list = await services.fetch_user_debts(user_id=user_id, supabase=supabase)
        expense_details_list = await services.fetch_user_expenses(user_id=user_id, supabase=supabase)
        print(f"Data fetched successfully for user_id: {user_id}.")

        # Prepare data for AI agent input (convert to JSON strings or suitable formats)
        user_profile_json = profile.model_dump_json(indent=2) if profile else 'N/A'
        financial_knowledge_data = [{'category': fk.category, 'level': fk.level, 'description': fk.description} for fk in financial_knowledge_list] if financial_knowledge_list else []
        income_details_data = [item.model_dump() for item in income_details_list] if income_details_list else []
        debt_details_data = [item.model_dump() for item in debt_details_list] if debt_details_list else []
        expense_details_data = [item.model_dump() for item in expense_details_list] if expense_details_list else []

        return {
            "user_profile_str": user_profile_json,
            "financial_knowledge_data": financial_knowledge_data,
            "income_details_data": income_details_data,
            "debt_details_data": debt_details_data,
            "expense_details_data": expense_details_data
        }
    except HTTPException as http_exc:
        raise http_exc # Re-raise if it's already an HTTPException
    except Exception as e:
        print(f"Error fetching data for user {user_id} for report generation: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching user data for the report."
        )

async def _run_ai_agent(
    agent: Any, 
    input_str: str,
    user_id: int,
    agent_name: str
) -> Any:
    """
    Helper function to run a pydantic-ai Agent asynchronously.
    Handles potential errors during agent execution.
    """
    if agent is None: # Simplified check, assumes 'agent' is a pydantic_ai.Agent instance
        print(f"Error: AI Agent '{agent_name}' is not initialized (e.g., API key missing or other setup issue).")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Agent '{agent_name}' is not available due to configuration error."
        )
    
    if not hasattr(agent, "run") or not asyncio.iscoroutinefunction(agent.run):
        print(f"Error: AI Agent '{agent_name}' does not have a compatible async 'run' method.")
        # This might indicate an issue with the pydantic_ai version or agent setup
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, # Or 503
            detail=f"AI Agent '{agent_name}' is not configured correctly for async operation."
        )

    try:
        print(f"Running {agent_name} for user_id: {user_id} asynchronously...")
        # Directly await the agent's asynchronous run method
        agent_response = await agent.run(input_str) 
        print(f"{agent_name} processing completed for user_id: {user_id}.")
        return agent_response
    except Exception as e:
        print(f"Error running {agent_name} for user {user_id}: {str(e)}")
        traceback.print_exc() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the report with {agent_name}."
        )

async def run_debt_pipeline(model, debt_prompt, agent_input, user_id, financial_knowledge_data):
    """
    Runs the debt agent and its summarizer.

    Args:
        model: The language model to be used.
        debt_prompt: The system prompt for the debt agent.
        agent_input: The input string for the debt agent.
        user_id: The ID of the user.
        financial_knowledge_data: Data about the user's financial knowledge.
        execute_python_code_tool: The tool for executing python code.

    Returns:
        The summarized debt insights.
    """
    # Initialize and run the debt agent
    debt_agent = Agent(
        model=model,
        system_prompt=debt_prompt,
        tools=[Tool(execute_python_code, name="execute_python_code", description="Python environment to perform complex calculations and data analysis", takes_ctx=False)],
    )
    debt_agent_response = await _run_ai_agent(
        debt_agent, agent_input, user_id, "Debt Agent"
    )
    # Process the raw results from the debt agent
    # Ensure parts and content exist before accessing
    debt_raw_results = '\n'.join(
        [str(r.parts[0].content) for r in debt_agent_response.all_messages()[1:] if r.parts and len(r.parts) > 0 and hasattr(r.parts[0], 'content') and r.parts[0].content is not None]
    )

    # Define the prompt for the debt summarizer agent
    debt_summarizer_prompt = """Given the context, summarize into a comprehensive insights for the user based on the user's financial knowledge on core concepts and credit.
Your insights must be backed by analysis and data, it is crucial for you to show the calculations and analysis you have done to get to the insights, eg: before and after comparison, etc.
"""
    # Initialize and run the debt summarizer agent
    debt_summarizer_agent = Agent(
        model=model,
        system_prompt=debt_summarizer_prompt,
        result_type=InsightOutput  # Assuming InsightOutput is a defined class
    )
    debt_summarizer_input = f"Debt management plan and recommendations:\n{debt_raw_results}\n\nFinancial knowledge level:{financial_knowledge_data}"
    debt_summarizer_response = await _run_ai_agent(
        debt_summarizer_agent, debt_summarizer_input, user_id, "Debt Summarizer Agent"
    )
    debt_summarized = debt_summarizer_response.data
    return debt_summarized


async def run_savings_pipeline(model, savings_prompt, agent_input, user_id, financial_knowledge_data):
    """
    Runs the savings agent and its summarizer.

    Args:
        model: The language model to be used.
        savings_prompt: The system prompt for the savings agent.
        agent_input: The input string for the savings agent (which includes debt insights).
        user_id: The ID of the user.
        financial_knowledge_data: Data about the user's financial knowledge.
        execute_python_code_tool: The tool for executing python code.

    Returns:
        The summarized savings insights.
    """
    # Initialize and run the savings agent
    savings_agent = Agent(
        model=model,
        system_prompt=savings_prompt,
        tools=[Tool(execute_python_code, name="execute_python_code", description="Python environment to perform complex calculations and data analysis", takes_ctx=False)],
    )
    savings_agent_response = await _run_ai_agent(
        savings_agent, agent_input, user_id, "Savings Agent"
    )
    # Process the raw results from the savings agent
    # Ensure parts and content exist before accessing
    savings_raw_results = '\n'.join(
        [str(r.parts[0].content) for r in savings_agent_response.all_messages()[1:] if r.parts and len(r.parts) > 0 and hasattr(r.parts[0], 'content') and r.parts[0].content is not None]
    )

    # Define the prompt for the savings summarizer agent
    savings_summarizer_prompt = """Given the context, summarize into a comprehensive insights for the user based on the user's financial knowledge on core concepts and budgeting.
Your insights must be backed by analysis and data, it is crucial for you to show the calculations and analysis you have done to get to the insights, eg: before and after comparison, etc.
"""
    # Initialize and run the savings summarizer agent
    savings_summarizer_agent = Agent(
        model=model,
        system_prompt=savings_summarizer_prompt,
        result_type=InsightOutput  # Assuming InsightOutput is a defined class
    )
    savings_summarizer_input = f"Savings plan and recommendations:\n{savings_raw_results}\n\nFinancial knowledge level:{financial_knowledge_data}"
    savings_summarizer_response = await _run_ai_agent(
        savings_summarizer_agent, savings_summarizer_input, user_id, "Savings Summarizer Agent"
    )
    savings_summarized = savings_summarizer_response.data
    return savings_summarized

# --- Pydantic Models for AI Agent Outputs (if used) ---
class PriorityOutput(BaseModel):
    user_id: int
    priority: List[Literal['debt', 'savings']]
    justification: List[str]

class InsightOutput(BaseModel):
    financial_goal: str = Field(
        ...,
        description="Insight title of the content generated by the agent based on the user's goal(s)"
    )
    detailed_insight: str = Field(
        ...,
        description="Detailed insight generated by the agent based on the user's financial knowledge level, at max 6 sentences"
    )
    implications: str = Field(
        ...,
        description="Implications of current behavior backed with concrete figures from what was calculated, at max 5 points with 2 sentences each. Must be normalized to user's financial knowledge level. Must be in points. Must include figures calculated from the agent."
    )
    recommended_actions: str = Field(
        ...,
        description="Recommended actions to take, at max 3 points with 3-4 sentences each. Must be normalized to user's financial knowledge level. Must be in points. Must be implementable and actionable straight away backed with concerete reasons and figures. Must include figures calculated from the agent."
    )

# --- Endpoints ---

@router.post(
    "/financial_report",
    summary="Generate a financial diagnostic report and insights for a user",
    description="Generates a comprehensive financial report using AI, analyzes it for debt and savings insights, prioritizes actions, and stores the results.",
    response_model=Dict[str, Any], 
    status_code=status.HTTP_201_CREATED
)
async def generate_financial_report_and_insights_endpoint(
    user_id: int = Path(..., title="The ID of the user for the report", ge=1),
    supabase: Any = Depends(get_supabase_client),
    definitions_map: Dict[str, Dict[int, str]] = Depends(services.get_definitions_map_with_supabase_dependency)
):
    """
    Endpoint to generate a financial report, derive insights, and save them.
    This endpoint orchestrates multiple AI agents if they are configured.
    """
    if model is None: # Check if the AI model was initialized
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI services are currently unavailable due to configuration issues (e.g., missing API key)."
        )
        
    # --- 1. Fetch User Data ---
    fetched_data = await _fetch_user_financial_data(user_id, supabase, definitions_map)

    user_profile_str = fetched_data["user_profile_str"]
    financial_knowledge_data = fetched_data["financial_knowledge_data"] 
    income_details_data = fetched_data["income_details_data"]
    debt_details_data = fetched_data["debt_details_data"]
    expense_details_data = fetched_data["expense_details_data"]

    # --- 2. Prepare Input for Initial Financial Analysis Agent ---
    financial_knowledge_str = str(financial_knowledge_data) 
    income_str = str(income_details_data)
    debt_str = str(debt_details_data)
    expense_str = str(expense_details_data)

    initial_agent_input_data_str = f"""
    User Profile:
    {user_profile_str}

    Financial Knowledge:
    {financial_knowledge_str}

    Income Details:
    {income_str}

    Debt Details:
    {debt_str}

    Expense Details (Transactions):
    {expense_str}
    """
    print(f"Initial AI input for user {user_id}:\n{initial_agent_input_data_str[:500]}...")

    financial_agent = Agent(
        model=model,
        system_prompt=financial_analysis_prompt_template,
        tools=[Tool(execute_python_code, name="execute_python_code", description="Python environment to perform complex calculations and data analysis", takes_ctx=False)],
    )
    financial_agent_response = await _run_ai_agent(
        financial_agent, initial_agent_input_data_str, user_id, "Financial Analysis Agent"
    )
    
    report_time = datetime.now().isoformat() # Changed from datetime.utcnow() to datetime.now() for local timezone if preferred, or keep utcnow() for consistency.
    financial_report_markdown = financial_agent_response.data

    financial_analysis_for_downstream = {
        "user_id": user_id,
        "report_generated_at": report_time,  
        "financial_report_markdown": financial_report_markdown
    }

    agent_input_for_downstream_agents = f"For user:\n{user_profile_str}\nDebt details:\n{debt_details_data}\nTransactions details:\n{expense_details_data}\nIncome details:\n{income_details_data}\nFinancial report:\n{financial_analysis_for_downstream['financial_report_markdown']}"

    priority_agent = Agent(
        model=model,
        system_prompt=prioritization_prompt,
        result_type=PriorityOutput
    )
    priority_agent_response = await _run_ai_agent(
        priority_agent, agent_input_for_downstream_agents, user_id, "Prioritization Agent"
    )
    
    insights_payload_for_db = {
        # "debt_insights": debt_summarized.model_dump(),
        # "savings_insights": savings_summarized.model_dump(),
        "financial_report_markdown_summary": financial_report_markdown if financial_report_markdown else None,
        "priority_assessment": priority_agent_response.data.model_dump() if priority_agent_response.data else None,
        "report_generated_at": report_time
    }
    
    priorities = priority_agent_response.data.priority

    pipeline_map = {
        "debt": run_debt_pipeline,
        "savings": run_savings_pipeline
    }

    agent_input_for_downstream_agents_depended = ""

    for i, priority in enumerate(priorities):
        summarized_insights = await pipeline_map[priority](
            model,
            debt_prompt if priority == "debt" else savings_prompt,
            agent_input_for_downstream_agents if i == 0 else agent_input_for_downstream_agents_depended,
            user_id,
            financial_knowledge_data
        )

        if i > 0:
            agent_input_for_downstream_agents_depended = agent_input_for_downstream_agents + f"Your insights and calculation must also take into account the following initial insights:\n{summarized_insights}"
        insights_payload_for_db[f"{priority}_insights"] = summarized_insights.model_dump()

    print(insights_payload_for_db)

#     debt_agent = Agent(
#         model=model,
#         system_prompt=debt_prompt,
#         tools=[Tool(execute_python_code, name="execute_python_code", description="Python environment to perform complex calculations and data analysis", takes_ctx=False)],
#     )
#     debt_agent_response = await _run_ai_agent(
#         debt_agent, agent_input_for_downstream_agents, user_id, "Debt Agent"
#     )
#     debt_raw_results = '\n'.join([str(r.parts[0].content) for r in debt_agent_response.all_messages()[1:] if r.parts and r.parts[0].content])


#     debt_summarizer_prompt = """Given the context, summarize into a comprehensive insights for the user based on the user's financial knowledge on core concepts and credit.
# Your insights must be backed by analysis and data, it is crucial for you to show the calculations and analysis you have done to get to the insights, eg: before and after comparison, etc.
# """
#     debt_summarizer_agent = Agent(
#         model=model,
#         system_prompt=debt_summarizer_prompt,
#         result_type=InsightOutput
#     )
#     debt_summarizer_input = f"Debt management plan and recommendations:\n{debt_raw_results}\n\nFinancial knowledge level:{financial_knowledge_data}"
#     debt_summarizer_response = await _run_ai_agent(
#         debt_summarizer_agent, debt_summarizer_input, user_id, "Debt Summarizer Agent"
#     )
#     debt_summarized = debt_summarizer_response.data

#     savings_agent = Agent(
#         model=model,
#         system_prompt=savings_prompt,
#         tools=[Tool(execute_python_code, name="execute_python_code", description="Python environment to perform complex calculations and data analysis", takes_ctx=False)],
#     )

#     agent_input_for_downstream_agents_debt_depended = agent_input_for_downstream_agents + f"\nDebt insights:\n{debt_summarized}"

#     savings_agent_response = await _run_ai_agent(
#         savings_agent, agent_input_for_downstream_agents_debt_depended, user_id, "Savings Agent"
#     )
#     savings_raw_results = '\n'.join([str(r.parts[0].content) for r in savings_agent_response.all_messages()[1:] if r.parts and r.parts[0].content])

#     savings_summarizer_prompt = """Given the context, summarize into a comprehensive insights for the user based on the user's financial knowledge on core concepts and budgeting.
# Your insights must be backed by analysis and data, it is crucial for you to show the calculations and analysis you have done to get to the insights, eg: before and after comparison, etc.
# """
#     savings_summarizer_agent = Agent(
#         model=model,
#         system_prompt=savings_summarizer_prompt,
#         result_type=InsightOutput
#     )
#     savings_summarizer_input = f"Savings plan and recommendations:\n{savings_raw_results}\n\nFinancial knowledge level:{financial_knowledge_data}"
#     savings_summarizer_response = await _run_ai_agent(
#         savings_summarizer_agent, savings_summarizer_input, user_id, "Savings Summarizer Agent"
#     )
#     savings_summarized = savings_summarizer_response.data

    # insights_payload_for_db = {
    #     "debt_insights": debt_summarized.model_dump(),
    #     "savings_insights": savings_summarized.model_dump(),
    #     "financial_report_markdown_summary": financial_report_markdown if financial_report_markdown else None,
    #     "priority_assessment": priority_agent_response.data.model_dump() if priority_agent_response.data else None,
    #     "report_generated_at": report_time
    # }

    db_data_to_upsert = {
        "user_id": user_id,
        "insights": insights_payload_for_db,
        # "updated_at" will be handled by Supabase default (NOW()) on insert/update
    }

    try:
        print(f"Upserting insights for user_id: {user_id} to Supabase.")
        # Using upsert with on_conflict for 'user_id' if you want to update existing insights,
        # or insert if you want to keep a history (requires 'users_insights' to not have user_id as PK alone).
        # Assuming 'users_insights' has 'insight_id' as PK and 'user_id' as a column that might not be unique
        # if you store multiple insights over time. If 'user_id' is unique for latest, then upsert on user_id.
        # For this example, we'll use simple insert, assuming each call generates a new insight record.
        response = supabase.table("users_insights").insert(
            db_data_to_upsert 
        ).execute()

        if hasattr(response, 'error') and response.error:
            print(f"Error from Supabase during insert for user {user_id}: {response.error.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Supabase error during insight insert: {response.error.message}"
            )
        if not response.data:
            print(f"Warning: Supabase insert for user {user_id} returned no data. RLS or other issue?")
        
        print(f"Successfully inserted insights for user_id: {user_id}.")
        
    except HTTPException as http_exc:
        raise http_exc 
    except Exception as e:
        print(f"Error upserting insights for user {user_id} to Supabase: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while saving insights: {str(e)}"
        )

    return {
        "message": "Financial report and insights generated and stored successfully.",
        "user_id": user_id,
        "full_insights_payload": insights_payload_for_db
    }


@router.get(
    "/latest",
    response_model=Optional[app_models.UserInsightResponse], 
    summary="Get the latest financial insight for a user",
    description="Retrieves the most recent insight record for the specified user, based on the 'updated_at' timestamp.",
    status_code=status.HTTP_200_OK
)
async def get_latest_user_insight_endpoint(
    user_id: int = Path(..., title="The ID of the user", ge=1, description="The unique identifier for the user."),
    supabase: Any = Depends(get_supabase_client)
):
    """
    Endpoint to fetch the latest financial insight for a user.
    - **user_id**: The ID of the user whose latest insight is to be retrieved.
    """
    try:
        latest_insight = await services.fetch_latest_user_insight(user_id=user_id, supabase=supabase)
        if not latest_insight:
            # Return 404 directly, service layer might not raise HTTPException for not found, but return None.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No insights found for user ID {user_id}."
            )
        return latest_insight
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in GET /users/{user_id}/insights/latest endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}"
        )
