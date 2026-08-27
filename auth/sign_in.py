import streamlit as st

from services.auth_service import (
    sign_in_user,
    get_user_role,
)


def show_sign_in():
    st.title("Sign In")
    st.write("Sign in to your CleanSight AI account.")

    email = st.text_input(
        "Email",
        key="signin_email",
    )

    password = st.text_input(
        "Password",
        type="password",
        key="signin_password",
    )

    if st.button(
        "Sign In",
        type="primary",
        use_container_width=True,
        key="signin_submit",
    ):
        if not email.strip() or not password:
            st.warning("Please enter your email and password.")
            return

        try:
            with st.spinner("Signing in..."):
                response = sign_in_user(
                    email.strip(),
                    password,
                )

            user = response.user

            if user is None:
                st.error("Sign in failed.")
                return

            role = get_user_role(user.id)
            role = str(role).strip().lower()

            st.session_state.auth_user = user
            st.session_state.user_role = role
            st.session_state.auth_page = None

            if role == "municipal":
                st.session_state.app_view = "Municipal"
            else:
                st.session_state.app_view = "Citizen"

            st.rerun()

        except Exception as e:
            st.error("Unable to sign in.")
            st.exception(e)

    st.divider()

    if st.button(
        "← Back",
        use_container_width=True,
        key="signin_back",
    ):
        st.session_state.auth_page = None
        st.rerun()
