# ================================================
# FILE: routers/insights_router.py
# ================================================
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import traceback

from fastapi import APIRouter, Depends, HTTPException, Path, status, Body
import os
from pydantic import Field
from pydantic_ai import Agent, RunContext, Tool # type: ignore
from pydantic_ai.providers.google_gla import GoogleGLAProvider # type: ignore
from pydantic_ai.models.gemini import GeminiModel, GeminiModelSettings # type: ignore

import services
import models as app_models
from models import InsightsResponse, PriorityOutput, InsightOutput
from database import get_supabase_client

from core.prompts import financial_analysis_prompt_template, prioritization_prompt, debt_prompt, savings_prompt, transaction_summarization_prompt
from core.tools import execute_python_code

try:
    gemini_api_key = os.environ['GEMINI_API_KEY']
    if not gemini_api_key:
        raise KeyError("GEMINI_API_KEY environment variable not set or empty.")
    
    model_settings = GeminiModelSettings(
        gemini_thinking_config={
            "include_thoughts": 0,
            "thinking_budget": 0
        }
    )

    # model_settings = None
    
    model = GeminiModel('gemini-2.5-flash-preview-04-17', provider=GoogleGLAProvider(api_key=gemini_api_key))
except KeyError as e:
    print(f"CRITICAL ERROR: {e}. Please set the GEMINI_API_KEY environment variable.")
    model = None

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
    Helper function to fetch all necessary financial data for a user concurrently.
    This is used by the financial report generation endpoint.
    """
    try:
        print(f"Fetching data concurrently for user_id: {user_id} for financial report.")

        results = await asyncio.gather(
            services.fetch_user_profile(user_id=user_id, supabase=supabase),
            services.fetch_user_financial_knowledge(
                user_id=user_id, supabase=supabase, definitions_map=definitions_map
            ),
            services.fetch_user_income(user_id=user_id, supabase=supabase),
            services.fetch_user_debts(user_id=user_id, supabase=supabase),
            services.fetch_user_expenses(user_id=user_id, supabase=supabase),
            return_exceptions=True
        )

        profile, financial_knowledge_list, income_details_list, debt_details_list, expense_details_list = results

        if isinstance(profile, Exception):
            print(f"Error fetching profile for user {user_id}: {profile}")
            raise profile
        if isinstance(financial_knowledge_list, Exception):
            print(f"Error fetching financial knowledge for user {user_id}: {financial_knowledge_list}")
            raise financial_knowledge_list
        if isinstance(income_details_list, Exception):
            print(f"Error fetching income for user {user_id}: {income_details_list}")
            raise income_details_list
        if isinstance(debt_details_list, Exception):
            print(f"Error fetching debts for user {user_id}: {debt_details_list}")
            raise debt_details_list
        if isinstance(expense_details_list, Exception):
            print(f"Error fetching expenses for user {user_id}: {expense_details_list}")
            raise expense_details_list
            
        if not profile:
            print(f"User profile not found for user_id: {user_id}.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")

        print(f"Data fetched successfully and concurrently for user_id: {user_id}.")

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
        raise http_exc
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
    agent_name: str,
    max_retries: int = 5
) -> Any:
    """
    Helper function to run a pydantic-ai Agent asynchronously with retry logic (no delay).
    Handles potential errors during agent execution.
    """
    if agent is None:
        print(f"Error: AI Agent '{agent_name}' is not initialized (e.g., API key missing or other setup issue).")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Agent '{agent_name}' is not available due to configuration error."
        )
    
    if not hasattr(agent, "run") or not asyncio.iscoroutinefunction(agent.run):
        print(f"Error: AI Agent '{agent_name}' does not have a compatible async 'run' method.")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"AI Agent '{agent_name}' is not configured correctly for async operation."
        )

    
    current_retry = 0
    last_exception = None

    while current_retry < max_retries:
        try:
            print(f"Running {agent_name} for user_id: {user_id} asynchronously... (Attempt {current_retry + 1}/{max_retries})")
            agent_response = await agent.run(input_str, model_settings=model_settings) 
            print(f"{agent_name} processing completed for user_id: {user_id}.")
            return agent_response
        except Exception as e:
            last_exception = e
            print(f"Error running {agent_name} for user {user_id} (Attempt {current_retry + 1}/{max_retries}): {str(e)}")
            traceback.print_exc() 
            current_retry += 1
            if current_retry < max_retries:
                print(f"Retrying immediately...")
                # No delay: await asyncio.sleep(delay)
                # No exponential backoff: delay *= 2
            else:
                print(f"All retries failed for {agent_name} for user {user_id}.")
    
    # If all retries failed, raise an HTTPException with the last encountered error
    if last_exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the report with {agent_name} after {max_retries} attempts: {str(last_exception)}"
        )
    else: # Should not happen if loop was entered, but as a safeguard
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unknown error occurred with {agent_name} after {max_retries} attempts."
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
    debt_agent = Agent(
        model=model,
        system_prompt=debt_prompt,
        tools=[Tool(execute_python_code, name="execute_python_code", description="Python environment to perform complex calculations and data analysis", takes_ctx=False)],
    )
    debt_agent_response = await _run_ai_agent(
        debt_agent, agent_input, user_id, "Debt Agent"
    )
    print(debt_agent_response.all_messages())
    debt_raw_results = '\n'.join(
        [str(r.parts[0].content) for r in debt_agent_response.all_messages()[1:] if r.parts and len(r.parts) > 0 and hasattr(r.parts[0], 'content') and r.parts[0].content is not None]
    )

    debt_summarizer_prompt = """Given the context, summarize into multiple comprehensive insights for the user based on the user's financial knowledge on core concepts and credit.
Your insights must be backed by analysis and data, it is crucial for you to show the calculations and analysis you have done to get to the insights, eg: before and after comparison, etc.
"""
    debt_summarizer_agent = Agent(
        model=model,
        system_prompt=debt_summarizer_prompt,
        result_type=InsightsResponse
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
    savings_agent = Agent(
        model=model,
        system_prompt=savings_prompt,
        tools=[Tool(execute_python_code, name="execute_python_code", description="Python environment to perform complex calculations and data analysis", takes_ctx=False)],
    )
    savings_agent_response = await _run_ai_agent(
        savings_agent, agent_input, user_id, "Savings Agent"
    )
    print(savings_agent_response.all_messages())
    savings_raw_results = '\n'.join(
        [str(r.parts[0].content) for r in savings_agent_response.all_messages()[1:] if r.parts and len(r.parts) > 0 and hasattr(r.parts[0], 'content') and r.parts[0].content is not None]
    )

    savings_summarizer_prompt = """Given the context, summarize into multiple comprehensive insights for the user based on the user's financial knowledge on core concepts and budgeting.
Your insights must be backed by analysis and data, it is crucial for you to show the calculations and analysis you have done to get to the insights, eg: before and after comparison, etc.
"""
    savings_summarizer_agent = Agent(
        model=model,
        system_prompt=savings_summarizer_prompt,
        result_type=InsightsResponse
    )
    savings_summarizer_input = f"Savings plan and recommendations:\n{savings_raw_results}\n\nFinancial knowledge level:{financial_knowledge_data}"
    savings_summarizer_response = await _run_ai_agent(
        savings_summarizer_agent, savings_summarizer_input, user_id, "Savings Summarizer Agent"
    )
    savings_summarized = savings_summarizer_response.data
    return savings_summarized

async def _run_initial_financial_analysis_agent(
    model: Any,
    user_id: int,
    user_profile_str: str,
    financial_knowledge_str: str,
    income_str: str,
    debt_str: str,
    expense_str: str
) -> Dict[str, Any]:
    """Runs the initial financial analysis agent."""
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
    
    print(financial_agent_response.all_messages())
    report_time = datetime.now().isoformat()
    financial_report_markdown = financial_agent_response.data

    return {
        "user_id": user_id,
        "report_generated_at": report_time,  
        "financial_report_markdown": financial_report_markdown
    }

async def _run_transaction_summarizer_agent(
    model: Any,
    user_id: int,
    expense_details_data: List[Dict[str, Any]]
) -> str:
    """Runs the transaction summarization agent."""
    transaction_agent_input_str = f"""
    Expense Details (Transactions):
    {str(expense_details_data)}
    """
    print(f"Transaction summarizer AI input for user {user_id}:\n{transaction_agent_input_str[:500]}...")

    transaction_summarizer_agent = Agent(
        model=model,
        system_prompt=transaction_summarization_prompt,
        tools=[Tool(execute_python_code, name="execute_python_code", description="Python environment to perform complex calculations and data analysis", takes_ctx=False)],
    )
    # Assuming the agent directly returns a string summary
    transaction_summarizer_response = await _run_ai_agent(
        transaction_summarizer_agent, transaction_agent_input_str, user_id, "Transaction Summarizer Agent"
    )
    
    # Ensure the response is a string. If it's a Pydantic model, extract the relevant field.
    # This depends on how your Agent is configured to return data.
    # For now, assuming it's `transaction_summarizer_response.data` if it's a model, or just the response itself.
    if hasattr(transaction_summarizer_response, 'data'):
        summarized_transactions_str = transaction_summarizer_response.data 
    elif isinstance(transaction_summarizer_response, str):
        summarized_transactions_str = transaction_summarizer_response
    else:
        # Fallback or error handling if the response format is unexpected
        print(f"Warning: Unexpected response type from Transaction Summarizer Agent for user {user_id}. Type: {type(transaction_summarizer_response)}")
        summarized_transactions_str = str(transaction_summarizer_response) # Convert to string as a fallback

    print(f"Transaction summary for user {user_id}:\n{summarized_transactions_str[:500]}...")
    return summarized_transactions_str

async def _run_prioritization_agent(
    model: Any,
    user_id: int,
    user_profile_str: str,
    debt_details_data: List[Dict[str, Any]],
    summarized_transactions_str: str, # Changed from expense_details_data
    income_details_data: List[Dict[str, Any]],
    financial_report_markdown: str
) -> PriorityOutput:
    """Runs the prioritization agent."""
    agent_input_for_downstream_agents = f"For user:\n{user_profile_str}\nDebt details:\n{debt_details_data}\nSummarized Transactions details:\n{summarized_transactions_str}\nIncome details:\n{income_details_data}\nFinancial report:\n{financial_report_markdown}"

    priority_agent = Agent(
        model=model,
        system_prompt=prioritization_prompt,
        result_type=PriorityOutput
    )
    priority_agent_response = await _run_ai_agent(
        priority_agent, agent_input_for_downstream_agents, user_id, "Prioritization Agent"
    )
    return priority_agent_response.data

async def _run_prioritized_insight_pipelines(
    model: Any,
    user_id: int,
    priorities: List[str],
    user_profile_str: str,
    debt_details_data: List[Dict[str, Any]],
    summarized_transactions_str: str, # Changed from expense_details_data
    income_details_data: List[Dict[str, Any]],
    financial_report_markdown: str,
    financial_knowledge_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Runs the debt and/or savings pipelines based on priority."""
    insights_from_pipelines = {}
    
    pipeline_map = {
        "debt": run_debt_pipeline,
        "savings": run_savings_pipeline
    }

    base_agent_input = f"For user:\n{user_profile_str}\nDebt details:\n{debt_details_data}\nSummarized Transactions details:\n{summarized_transactions_str}\nIncome details:\n{income_details_data}\nFinancial report:\n{financial_report_markdown}"
    
    current_agent_input = base_agent_input
    
    processed_insights_for_dependency = []

    for i, priority in enumerate(priorities):
        if i > 0 and processed_insights_for_dependency:
            previous_insights_summary = f"\n\nIn your calculation for the insights and recommended actions for {priority}, the figures must take into account the recommendations from the previously derived insights,\n" + "\n".join(
                [f"- {insight_type.capitalize()} Insight: {str(insight_data)}" for insight_type, insight_data in processed_insights_for_dependency]
            )
            current_agent_input = base_agent_input + previous_insights_summary
        
        summarized_insights = await pipeline_map[priority](
            model,
            debt_prompt if priority == "debt" else savings_prompt,
            current_agent_input,
            user_id,
            financial_knowledge_data
        )
        
        print(f"Summarized insights for {priority} for user {user_id}:\n{summarized_insights.model_dump()}")
        insights_from_pipelines[f"{priority}_insights"] = summarized_insights.model_dump()
        processed_insights_for_dependency.append((priority, summarized_insights.insights))

    return insights_from_pipelines

async def _save_insights_to_db(
    supabase: Any,
    user_id: int,
    insights_payload_for_db: Dict[str, Any]
):
    """Saves the generated insights to the database."""
    db_data_to_upsert = {
        "user_id": user_id,
        "insights": insights_payload_for_db,
    }

    try:
        print(f"Upserting insights for user_id: {user_id} to Supabase.")
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
    This endpoint orchestrates multiple AI agents.
    """
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI services are currently unavailable due to configuration issues (e.g., missing API key)."
        )
        
    fetched_data = await _fetch_user_financial_data(user_id, supabase, definitions_map)
    user_profile_str = fetched_data["user_profile_str"]
    financial_knowledge_data = fetched_data["financial_knowledge_data"] 
    income_details_data = fetched_data["income_details_data"]
    debt_details_data = fetched_data["debt_details_data"]
    expense_details_data = fetched_data["expense_details_data"] # Still needed for summarizer

    # Run financial analysis and transaction summarization concurrently
    initial_analysis_task = _run_initial_financial_analysis_agent(
        model=model,
        user_id=user_id,
        user_profile_str=user_profile_str,
        financial_knowledge_str=str(financial_knowledge_data),
        income_str=str(income_details_data),
        debt_str=str(debt_details_data),
        expense_str=str(expense_details_data) # Main report still gets full details
    )
    
    transaction_summary_task = _run_transaction_summarizer_agent(
        model=model,
        user_id=user_id,
        expense_details_data=expense_details_data
    )

    results = await asyncio.gather(initial_analysis_task, transaction_summary_task, return_exceptions=True)

    financial_analysis_result = None
    summarized_transactions_str = None

    if isinstance(results[0], Exception):
        print(f"Error in financial analysis agent: {results[0]}")
        # Decide how to handle this error, e.g., raise HTTPException or proceed without report
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating financial report: {results[0]}")
    else:
        financial_analysis_result = results[0]

    if isinstance(results[1], Exception):
        print(f"Error in transaction summarizer agent: {results[1]}")
        # Decide how to handle this error, e.g., raise HTTPException or proceed with raw data if necessary
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error summarizing transactions: {results[1]}")
    else:
        summarized_transactions_str = results[1]
        
    if not financial_analysis_result or not summarized_transactions_str:
        # This case should ideally be caught by the exception checks above
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get critical AI results.")

    financial_report_markdown = financial_analysis_result["financial_report_markdown"]
    report_time = financial_analysis_result["report_generated_at"]

    priority_assessment_data = await _run_prioritization_agent(
        model=model,
        user_id=user_id,
        user_profile_str=user_profile_str,
        debt_details_data=debt_details_data,
        summarized_transactions_str=summarized_transactions_str, # Pass summarized string
        income_details_data=income_details_data,
        financial_report_markdown=financial_report_markdown
    )
    
    insights_payload_for_db = {
        "financial_report_markdown_summary": financial_report_markdown,
        "transaction_summary_markdown": summarized_transactions_str, # Add summary to DB
        "priority_assessment": priority_assessment_data.model_dump(),
        "report_generated_at": report_time
    }
    
    if priority_assessment_data and priority_assessment_data.priority:
        priorities = priority_assessment_data.priority
        pipeline_insights = await _run_prioritized_insight_pipelines(
            model=model,
            user_id=user_id,
            priorities=priorities,
            user_profile_str=user_profile_str,
            debt_details_data=debt_details_data,
            summarized_transactions_str=summarized_transactions_str, # Pass summarized string
            income_details_data=income_details_data,
            financial_report_markdown=financial_report_markdown,
            financial_knowledge_data=financial_knowledge_data
        )
        insights_payload_for_db.update(pipeline_insights)
    else:
        print(f"No priorities determined for user {user_id}, skipping debt/savings pipelines.")

    await _save_insights_to_db(supabase, user_id, insights_payload_for_db)

    print(f"Final insights payload for user {user_id}: {insights_payload_for_db}")

    return insights_payload_for_db

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
