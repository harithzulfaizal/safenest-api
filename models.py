# ================================================
# FILE: models.py
# ================================================
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta # Added timedelta
from pydantic import BaseModel, Field, EmailStr

# --- Pydantic Models for Data Structuring ---

# User Profile Models
class UserProfileBase(BaseModel):
    """Base model for user profile attributes, used for creation or partial updates if needed."""
    age: Optional[int] = Field(None, description="User's age")
    num_children: Optional[int] = Field(None, description="Number of children the user has")
    marital_status: Optional[str] = Field(None, description="User's marital status (e.g., Single, Married)")
    retirement_status: Optional[str] = Field(None, description="User's retirement status (e.g., Employed, Retired)")
    goals: Optional[Dict[str, Any]] = Field(None, description="User's financial or life goals, stored as a JSON object")

class UserProfileCreate(UserProfileBase):
    """Model for creating a new user profile. user_id is typically assigned by the database or an external system."""
    pass

class UserProfileUpdate(UserProfileBase):
    """Model for updating an existing user profile. All fields are optional."""
    pass # Inherits all optional fields from UserProfileBase

class UserProfile(UserProfileBase):
    """
    Represents a user's profile information.
    Inherits common fields from UserProfileBase and adds user_id.
    """
    user_id: int = Field(..., description="Unique identifier for the user", example=1)

    class Config:
        orm_mode = True
        # For Pydantic V2:
        # model_config = {"from_attributes": True}

# Financial Knowledge Definition Models
class FinancialKnowledgeDefinitionBase(BaseModel):
    """Base model for financial knowledge definition attributes."""
    category: str = Field(..., description="The category of financial knowledge (e.g., Budgeting, Investing)", example="Investing")
    level: int = Field(..., description="The proficiency level within the category (e.g., 1 for Beginner, 5 for Expert)", example=3)
    description: str = Field(..., description="A detailed description of what this level in this category entails", example="Understands basic investment products like stocks and bonds.")

class FinancialKnowledgeDefinitionCreate(FinancialKnowledgeDefinitionBase):
    """Model for creating a new financial knowledge definition."""
    pass

class FinancialKnowledgeDefinitionUpdate(BaseModel):
    """Model for updating an existing financial knowledge definition. All fields are optional."""
    category: Optional[str] = Field(None, description="The category of financial knowledge")
    level: Optional[int] = Field(None, description="The proficiency level within the category")
    description: Optional[str] = Field(None, description="A detailed description of what this level entails")

class FinancialKnowledgeDefinition(FinancialKnowledgeDefinitionBase):
    """
    Defines the structure for a financial knowledge category and its proficiency level, including its unique ID.
    """
    id: int = Field(..., description="Unique identifier for the financial knowledge definition", example=1)

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True} # Pydantic V2

# User Financial Knowledge Models
class UserFinancialKnowledgeCreate(BaseModel):
    """Model for adding a financial knowledge category and level for a user."""
    category: str = Field(..., description="The category of financial knowledge", example="Budgeting")
    level: int = Field(..., description="The user's assessed level in this category", example=2)

class UserFinancialKnowledgeUpdate(BaseModel):
    """Model for updating a user's financial knowledge level in a specific category."""
    level: int = Field(..., description="The new user's assessed level in this category", example=3)

class UserFinancialKnowledgeDetail(BaseModel):
    """
    Represents a user's specific financial knowledge level in a category, including the description.
    """
    user_id: Optional[int] = Field(None, description="Unique identifier for the user, if relevant in this context")
    category: str = Field(..., description="The category of financial knowledge", example="Budgeting")
    level: int = Field(..., description="The user's assessed level in this category", example=2)
    description: Optional[str] = Field(None, description="Description of the financial knowledge level, populated from definitions", example="Can create and follow a simple monthly budget.")

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True} # Pydantic V2

# Income Models
class IncomeDetailBase(BaseModel):
    """Base model for income details."""
    income_source: Optional[str] = Field(None, description="Source of the income (e.g., Salary, Freelance)", example="Salary")
    monthly_income: Optional[Decimal] = Field(None, description="Monthly income amount from this source", example=5000.00)
    description: Optional[str] = Field(None, description="Additional details about the income source", example="Primary job at Tech Corp")

class IncomeDetailCreate(IncomeDetailBase):
    """Model for creating an income detail record for a user."""
    pass

class IncomeDetailUpdate(IncomeDetailBase):
    """Model for updating an income detail record. All fields are optional."""
    pass

class IncomeDetail(IncomeDetailBase):
    """Represents a specific income source for a user."""
    income_id: int = Field(..., description="Unique identifier for the income record", example=101)
    user_id: int = Field(..., description="Identifier of the user this income belongs to", example=1)

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True}

# Debt Models
class DebtDetailBase(BaseModel):
    """Base model for debt details."""
    account_name: Optional[str] = Field(None, description="Name of the debt account (e.g., Credit Card, Student Loan)", example="Visa Credit Card")
    current_balance: Optional[Decimal] = Field(None, description="Current outstanding balance of the debt", example=2500.75)
    interest_rate: Optional[Decimal] = Field(None, description="Annual interest rate of the debt (e.g., 0.18 for 18%)", example=0.18)
    min_monthly_payment: Optional[Decimal] = Field(None, description="Minimum monthly payment required for this debt", example=50.00)

class DebtDetailCreate(DebtDetailBase):
    """Model for creating a debt detail record for a user."""
    pass

class DebtDetailUpdate(DebtDetailBase):
    """Model for updating a debt detail record. All fields are optional."""
    pass

class DebtDetail(DebtDetailBase):
    """Represents a specific debt obligation for a user."""
    debt_id: int = Field(..., description="Unique identifier for the debt record", example=201)
    user_id: int = Field(..., description="Identifier of the user this debt belongs to", example=1)

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True}

# Expense Models
class ExpenseDetailBase(BaseModel):
    """Base model for expense details."""
    expense_category: Optional[str] = Field(None, description="Category of the expense (e.g., Housing, Food, Transport)", example="Groceries")
    monthly_amount: Optional[Decimal] = Field(None, description="Estimated or actual monthly amount for this expense", example=300.00)
    description: Optional[str] = Field(None, description="Additional details about the expense", example="Weekly grocery shopping")
    timestamp: Optional[datetime] = Field(description="Timestamp of when the expense was recorded or occurred (if applicable)", default_factory=datetime.utcnow)

class ExpenseDetailCreate(ExpenseDetailBase):
    """Model for creating an expense detail record for a user."""
    pass

class ExpenseDetailUpdate(ExpenseDetailBase):
    """Model for updating an expense detail record. All fields are optional."""
    timestamp: Optional[datetime] = Field(None, description="Timestamp of when the expense was recorded or occurred (if applicable)")


class ExpenseDetail(ExpenseDetailBase):
    """Represents a specific expense for a user."""
    expense_id: int = Field(..., description="Unique identifier for the expense record", example=301)
    user_id: int = Field(..., description="Identifier of the user this expense belongs to", example=1)

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True}

# Comprehensive User Details
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
        # model_config = {"from_attributes": True}

# --- User Login Models (Registration) ---
class UserLoginCreate(BaseModel):
    """Model for creating new login credentials for a user during registration."""
    user_id: int = Field(..., description="The ID of the user to associate these login credentials with", example=1)
    email: EmailStr = Field(..., description="User's email address for login", example="user@example.com")
    password: str = Field(..., min_length=8, description="User's password (will be securely hashed before storage)", example="securepassword123")

class UserLoginResponse(BaseModel):
    """Model for the response after creating user login credentials (registration)."""
    login_id: int = Field(..., description="The ID of the login record created")
    user_id: int = Field(..., description="The ID of the user")
    email: EmailStr = Field(..., description="User's email address")
    last_login: Optional[datetime] = Field(None, description="Timestamp of the last successful login, null on creation")
    created_at: Optional[datetime] = Field(None, description="Timestamp of when the login record was created")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of when the login record was last updated")

    class Config:
        orm_mode = True
        # model_config = {"from_attributes": True}

# --- User Login Models (Authentication) ---
class UserLoginRequest(BaseModel):
    """Model for user login request (authentication)."""
    email: EmailStr = Field(..., description="User's email address for login", example="user@example.com")
    password: str = Field(..., description="User's password", example="securepassword123")

class UserLoginSuccessResponse(BaseModel):
    """Model for a successful login response (simple version, no token)."""
    user_id: int = Field(..., description="The ID of the logged-in user")
    email: EmailStr = Field(..., description="User's email address")
    message: str = Field(default="Login successful", description="Login status message")

    class Config:
        orm_mode = True # Important if you are returning ORM objects directly

# --- Token Models (for JWT - can be used later if full auth is implemented) ---
class Token(BaseModel):
    """Model for the JWT access token."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Data/payload contained within a JWT."""
    email: Optional[EmailStr] = None
    user_id: Optional[int] = None # Added user_id to token data
