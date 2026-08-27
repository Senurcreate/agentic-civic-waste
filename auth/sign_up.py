import streamlit as st

from services.auth_service import (
    sign_up_user,
    sign_in_user,
    get_user_role
)


def show_sign_up():

    left, right = st.columns(
        [5, 1]
    )

    with left:

        st.title(
            "Create Account"
        )

        st.caption(
            "Create a CleanSight AI citizen account."
        )

    with right:

        if st.button(
            "← Back",
            use_container_width=True,
            key="signup_back"
        ):

            st.session_state.auth_page = None

            st.rerun()


    st.divider()


    _, center, _ = st.columns(
        [1, 1.5, 1]
    )


    with center:

        st.markdown(
            "### ♻️ Join CleanSight AI"
        )


        full_name = st.text_input(
            "Full Name",
            placeholder="Enter your full name",
            key="register_name"
        )


        email = st.text_input(
            "Email Address",
            placeholder="you@example.com",
            key="register_email"
        )


        password = st.text_input(
            "Password",
            type="password",
            placeholder="Create a password",
            key="register_password"
        )


        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Re-enter your password",
            key="register_confirm_password"
        )


        st.text_input(
            "Account Type",
            value="Citizen",
            disabled=True
        )


        terms = st.checkbox(
            "I agree to the Terms of Use and Privacy Policy.",
            key="register_terms"
        )


        if st.button(
            "Create Account",
            type="primary",
            use_container_width=True,
            key="register_submit"
        ):

            if not full_name.strip():

                st.error(
                    "Please enter your full name."
                )


            elif not email.strip():

                st.error(
                    "Please enter your email address."
                )


            elif len(password) < 8:

                st.error(
                    "Password must contain at least 8 characters."
                )


            elif password != confirm_password:

                st.error(
                    "Passwords do not match."
                )


            elif not terms:

                st.error(
                    "Please accept the Terms of Use "
                    "and Privacy Policy."
                )


            else:

                try:

                    response = sign_up_user(
                        full_name.strip(),
                        email.strip(),
                        password
                    )

                    if not response.user:

                        st.error(
                            "The account could not be created."
                        )
                        return

                    # If Supabase returned a session, use it directly.
                    if response.session:

                        user = response.user

                    else:

                        # MVP behaviour:
                        # immediately sign the new citizen in.
                        login_response = sign_in_user(
                            email.strip(),
                            password
                        )

                        user = login_response.user

                        if not user:

                            st.error(
                                "The account was created, but automatic "
                                "sign in failed."
                            )
                            return

                    role = get_user_role(
                        user.id
                    )

                    st.session_state.auth_user = user
                    st.session_state.user_role = role
                    st.session_state.auth_page = None
                    st.session_state.app_view = "Citizen"
                    st.session_state.citizen_started = False

                    st.success(
                        "Account created successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Could not create the account."
                    )

                    st.exception(e)


        st.divider()


        st.write(
            "Already have an account?"
        )


        if st.button(
            "Sign In Instead",
            use_container_width=True,
            key="register_signin"
        ):

            st.session_state.auth_page = "signin"

            st.rerun()
