# models.py
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field

# --- Pydantic Models for Data Structuring ---

class UserProfileBase(BaseModel):
    """Base model for user profile attributes, used for creation or partial updates if needed."""
    age: Optional[int] = Field(None, description="User's age")
    num_children: Optional[int] = Field(None, description="Number of children the user has")
    marital_status: Optional[str] = Field(None, description="User's marital status (e.g., Single, Married)")
    retirement_status: Optional[str] = Field(None, description="User's retirement status (e.g., Employed, Retired)")
    goals: Optional[Dict[str, Any]] = Field(None, description="User's financial or life goals, stored as a JSON object")

class UserProfile(UserProfileBase):
    """
    Represents a user's profile information.
    Inherits common fields from UserProfileBase and adds user_id.
    """
    user_id: int = Field(..., description="Unique identifier for the user", example=1)

    class Config:
        orm_mode = True # Deprecated in Pydantic V2, use model_config = {"from_attributes": True}
        # For Pydantic V2:
        # model_config = {
        #     "from_attributes": True,
        #     "json_encoders": {
        #         Decimal: lambda v: float(v) # Example if you need to serialize Decimal to float for JSON
        #     }
        # }


class FinancialKnowledgeDefinition(BaseModel):
    """
    Defines the structure for a financial knowledge category and its proficiency level.
    """
    category: str = Field(..., description="The category of financial knowledge (e.g., Budgeting, Investing)", example="Investing")
    level: int = Field(..., description="The proficiency level within the category (e.g., 1 for Beginner, 5 for Expert)", example=3)
    description: str = Field(..., description="A detailed description of what this level in this category entails", example="Understands basic investment products like stocks and bonds.")

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True} # Pydantic V2

class UserFinancialKnowledgeDetail(BaseModel):
    """
    Represents a user's specific financial knowledge level in a category, including the description.
    """
    category: str = Field(..., description="The category of financial knowledge", example="Budgeting")
    level: int = Field(..., description="The user's assessed level in this category", example=2)
    description: Optional[str] = Field(None, description="Description of the financial knowledge level, populated from definitions", example="Can create and follow a simple monthly budget.")

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True} # Pydantic V2

class IncomeDetailBase(BaseModel):
    """Base model for income details."""
    income_source: Optional[str] = Field(None, description="Source of the income (e.g., Salary, Freelance)", example="Salary")
    monthly_income: Optional[Decimal] = Field(None, description="Monthly income amount from this source", example=5000.00)
    description: Optional[str] = Field(None, description="Additional details about the income source", example="Primary job at Tech Corp")

class IncomeDetail(IncomeDetailBase):
    """Represents a specific income source for a user."""
    income_id: int = Field(..., description="Unique identifier for the income record", example=101)
    user_id: int = Field(..., description="Identifier of the user this income belongs to", example=1)

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True} # Pydantic V2

class DebtDetailBase(BaseModel):
    """Base model for debt details."""
    account_name: Optional[str] = Field(None, description="Name of the debt account (e.g., Credit Card, Student Loan)", example="Visa Credit Card")
    current_balance: Optional[Decimal] = Field(None, description="Current outstanding balance of the debt", example=2500.75)
    interest_rate: Optional[Decimal] = Field(None, description="Annual interest rate of the debt (e.g., 0.18 for 18%)", example=0.18)
    min_monthly_payment: Optional[Decimal] = Field(None, description="Minimum monthly payment required for this debt", example=50.00)

class DebtDetail(DebtDetailBase):
    """Represents a specific debt obligation for a user."""
    debt_id: int = Field(..., description="Unique identifier for the debt record", example=201)
    user_id: int = Field(..., description="Identifier of the user this debt belongs to", example=1)

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True} # Pydantic V2

class ExpenseDetailBase(BaseModel):
    """Base model for expense details."""
    expense_category: Optional[str] = Field(None, description="Category of the expense (e.g., Housing, Food, Transport)", example="Groceries")
    monthly_amount: Optional[Decimal] = Field(None, description="Estimated or actual monthly amount for this expense", example=300.00)
    description: Optional[str] = Field(None, description="Additional details about the expense", example="Weekly grocery shopping")
    timestamp: Optional[datetime] = Field(None, description="Timestamp of when the expense was recorded or occurred (if applicable)")

class ExpenseDetail(ExpenseDetailBase):
    """Represents a specific expense for a user."""
    expense_id: int = Field(..., description="Unique identifier for the expense record", example=301)
    user_id: int = Field(..., description="Identifier of the user this expense belongs to", example=1)

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True} # Pydantic V2

class ComprehensiveUserDetails(BaseModel):
    """
    A comprehensive model that aggregates all financial details for a user.
    This is typically used for endpoints that return a complete overview.
    """
    profile: Optional[UserProfile] = Field(None, description="User's profile information")
    financial_knowledge: List[UserFinancialKnowledgeDetail] = Field([], description="List of user's financial knowledge levels with descriptions")
    income: List[IncomeDetail] = Field([], description="List of user's income sources")
    debts: List[DebtDetail] = Field([], description="List of user's debt obligations")
    expenses: List[ExpenseDetail] = Field([], description="List of user's expenses")

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True} # Pydantic V2
