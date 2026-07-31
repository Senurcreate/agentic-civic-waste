import streamlit as st

try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
    supabase_url = st.secrets["SUPABASE_URL"]
    st.success("✅ Secrets loaded successfully!")
except Exception as e:
    st.error(f"❌ Could not load secrets: {e}")