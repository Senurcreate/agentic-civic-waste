from services.supabase_service import supabase


# ============================================================
# SIGN UP
# Public signup always creates CITIZEN accounts.
# The profiles row is created by the Supabase database trigger.
# ============================================================

def sign_up_user(
    full_name,
    email,
    password
):

    response = (
        supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "role": "citizen"
                    }
                }
            }
        )
    )

    return response


# ============================================================
# SIGN IN
# ============================================================

def sign_in_user(
    email,
    password
):

    return (
        supabase.auth
        .sign_in_with_password(
            {
                "email": email,
                "password": password
            }
        )
    )


# ============================================================
# GET ROLE
# ============================================================

def get_user_role(
    user_id
):

    response = (
        supabase
        .table("profiles")
        .select("role")
        .eq(
            "user_id",
            str(user_id)
        )
        .execute()
    )

    if not response.data:

        # No profile must never grant municipal access.
        return "citizen"

    role = (
        response.data[0]
        .get(
            "role",
            "citizen"
        )
    )

    return str(
        role
    ).strip().lower()


# ============================================================
# CURRENT USER
# ============================================================

def get_current_user():

    try:

        response = (
            supabase.auth
            .get_user()
        )

        return response.user

    except Exception:

        return None


# ============================================================
# SIGN OUT
# ============================================================

def sign_out_user():

    return (
        supabase.auth
        .sign_out()
    )
