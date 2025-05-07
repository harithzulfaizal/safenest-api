# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This allows you to keep sensitive information like API keys out of your codebase.
# Create a .env file in the root of your project with:
# SUPABASE_URL="your_supabase_url"
# SUPABASE_SERVICE_KEY="your_supabase_service_key"
load_dotenv()

# Supabase Configuration
# Fetches the Supabase URL and Service Key from environment variables.
# It's good practice to provide default values or handle cases where they might not be set,
# though for this application, they are essential.
SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")

# Application settings (example)
# You can add other application-wide configurations here.
# For instance, API version, application name, etc.
APP_VERSION = "1.1.0"
APP_TITLE = "User Financial Details API - Modular"
APP_DESCRIPTION = "API to retrieve comprehensive and granular financial details for a user (Modular Structure)."

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("CRITICAL ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables or .env file.")
    # In a real application, you might exit or raise a more specific configuration error.
    # For simplicity here, we just print, but the get_supabase_client will raise an HTTPException.
