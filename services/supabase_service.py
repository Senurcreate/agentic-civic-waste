# ============================================================
# SUPABASE CLIENT
# ============================================================
import streamlit as st
#import toml

from supabase import create_client, Client


# Load secrets
#secrets = toml.load("secrets.toml")


SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]


if not SUPABASE_URL:
    raise ValueError(
        "SUPABASE_URL not found in secrets.toml"
    )


if not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_KEY not found in secrets.toml"
    )


# Create Supabase client
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)