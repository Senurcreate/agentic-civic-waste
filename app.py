import streamlit as st

from citizen_view import show_citizen_view
from municipal_view import show_municipal_view
from services.auth_service import get_current_user, get_user_role


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="CleanSight AI",
    page_icon="assets/icon.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# SESSION STATE
# ============================================================

def initialize_app_state():

    defaults = {
        "auth_user": None,
        "user_role": None,
        "app_view": "Citizen",
        "auth_page": None
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# RESTORE AUTH SESSION
# ============================================================

def restore_auth_session():

    # If the app already knows the current user,
    # do not fetch it again.
    if st.session_state.auth_user is not None:

        return

    try:

        user = get_current_user()

        if user is None:

            return

        role = get_user_role(
            user.id
        )

        st.session_state.auth_user = user
        st.session_state.user_role = role

        if role == "municipal":

            st.session_state.app_view = "Municipal"

        else:

            st.session_state.app_view = "Citizen"

    except Exception:

        # If there is no valid Supabase session,
        # continue as a public citizen visitor.
        st.session_state.auth_user = None
        st.session_state.user_role = None
        st.session_state.app_view = "Citizen"


# ============================================================
# MAIN ROUTING
# ============================================================

def main():

    initialize_app_state()

    restore_auth_session()

    role = st.session_state.get(
        "user_role"
    )

    # ========================================================
    # MUNICIPAL
    # ========================================================

    if role == "municipal":

        st.session_state.app_view = "Municipal"

        show_municipal_view()

        return

    # ========================================================
    # CITIZEN / PUBLIC USER
    # ========================================================

    # For the MVP, signed-in citizens and public visitors
    # use the same citizen interface.
    #
    # There is no separate personalized citizen dashboard yet.
    st.session_state.app_view = "Citizen"

    show_citizen_view()


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":

    main()
