import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "your_supabase_url_here")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "your_supabase_service_key_here")

APP_VERSION = "1.2.0"
APP_TITLE = "User Financial Details API - Modular"
APP_DESCRIPTION = "API to retrieve comprehensive and granular financial details for a user, including authentication (Modular Structure)."

# JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your_super_secret_random_key_for_jwt_here_min_32_chars")
# JWT_ALGORITHM: str = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if not SUPABASE_URL or SUPABASE_URL == "your_supabase_url_here":
    print("CRITICAL ERROR: SUPABASE_URL must be set in environment variables or .env file and not be the placeholder value.")

if not SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_KEY == "your_supabase_service_key_here":
    print("CRITICAL ERROR: SUPABASE_SERVICE_KEY must be set in environment variables or .env file and not be the placeholder value.")

# if not JWT_SECRET_KEY or JWT_SECRET_KEY == "your_super_secret_random_key_for_jwt_here_min_32_chars":
#     print("WARNING: JWT_SECRET_KEY is not set or is using the placeholder. This is insecure for production.")

print(f"Config loaded: SUPABASE_URL (ending): ...{SUPABASE_URL[-10:] if SUPABASE_URL else 'N/A'}")
# print(f"Config loaded: JWT_SECRET_KEY (status): {'SET' if JWT_SECRET_KEY and JWT_SECRET_KEY != 'your_super_secret_random_key_for_jwt_here_min_32_chars' else 'NOT SET or PLACEHOLDER'}")
