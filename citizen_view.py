# ============================================================
# CLEANSIGHT AI
# CITIZEN VIEW
# ============================================================

import uuid
import math
from datetime import datetime, timedelta

import streamlit as st
import folium

from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

# ============================================================
# AUTH VIEWS
# ============================================================

from auth.sign_in import show_sign_in
from auth.sign_up import show_sign_up
from services.auth_service import sign_out_user

# ============================================================
# BACKEND SERVICES
# ============================================================

from services.location_service import (
    geocode_address,
    reverse_geocode
)

from services.ai_service import (
    analyze_waste_image
)

from services.report_service import (
    save_report
)

from services.supabase_service import (
    supabase
)


# ============================================================
# CONSTANTS
# ============================================================

STORAGE_BUCKET = "waste-images"

DEFAULT_SRI_LANKA_LAT = 7.8731
DEFAULT_SRI_LANKA_LON = 80.7718

# Duplicate detection
DUPLICATE_RADIUS_METERS = 200
DUPLICATE_LOOKBACK_HOURS = 72


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

def initialize_citizen_state():

    defaults = {

        # Navigation
        "citizen_started": False,
        "auth_page": None,

        # Authentication
        "auth_user": None,

        # Stepper
        "report_step": 1,

        # Image
        "report_image_bytes": None,
        "report_image_name": None,
        "report_image_type": None,

        # Location
        "location_method": "Address / Landmark",
        "location_address": "",
        "location_search_text": "",
        "location_resolved_address": "",
        "location_match_precision": None,
        "location_landmark": "",
        "location_lat": None,
        "location_lon": None,
        "location_source": None,
        "location_confirmed": False,

        # Display-only location fields
        "detected_location_display": "Not selected",
        "location_source_display": "Not selected",
        "latitude_display": "Not available",
        "longitude_display": "Not available",

        # Citizen details
        "citizen_description": "",

        # AI
        "ai_result": None,

        # Priority
        "priority_score": None,
        "priority_level": None,

        # Submission
        "report_submitted": False,
        "saved_report_id": None,

        # Duplicate detection
        "possible_duplicate": None,
        "duplicate_check_completed": False,
        "duplicate_override": False
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# RESET REPORT
# ============================================================

def reset_report():

    st.session_state.report_step = 1

    st.session_state.report_image_bytes = None
    st.session_state.report_image_name = None
    st.session_state.report_image_type = None

    st.session_state.location_method = "Address / Landmark"

    st.session_state.location_address = ""
    st.session_state.location_search_text = ""
    st.session_state.location_resolved_address = ""
    st.session_state.location_match_precision = None
    st.session_state.location_landmark = ""
    st.session_state.location_lat = None
    st.session_state.location_lon = None
    st.session_state.location_source = None
    st.session_state.location_confirmed = False

    st.session_state.detected_location_display = (
        "Not selected"
    )

    st.session_state.location_source_display = (
        "Not selected"
    )

    st.session_state.latitude_display = (
        "Not available"
    )

    st.session_state.longitude_display = (
        "Not available"
    )

    st.session_state.citizen_description = ""

    st.session_state.ai_result = None

    st.session_state.priority_score = None
    st.session_state.priority_level = None

    st.session_state.report_submitted = False
    st.session_state.saved_report_id = None

    st.session_state.possible_duplicate = None
    st.session_state.duplicate_check_completed = False
    st.session_state.duplicate_override = False


# ============================================================
# UPDATE LOCATION DISPLAY FIELDS
# ============================================================

def update_location_display_fields():

    if st.session_state.location_source == "Address":
        display_location = (
            st.session_state.location_search_text
            or
            st.session_state.location_address
        )
    else:
        display_location = st.session_state.location_address

    st.session_state.detected_location_display = (
        display_location
        or
        "Not selected"
    )

    st.session_state.location_source_display = (
        st.session_state.location_source
        or
        "Not selected"
    )

    if st.session_state.location_lat is not None:

        st.session_state.latitude_display = (
            f"{st.session_state.location_lat:.6f}"
        )

    else:

        st.session_state.latitude_display = (
            "Not available"
        )

    if st.session_state.location_lon is not None:

        st.session_state.longitude_display = (
            f"{st.session_state.location_lon:.6f}"
        )

    else:

        st.session_state.longitude_display = (
            "Not available"
        )


# ============================================================
# PRIORITY CALCULATION
# ============================================================

def calculate_priority(
    hazard_score,
    estimated_volume
):

    volume_scores = {
        "Small": 30,
        "Medium": 60,
        "Large": 100
    }

    hazard_normalized = (
        hazard_score / 10
    ) * 100

    volume_normalized = (
        volume_scores.get(
            estimated_volume,
            50
        )
    )

    total_score = (
        hazard_normalized * 0.70
        +
        volume_normalized * 0.30
    )

    if total_score >= 75:

        priority_level = "HIGH"

    elif total_score >= 45:

        priority_level = "MEDIUM"

    else:

        priority_level = "LOW"

    return (
        round(total_score, 1),
        priority_level
    )


# ============================================================
# SUPABASE IMAGE UPLOAD
# ============================================================

def upload_report_image():

    image_bytes = (
        st.session_state.report_image_bytes
    )

    if not image_bytes:

        raise ValueError(
            "No report image is available."
        )

    original_name = (
        st.session_state.report_image_name
        or
        "waste.jpg"
    )

    if "." in original_name:

        extension = (
            original_name
            .split(".")[-1]
            .lower()
        )

    else:

        extension = "jpg"

    file_id = str(
        uuid.uuid4()
    )

    storage_path = (
        f"reports/{file_id}.{extension}"
    )

    mime_type = (
        st.session_state.report_image_type
        or
        f"image/{extension}"
    )

    supabase.storage.from_(
        STORAGE_BUCKET
    ).upload(
        path=storage_path,
        file=image_bytes,
        file_options={
            "content-type": mime_type,
            "upsert": "false"
        }
    )

    public_url = (
        supabase.storage
        .from_(STORAGE_BUCKET)
        .get_public_url(
            storage_path
        )
    )

    return (
        storage_path,
        public_url
    )


# ============================================================
# PUBLIC HEADER
# ============================================================

def render_public_header():

    auth_user = st.session_state.get(
        "auth_user"
    )

    if auth_user:

        logo_col, spacer_col, logout_col = (
            st.columns(
                [3.5, 6.2, 1.3],
                vertical_alignment="center"
            )
        )

    else:

        logo_col, spacer_col, signin_col, signup_col = (
            st.columns(
                [3.5, 5, 1.2, 1.2],
                vertical_alignment="center"
            )
        )

    with logo_col:

        st.markdown(
            "### ♻️ CleanSight AI"
        )

    if auth_user:

        with logout_col:

            if st.button(
                "Log Out",
                use_container_width=True,
                key="citizen_logout"
            ):

                sign_out_user()

                st.session_state.auth_user = None
                st.session_state.user_role = None
                st.session_state.auth_page = None
                st.session_state.app_view = "Citizen"
                st.session_state.citizen_started = False

                st.rerun()

    else:

        with signin_col:

            if st.button(
                "Sign In",
                use_container_width=True,
                key="header_signin"
            ):

                st.session_state.auth_page = "signin"

                st.rerun()

        with signup_col:

            if st.button(
                "Sign Up",
                type="primary",
                use_container_width=True,
                key="header_signup"
            ):

                st.session_state.auth_page = "signup"

                st.rerun()

    st.divider()


# ============================================================
# HERO
# ============================================================

def render_hero():

    # Centered hero.
    # The content still uses normal Streamlit components.
    # A very small CSS rule is used only because Streamlit
    # does not provide a native text-alignment option.

    st.markdown(
        """
<style>
.st-key-clean_hero h1,
.st-key-clean_hero h2,
.st-key-clean_hero h3,
.st-key-clean_hero p {
    text-align: center;
}
</style>
        """,
        unsafe_allow_html=True
    )

    left, center, right = st.columns(
        [1, 2.4, 1]
    )

    with center:

        with st.container(
            key="clean_hero"
        ):

            st.markdown(
                "### AI-ASSISTED CIVIC WASTE REPORTING"
            )

            st.title(
                "Together for a Cleaner Sri Lanka"
            )

            st.write(
                "See illegal waste dumping? "
                "Report it quickly and help municipal authorities "
                "respond with clearer, structured information."
            )

            st.write("")

            if st.button(
                "♻️ Report Waste Now",
                type="primary",
                use_container_width=True,
                key="hero_report"
            ):

                reset_report()

                st.session_state.citizen_started = True

                st.rerun()

            st.caption(
                "No account required to submit "
                "a waste report."
            )


# ============================================================
# HOW IT WORKS
# ============================================================

def render_how_it_works():

    st.divider()

    st.header(
        "How it works"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.subheader(
            "📷 Photo"
        )

        st.write(
            "Upload a clear photograph "
            "of the waste incident."
        )

    with c2:

        st.subheader(
            "📍 Location"
        )

        st.write(
            "Use your current location "
            "or enter an address or landmark."
        )

    with c3:

        st.subheader(
            "🤖 AI Analysis"
        )

        st.write(
            "AI converts the photograph "
            "into structured incident information."
        )

    with c4:

        st.subheader(
            "🏢 Review"
        )

        st.write(
            "Municipal officers review "
            "the submitted incident."
        )


# ============================================================
# LANDING PAGE
# ============================================================

def render_landing():

    render_public_header()

    render_hero()

    render_how_it_works()


# ============================================================
# REPORT HEADER
# ============================================================

def render_report_header():

    left, right = st.columns(
        [5, 1]
    )

    with left:

        st.title(
            "Report Illegal Waste"
        )

        st.caption(
            "Complete the steps below "
            "to create your incident report."
        )

    with right:

        if st.button(
            "← Home",
            use_container_width=True,
            key="report_home"
        ):

            reset_report()

            st.session_state.citizen_started = False

            st.rerun()


# ============================================================
# STEPPER
# ============================================================

def render_stepper():

    current_step = (
        st.session_state.report_step
    )

    steps = [
        (1, "Photo"),
        (2, "Location"),
        (3, "AI Analysis"),
        (4, "Review"),
        (5, "Submit")
    ]

    columns = st.columns(
        len(steps)
    )

    for column, (
        step_number,
        step_name
    ) in zip(
        columns,
        steps
    ):

        with column:

            if step_number < current_step:

                st.success(
                    f"✓ {step_name}"
                )

            elif step_number == current_step:

                st.info(
                    f"{step_number}. {step_name}"
                )

            else:

                st.caption(
                    f"{step_number}. {step_name}"
                )


# ============================================================
# STEP 1 - PHOTO
# ============================================================

def render_photo_step():

    st.subheader(
        "Step 1 — Upload a Photograph"
    )

    st.write(
        "Upload a clear image showing "
        "the waste dumping incident."
    )

    uploaded_image = st.file_uploader(
        "Waste photograph",
        type=[
            "jpg",
            "jpeg",
            "png"
        ],
        accept_multiple_files=False,
        key="citizen_image"
    )

    if uploaded_image:

        st.session_state.report_image_bytes = (
            uploaded_image.getvalue()
        )

        st.session_state.report_image_name = (
            uploaded_image.name
        )

        st.session_state.report_image_type = (
            uploaded_image.type
        )

    if st.session_state.report_image_bytes:

        st.image(
            st.session_state.report_image_bytes,
            caption=(
                st.session_state.report_image_name
            ),
            use_container_width=True
        )

        st.success(
            "✓ Photograph added."
        )

    st.divider()

    _, next_col = st.columns(2)

    with next_col:

        if st.button(
            "Continue to Location →",
            type="primary",
            use_container_width=True,
            key="photo_continue"
        ):

            if not st.session_state.report_image_bytes:

                st.error(
                    "Please upload a photograph first."
                )

            else:

                st.session_state.report_step = 2

                st.rerun()


# ============================================================
# STEP 2 - LOCATION
# ============================================================

def render_location_step():

    st.subheader(
        "Step 2 — Incident Location"
    )

    st.write(
        "Tell us where the waste is. You can type the location "
        "the same way you normally would in everyday life."
    )

    method = st.radio(
        "Location method",
        [
            "🔎 Enter Address / Landmark",
            "📍 Use Current Location"
        ],
        horizontal=True,
        index=(
            0
            if st.session_state.location_method
            == "Address / Landmark"
            else 1
        ),
        key="location_method_selector"
    )

    # ========================================================
    # ADDRESS / LANDMARK
    # ========================================================

    if method == "🔎 Enter Address / Landmark":

        st.session_state.location_method = (
            "Address / Landmark"
        )

        st.info(
            "You do not need to use a formal postal address. "
            "Examples: 'Jambugasmulla Rd, Kohuwala', "
            "'near Keells Kohuwala', or 'Balapokuna, Nugegoda'."
        )

        address = st.text_input(
            "Where is the waste?",
            value=st.session_state.location_search_text,
            placeholder=(
                "Example: 29/B Jambugasmulla Rd, Kohuwala"
            ),
            help=(
                "Enter a house number, road, landmark, town, "
                "or any combination you normally use."
            ),
            key="address_search_input"
        )

        if st.button(
            "🔎 Find Location",
            use_container_width=True,
            key="find_location"
        ):

            if not address.strip():

                st.warning(
                    "Please enter a road, landmark, town, "
                    "or nearby place."
                )

            else:

                try:

                    with st.spinner(
                        "Finding the closest matching location..."
                    ):

                        location = geocode_address(
                            address
                        )

                    if location is None:

                        st.error(
                            "We couldn't locate that place automatically. "
                            "Try the road or nearby area only, for example "
                            "'Jambugasmulla Road, Kohuwala'."
                        )

                    else:

                        # Keep exactly what the citizen typed for the UI.
                        st.session_state.location_search_text = (
                            address.strip()
                        )

                        st.session_state.location_address = (
                            address.strip()
                        )

                        # Keep the geocoder's formal result separately.
                        st.session_state.location_resolved_address = (
                            location.get("address", "")
                        )

                        st.session_state.location_match_precision = (
                            location.get("match_precision")
                        )

                        st.session_state.location_lat = (
                            float(
                                location["latitude"]
                            )
                        )

                        st.session_state.location_lon = (
                            float(
                                location["longitude"]
                            )
                        )

                        st.session_state.location_source = (
                            "Address"
                        )

                        st.session_state.location_confirmed = (
                            True
                        )

                        update_location_display_fields()

                        st.rerun()

                except Exception as e:

                    st.error(
                        "Could not search for this location right now."
                    )

                    st.exception(e)

        # Explain when the fallback matched a broader nearby area.
        if (
            st.session_state.location_source == "Address"
            and
            st.session_state.location_lat is not None
        ):

            precision = (
                st.session_state.location_match_precision
            )

            if precision == "area":

                st.warning(
                    "The exact address was not available in the map data, "
                    "so CleanSight located the nearest matching area. "
                    "Please check the map preview below."
                )

            elif precision in ("road", "place"):

                st.success(
                    "✓ Location found from the information you entered."
                )

            elif precision == "exact":

                st.success(
                    "✓ Location found."
                )

    # ========================================================
    # CURRENT GPS
    # ========================================================

    else:

        st.session_state.location_method = (
            "GPS"
        )

        st.info(
            "Use this option if you are currently "
            "at or near the waste dumping site."
        )

        st.caption(
            "Your browser may ask for permission "
            "to access your location."
        )

        gps_data = streamlit_geolocation()

        if gps_data:

            latitude = gps_data.get(
                "latitude"
            )

            longitude = gps_data.get(
                "longitude"
            )

            if (
                latitude is not None
                and
                longitude is not None
            ):

                latitude = float(
                    latitude
                )

                longitude = float(
                    longitude
                )

                previous_lat = (
                    st.session_state.location_lat
                )

                previous_lon = (
                    st.session_state.location_lon
                )

                location_changed = (
                    previous_lat is None
                    or
                    previous_lon is None
                    or
                    abs(
                        previous_lat - latitude
                    ) > 0.00001
                    or
                    abs(
                        previous_lon - longitude
                    ) > 0.00001
                )

                st.session_state.location_lat = (
                    latitude
                )

                st.session_state.location_lon = (
                    longitude
                )

                st.session_state.location_source = (
                    "Current GPS"
                )

                st.session_state.location_match_precision = (
                    "gps"
                )

                needs_address = (
                    not st.session_state.location_address
                    or
                    st.session_state.location_address
                    == "Current GPS Location"
                    or
                    location_changed
                )

                if needs_address:

                    try:

                        with st.spinner(
                            "Finding your address..."
                        ):

                            detected_address = (
                                reverse_geocode(
                                    latitude,
                                    longitude
                                )
                            )

                        st.session_state.location_address = (
                            detected_address
                        )

                        st.session_state.location_resolved_address = (
                            detected_address
                        )

                        st.session_state.location_search_text = ""

                    except Exception:

                        fallback_location = (
                            f"{latitude:.6f}, "
                            f"{longitude:.6f}"
                        )

                        st.session_state.location_address = (
                            fallback_location
                        )

                        st.session_state.location_resolved_address = (
                            fallback_location
                        )

                        st.session_state.location_search_text = ""

                st.session_state.location_confirmed = (
                    True
                )

                update_location_display_fields()

        if (
            st.session_state.location_source
            == "Current GPS"
            and
            st.session_state.location_lat
            is not None
            and
            st.session_state.location_lon
            is not None
        ):

            st.success(
                "✓ Current location detected."
            )

    # ========================================================
    # KEEP DISPLAY FIELDS SYNCHRONIZED
    # ========================================================

    update_location_display_fields()

    # ========================================================
    # MAP PREVIEW
    # ========================================================

    st.markdown(
        "### Location Preview"
    )

    if (
        st.session_state.location_lat
        is not None
        and
        st.session_state.location_lon
        is not None
    ):

        map_center = [
            st.session_state.location_lat,
            st.session_state.location_lon
        ]

        zoom_level = 16

    else:

        map_center = [
            DEFAULT_SRI_LANKA_LAT,
            DEFAULT_SRI_LANKA_LON
        ]

        zoom_level = 7

    location_map = folium.Map(
        location=map_center,
        zoom_start=zoom_level
    )

    if (
        st.session_state.location_lat
        is not None
        and
        st.session_state.location_lon
        is not None
    ):

        marker_tooltip = (
            st.session_state.location_search_text
            or
            st.session_state.location_address
            or
            "Waste incident location"
        )

        marker_popup = (
            st.session_state.location_resolved_address
            or
            st.session_state.location_address
            or
            "Waste incident location"
        )

        folium.Marker(
            [
                st.session_state.location_lat,
                st.session_state.location_lon
            ],
            tooltip=marker_tooltip,
            popup=marker_popup,
            icon=folium.Icon(
                color="red"
            )
        ).add_to(
            location_map
        )

    st_folium(
        location_map,
        height=380,
        use_container_width=True,
        key="citizen_location_map"
    )

    # ========================================================
    # LOCATION DETAILS
    # ========================================================

    st.markdown(
        "### Location Details"
    )

    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:

        st.text_input(
            "Detected Location",
            key="detected_location_display",
            disabled=True
        )

    with row1_col2:

        st.text_input(
            "Location Source",
            key="location_source_display",
            disabled=True
        )

    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:

        st.text_input(
            "Latitude",
            key="latitude_display",
            disabled=True
        )

    with row2_col2:

        st.text_input(
            "Longitude",
            key="longitude_display",
            disabled=True
        )

    # ========================================================
    # LANDMARK / NEARBY PLACE
    # ========================================================

    st.markdown(
        "### Landmark / Nearby Place"
    )

    landmark = st.text_input(
        "Landmark or nearby place (optional)",
        value=st.session_state.location_landmark,
        placeholder=(
            "Example: Near Keells, bus stop, school gate"
        ),
        help=(
            "Add a nearby landmark that can help the "
            "municipal officer locate the waste more easily."
        ),
        key="location_landmark_input"
    )

    st.session_state.location_landmark = (
        landmark.strip()
    )

    # ========================================================
    # ADDITIONAL INFORMATION
    # ========================================================

    st.markdown(
        "### Additional Information"
    )

    description = st.text_area(
        "Description (optional)",
        value=(
            st.session_state.citizen_description
        ),
        placeholder=(
            "Example: Large waste pile beside the road "
            "near the bus stop."
        ),
        key="location_description"
    )

    st.session_state.citizen_description = (
        description
    )

    # ========================================================
    # LOCATION STATUS
    # ========================================================

    valid_location = (
        st.session_state.location_lat
        is not None
        and
        st.session_state.location_lon
        is not None
    )

    if valid_location:

        st.success(
            "✓ Incident location is ready."
        )

    else:

        st.warning(
            "Provide a valid location before continuing."
        )

    # ========================================================
    # NAVIGATION
    # ========================================================

    st.divider()

    back_col, next_col = st.columns(2)

    with back_col:

        if st.button(
            "← Back",
            use_container_width=True,
            key="location_back"
        ):

            st.session_state.report_step = 1

            st.rerun()

    with next_col:

        if st.button(
            "Continue to AI Analysis →",
            type="primary",
            use_container_width=True,
            key="location_next"
        ):

            if not valid_location:

                st.error(
                    "Please provide a valid "
                    "incident location first."
                )

            else:

                st.session_state.report_step = 3

                st.rerun()


# ============================================================
# DISPLAY AI RESULT
# ============================================================

def display_ai_result(result):

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Hazard",
        f"{result['hazard_score']}/10"
    )

    c2.metric(
        "Volume",
        result["estimated_volume"]
    )

    c3.metric(
        "Confidence",
        f"{result['confidence'] * 100:.0f}%"
    )

    st.write(
        "**Waste Type**"
    )

    st.write(
        result["waste_type"]
    )

    st.write(
        "**Description**"
    )

    st.write(
        result["description"]
    )

    st.write(
        "**Road Access**"
    )

    st.write(
        result["road_access"]
    )

    st.write(
        "**Recommended Vehicle**"
    )

    st.write(
        result["recommended_vehicle"]
    )

    st.write(
        "**Visible Hazards**"
    )

    hazards = (
        result.get(
            "visible_hazards"
        )
        or []
    )

    if hazards:

        for hazard in hazards:

            st.write(
                f"- {hazard}"
            )

    else:

        st.write(
            "None identified"
        )

    st.write(
        "**Calculated Cleanup Priority**"
    )

    st.write(
        f"{st.session_state.priority_level} "
        f"({st.session_state.priority_score}/100)"
    )


# ============================================================
# STEP 3 - AI ANALYSIS
# ============================================================

def render_analysis_step():

    st.subheader(
        "Step 3 — AI Analysis"
    )

    st.write(
        "CleanSight AI will analyze the photograph "
        "and create structured incident information."
    )

    st.warning(
        "AI-generated information may not always "
        "be accurate. You will review the result "
        "before submission."
    )

    image_col, result_col = st.columns(
        [1, 1]
    )

    with image_col:

        st.image(
            st.session_state.report_image_bytes,
            caption="Submitted photograph",
            use_container_width=True
        )

    with result_col:

        if st.session_state.ai_result is None:

            st.info(
                "The photograph has not "
                "been analyzed yet."
            )

            if st.button(
                "🤖 Analyze Photograph",
                type="primary",
                use_container_width=True,
                key="analyze_image"
            ):

                try:

                    with st.spinner(
                        "CleanSight AI is analyzing "
                        "the photograph..."
                    ):

                        result = (
                            analyze_waste_image(
                                st.session_state
                                .report_image_bytes
                            )
                        )

                    st.session_state.ai_result = (
                        result.model_dump()
                    )

                    priority_score, priority_level = (
                        calculate_priority(
                            result.hazard_score,
                            result.estimated_volume
                        )
                    )

                    st.session_state.priority_score = (
                        priority_score
                    )

                    st.session_state.priority_level = (
                        priority_level
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "AI analysis could not be completed."
                    )

                    st.exception(e)

        else:

            st.success(
                "✓ AI analysis completed."
            )

            display_ai_result(
                st.session_state.ai_result
            )

    st.divider()

    back_col, next_col = st.columns(2)

    with back_col:

        if st.button(
            "← Back to Location",
            use_container_width=True,
            key="analysis_back"
        ):

            st.session_state.report_step = 2

            st.rerun()

    with next_col:

        if st.button(
            "Continue to Review →",
            type="primary",
            use_container_width=True,
            key="analysis_next"
        ):

            if st.session_state.ai_result is None:

                st.error(
                    "Please complete the AI analysis first."
                )

            else:

                st.session_state.report_step = 4

                st.rerun()


# ============================================================
# STEP 4 - REVIEW
# ============================================================

def render_review_step():

    st.subheader(
        "Step 4 — Review Your Report"
    )

    st.warning(
        "Please review both your information "
        "and the AI-generated assessment carefully."
    )

    citizen_col, ai_col = st.columns(
        [1, 1]
    )

    with citizen_col:

        st.markdown(
            "### Your Information"
        )

        st.image(
            st.session_state.report_image_bytes,
            use_container_width=True
        )

        st.write(
            "**Location**"
        )

        st.write(
            st.session_state.location_address
        )

        st.write(
            "**Landmark / Nearby Place**"
        )

        st.write(
            st.session_state.location_landmark
            if st.session_state.location_landmark
            else "N/A"
        )

        if (
            st.session_state.location_lat
            is not None
            and
            st.session_state.location_lon
            is not None
        ):

            st.caption(
                f"{st.session_state.location_lat:.6f}, "
                f"{st.session_state.location_lon:.6f}"
            )

        st.write(
            "**Additional Description**"
        )

        st.write(
            st.session_state.citizen_description
            or
            "No additional description provided."
        )

    with ai_col:

        st.markdown(
            "### AI Assessment"
        )

        if st.session_state.ai_result:

            display_ai_result(
                st.session_state.ai_result
            )

        else:

            st.error(
                "AI assessment unavailable."
            )

    st.divider()

    back_col, confirm_col = st.columns(2)

    with back_col:

        if st.button(
            "← Back",
            use_container_width=True,
            key="review_back"
        ):

            st.session_state.report_step = 3

            st.rerun()

    with confirm_col:

        if st.button(
            "Confirm Report →",
            type="primary",
            use_container_width=True,
            key="review_confirm"
        ):

            if st.session_state.ai_result is None:

                st.error(
                    "AI analysis is required first."
                )

            else:

                st.session_state.report_step = 5

                st.rerun()


# ============================================================
# DUPLICATE REPORT DETECTION
# ============================================================

def haversine_distance_meters(
    lat1,
    lon1,
    lat2,
    lon2
):

    earth_radius_m = 6371000

    lat1_rad = math.radians(
        float(lat1)
    )

    lon1_rad = math.radians(
        float(lon1)
    )

    lat2_rad = math.radians(
        float(lat2)
    )

    lon2_rad = math.radians(
        float(lon2)
    )

    delta_lat = (
        lat2_rad - lat1_rad
    )

    delta_lon = (
        lon2_rad - lon1_rad
    )

    a = (
        math.sin(
            delta_lat / 2
        ) ** 2
        +
        math.cos(lat1_rad)
        *
        math.cos(lat2_rad)
        *
        math.sin(
            delta_lon / 2
        ) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius_m * c


def normalize_waste_type(value):

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
    )


def waste_types_are_similar(
    new_type,
    existing_type
):

    new_value = normalize_waste_type(
        new_type
    )

    old_value = normalize_waste_type(
        existing_type
    )

    if not new_value or not old_value:
        return False

    return (
        new_value == old_value
        or new_value in old_value
        or old_value in new_value
    )


def find_possible_duplicate():

    ai = st.session_state.ai_result

    if ai is None:
        return None

    latitude = (
        st.session_state.location_lat
    )

    longitude = (
        st.session_state.location_lon
    )

    if (
        latitude is None
        or longitude is None
    ):
        return None

    cutoff = (
        datetime.now()
        -
        timedelta(
            hours=DUPLICATE_LOOKBACK_HOURS
        )
    ).isoformat()

    response = (
        supabase
        .table("waste_reports")
        .select(
            "id,created_at,latitude,longitude,"
            "location_address,landmark,waste_type,"
            "status,priority,hazard_score"
        )
        .gte(
            "created_at",
            cutoff
        )
        .in_(
            "status",
            [
                "SUBMITTED",
                "REVIEWED"
            ]
        )
        .execute()
    )

    candidates = (
        response.data
        or []
    )

    best_match = None
    best_distance = None

    for report in candidates:

        existing_lat = report.get(
            "latitude"
        )

        existing_lon = report.get(
            "longitude"
        )

        if (
            existing_lat is None
            or existing_lon is None
        ):
            continue

        distance = (
            haversine_distance_meters(
                latitude,
                longitude,
                existing_lat,
                existing_lon
            )
        )

        if (
            distance
            >
            DUPLICATE_RADIUS_METERS
        ):
            continue

        if not waste_types_are_similar(
            ai.get("waste_type"),
            report.get("waste_type")
        ):
            continue

        if (
            best_distance is None
            or distance < best_distance
        ):

            best_distance = distance

            best_match = {
                **report,
                "distance_meters":
                    round(
                        distance
                    )
            }

    return best_match


def render_duplicate_warning():

    duplicate = (
        st.session_state
        .possible_duplicate
    )

    if not duplicate:
        return

    st.warning(
        "⚠️ A similar waste report may already "
        "exist near this location."
    )

    st.write(
        "A recent report with a similar waste type "
        "was found approximately "
        f"**{duplicate.get('distance_meters', '?')} m** away."
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Existing Report",
        (
            "#"
            +
            str(
                duplicate.get(
                    "id",
                    ""
                )
            )[:8]
        )
    )

    c2.metric(
        "Status",
        duplicate.get(
            "status",
            "Unknown"
        )
    )

    c3.metric(
        "Priority",
        duplicate.get(
            "priority",
            "Unknown"
        )
    )

    st.write(
        "**Waste Type:**",
        duplicate.get(
            "waste_type",
            "Unknown"
        )
    )

    st.write(
        "**Existing Location:**",
        duplicate.get(
            "location_address",
            "Unknown"
        )
    )

    landmark = duplicate.get(
        "landmark"
    )

    if landmark:

        st.write(
            "**Landmark:**",
            landmark
        )

    st.caption(
        "This is only a possible duplicate. "
        "If this is a different waste incident, "
        "you can still submit it. Municipal officers "
        "can review and group related reports later "
        "without deleting the original reports."
    )

    submit_col, cancel_col = (
        st.columns(2)
    )

    with submit_col:

        if st.button(
            "Submit Anyway",
            type="primary",
            use_container_width=True,
            key="duplicate_submit_anyway"
        ):

            st.session_state.duplicate_override = (
                True
            )

            try:

                with st.spinner(
                    "Submitting your report..."
                ):

                    submit_report(
                        skip_duplicate_check=True
                    )

                st.rerun()

            except Exception as e:

                st.error(
                    "The report could not be submitted."
                )

                st.exception(e)

    with cancel_col:

        if st.button(
            "Go Back",
            use_container_width=True,
            key="duplicate_go_back"
        ):

            st.session_state.possible_duplicate = (
                None
            )

            st.session_state.duplicate_check_completed = (
                False
            )

            st.session_state.duplicate_override = (
                False
            )

            st.session_state.report_step = (
                4
            )

            st.rerun()


# ============================================================
# SUBMIT REPORT
# ============================================================

def submit_report(
    skip_duplicate_check=False
):

    ai = st.session_state.ai_result

    if ai is None:

        raise ValueError(
            "AI analysis is missing."
        )

    # Check for a possible duplicate before uploading the
    # image or inserting a new database record.
    if (
        not skip_duplicate_check
        and
        not st.session_state.duplicate_override
    ):

        duplicate = (
            find_possible_duplicate()
        )

        st.session_state.duplicate_check_completed = (
            True
        )

        if duplicate is not None:

            st.session_state.possible_duplicate = (
                duplicate
            )

            return False

    image_path, image_url = (
        upload_report_image()
    )

    auth_user = st.session_state.get(
        "auth_user"
    )

    user_id = None

    if auth_user is not None:

        user_id = str(
            auth_user.id
        )

    report_data = {

        "user_id":
            user_id,

        "image_url":
            image_url,

        "location_address":
            st.session_state.location_address,

        "landmark":
            (
                st.session_state.location_landmark
                or None
            ),

        "latitude":
            st.session_state.location_lat,

        "longitude":
            st.session_state.location_lon,

        "citizen_description":
            st.session_state.citizen_description,

        "waste_type":
            ai["waste_type"],

        "ai_description":
            ai["description"],

        "estimated_volume":
            ai["estimated_volume"],

        "hazard_score":
            ai["hazard_score"],

        "visible_hazards":
            ai["visible_hazards"],

        "road_access":
            ai["road_access"],

        "recommended_vehicle":
            ai["recommended_vehicle"],

        "confidence":
            ai["confidence"],

        "priority_score":
            st.session_state.priority_score,

        "priority":
            st.session_state.priority_level,

        "status":
            "SUBMITTED",

        "created_at":
            datetime.now().isoformat()
    }

    saved_report = save_report(
        report_data
    )

    st.session_state.saved_report_id = (
        saved_report["id"]
    )

    st.session_state.report_submitted = (
        True
    )

    st.session_state.possible_duplicate = (
        None
    )

    st.session_state.duplicate_override = (
        False
    )

    return True


# ============================================================
# STEP 5 - SUBMIT
# ============================================================

def render_submit_step():

    st.subheader(
        "Step 5 — Submit Report"
    )

    if not st.session_state.report_submitted:

        if st.session_state.possible_duplicate:

            render_duplicate_warning()

            return

        st.success(
            "Your incident report is ready."
        )

        st.write(
            "Once submitted, it will be available "
            "for municipal review."
        )

        confirmation = st.checkbox(
            "I confirm that the information I provided "
            "is accurate to the best of my knowledge.",
            key="citizen_confirmation"
        )

        if st.button(
            "🚀 Submit Waste Report",
            type="primary",
            use_container_width=True,
            key="submit_report"
        ):

            if not confirmation:

                st.error(
                    "Please confirm the information first."
                )

            else:

                try:

                    with st.spinner(
                        "Checking for similar nearby reports..."
                    ):

                        submitted = (
                            submit_report()
                        )

                    # False means a possible duplicate was found.
                    # Rerun to show the duplicate warning.
                    if submitted is False:

                        st.rerun()

                    st.rerun()

                except Exception as e:

                    st.error(
                        "The report could not be submitted."
                    )

                    st.exception(e)

    else:

        st.success(
            "✓ Waste report submitted successfully!"
        )

        st.header(
            "Thank you for helping keep Sri Lanka clean."
        )

        if st.session_state.saved_report_id:

            st.info(
                "Incident Reference: "
                f"#{st.session_state.saved_report_id}"
            )

        st.write(
            "Your incident has been forwarded "
            "for municipal review."
        )

        c1, c2 = st.columns(2)

        with c1:

            if st.button(
                "♻️ Report Another Incident",
                type="primary",
                use_container_width=True,
                key="another_report"
            ):

                reset_report()

                st.rerun()

        with c2:

            if st.button(
                "Return Home",
                use_container_width=True,
                key="return_home"
            ):

                reset_report()

                st.session_state.citizen_started = False

                st.rerun()


# ============================================================
# MAIN CITIZEN VIEW
# ============================================================

def show_citizen_view():

    initialize_citizen_state()

    # ========================================================
    # AUTH ROUTING
    # ========================================================

    auth_page = st.session_state.get(
        "auth_page"
    )

    if auth_page == "signin":

        show_sign_in()
        return

    if auth_page == "signup":

        show_sign_up()
        return

    # ========================================================
    # PUBLIC LANDING
    # ========================================================

    if not st.session_state.citizen_started:

        render_landing()
        return

    # ========================================================
    # REPORT FLOW
    # ========================================================

    render_report_header()

    render_stepper()

    st.divider()

    current_step = (
        st.session_state.report_step
    )

    if current_step == 1:

        render_photo_step()

    elif current_step == 2:

        render_location_step()

    elif current_step == 3:

        render_analysis_step()

    elif current_step == 4:

        render_review_step()

    elif current_step == 5:

        render_submit_step()