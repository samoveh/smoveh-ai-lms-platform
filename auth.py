from supabase import create_client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create Supabase client
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================
# SIGNUP FUNCTION
# =========================

def sign_up(email, password):

    try:

        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        return response

    except Exception as e:

        return str(e)

# =========================
# LOGIN FUNCTION
# =========================

def sign_in(email, password):

    try:

        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        return response

    except Exception as e:

        return str(e)

# =========================
# LOGOUT FUNCTION
# =========================

def sign_out():

    supabase.auth.sign_out()