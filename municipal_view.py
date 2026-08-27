# ============================================================
# CLEANSIGHT AI - MUNICIPAL VIEW
# VERSION: V6 - FIXED ACTION DROPDOWN STATE HANDLING
# ============================================================

import math
import uuid
import csv
import io
import pandas as pd
import streamlit as st
import folium
from datetime import datetime, timedelta

from streamlit_folium import st_folium
from services.supabase_service import supabase
from services.auth_service import sign_out_user


ROWS_PER_PAGE = 10

# Duplicate / related-report detection
DUPLICATE_RADIUS_METERS = 200
DUPLICATE_LOOKBACK_HOURS = 168


# ============================================================
# DATA ACCESS
# ============================================================

def load_reports():

    response = (
        supabase
        .table("waste_reports")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return response.data or []


def get_report_by_id(report_id):

    response = (
        supabase
        .table("waste_reports")
        .select("*")
        .eq("id", report_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def update_report_status(
    report_id,
    new_status
):
    """
    Update one report status and verify that Supabase
    actually returned the updated row.
    """

    response = (
        supabase
        .table("waste_reports")
        .update(
            {
                "status": new_status
            }
        )
        .eq(
            "id",
            report_id
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Supabase did not update the report. "
            "This is usually caused by an RLS UPDATE policy."
        )

    return response.data[0]


def update_report(
    report_id,
    changes
):

    return (
        supabase
        .table("waste_reports")
        .update(changes)
        .eq("id", report_id)
        .execute()
    )


def delete_report(
    report_id
):

    return (
        supabase
        .table("waste_reports")
        .delete()
        .eq("id", report_id)
        .execute()
    )


# ============================================================
# HELPERS
# ============================================================

def short_id(report_id):

    if not report_id:
        return "Unknown"

    return str(report_id)[:8]


def get_hazard_level(score):

    try:
        score = int(score)

    except (TypeError, ValueError):
        return "Unknown"

    if score >= 7:
        return "High"

    if score >= 4:
        return "Medium"

    return "Low"


def shorten_location(address):

    if not address:
        return "Unknown Location"

    parts = [
        part.strip()
        for part in str(address).split(",")
        if part.strip()
    ]

    return ", ".join(parts[:3])


def display_optional(value):

    if value is None:
        return "N/A"

    value = str(value).strip()

    if not value:
        return "N/A"

    return value


def get_landmark_display(report):
    """
    New reports use the dedicated landmark field.

    Older reports were created before the dedicated landmark
    column existed, so landmark/extra-location text may be inside
    citizen_description. For those records, show the legacy text
    clearly instead of pretending it is a newly structured landmark.
    """

    landmark = report.get("landmark")

    if landmark is not None and str(landmark).strip():
        return str(landmark).strip()

    legacy_details = report.get("citizen_description")

    if legacy_details is not None and str(legacy_details).strip():
        return f"{str(legacy_details).strip()} (legacy)"

    return "N/A"


def description_indicator(report):

    description = report.get("citizen_description")

    if description is not None and str(description).strip():
        return "📝 Available"

    return "N/A"


def format_date(value):

    if not value:
        return "Unknown"

    try:

        return (
            pd.to_datetime(value)
            .strftime(
                "%d %b %Y %I:%M %p"
            )
        )

    except Exception:

        return str(value)


def priority_rank(priority):

    return {
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3
    }.get(
        str(priority).upper(),
        4
    )


def format_confidence(confidence):

    if confidence is None:
        return "Unknown"

    try:

        value = float(confidence)

        # Current AI output is normally stored as 0.0 - 1.0.
        # If a future value is already stored as a percentage,
        # do not multiply it again.
        if value <= 1:
            value = value * 100

        return f"{value:.0f}%"

    except (TypeError, ValueError):

        return str(confidence)


def sort_reports(reports):

    return sorted(
        reports,
        key=lambda report: (
            # Keep grouped reports beside each other.
            0
            if report.get(
                "incident_group_id"
            )
            else 1,

            str(
                report.get(
                    "incident_group_id"
                )
                or
                ""
            ),

            priority_rank(
                report.get(
                    "priority"
                )
            ),

            str(
                report.get(
                    "created_at",
                    ""
                )
            )
        )
    )



# ============================================================
# DUPLICATE / RELATED REPORT HELPERS
# ============================================================

def haversine_distance_meters(
    lat1,
    lon1,
    lat2,
    lon2
):

    earth_radius_m = 6371000

    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
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
    first,
    second
):

    first_value = normalize_waste_type(first)
    second_value = normalize_waste_type(second)

    if not first_value or not second_value:
        return False

    return (
        first_value == second_value
        or first_value in second_value
        or second_value in first_value
    )


def load_duplicate_decisions():

    try:

        response = (
            supabase
            .table("report_duplicate_decisions")
            .select(
                "report_id,related_report_id,decision"
            )
            .execute()
        )

        return response.data or []

    except Exception:

        return []


def build_decision_lookup(decisions):

    lookup = {}

    for item in decisions:

        report_id = str(
            item.get("report_id", "")
        )

        related_id = str(
            item.get("related_report_id", "")
        )

        if not report_id or not related_id:
            continue

        lookup[
            (report_id, related_id)
        ] = str(
            item.get(
                "decision",
                ""
            )
        ).upper()

    return lookup


def save_duplicate_decision(
    report_id,
    related_report_id,
    decision
):

    rows = [
        {
            "report_id":
                report_id,

            "related_report_id":
                related_report_id,

            "decision":
                decision
        },
        {
            "report_id":
                related_report_id,

            "related_report_id":
                report_id,

            "decision":
                decision
        }
    ]

    return (
        supabase
        .table(
            "report_duplicate_decisions"
        )
        .upsert(
            rows,
            on_conflict=(
                "report_id,related_report_id"
            )
        )
        .execute()
    )


def format_group_label(group_id):

    if not group_id:
        return "—"

    return (
        "G-"
        +
        str(group_id)[:8].upper()
    )


def remove_report_from_group(
    report_id
):

    return (
        supabase
        .table("waste_reports")
        .update(
            {
                "incident_group_id":
                    None
            }
        )
        .eq(
            "id",
            report_id
        )
        .execute()
    )


def set_incident_group(
    report_ids,
    group_id=None
):

    report_ids = [
        str(report_id)
        for report_id in report_ids
        if report_id
    ]

    if not report_ids:
        return None

    if group_id is None:

        # Reuse an existing group if any selected report
        # already belongs to one.
        response = (
            supabase
            .table("waste_reports")
            .select(
                "id,incident_group_id"
            )
            .in_(
                "id",
                report_ids
            )
            .execute()
        )

        existing_groups = [
            row.get("incident_group_id")
            for row in (
                response.data
                or []
            )
            if row.get(
                "incident_group_id"
            )
        ]

        if existing_groups:
            group_id = existing_groups[0]

        else:
            group_id = str(
                uuid.uuid4()
            )

    (
        supabase
        .table("waste_reports")
        .update(
            {
                "incident_group_id":
                    group_id
            }
        )
        .in_(
            "id",
            report_ids
        )
        .execute()
    )

    return group_id


def get_group_members(
    report,
    all_reports
):

    group_id = report.get(
        "incident_group_id"
    )

    if not group_id:
        return []

    return [
        item
        for item in all_reports
        if (
            item.get(
                "incident_group_id"
            )
            == group_id
            and
            item.get("id")
            != report.get("id")
        )
    ]


def find_related_reports(
    report,
    all_reports,
    decision_lookup=None
):

    if decision_lookup is None:
        decision_lookup = {}

    report_id = str(
        report.get(
            "id",
            ""
        )
    )

    # Grouped members always remain related even if their
    # distance/time no longer matches the automatic rule.
    related = {
        str(item.get("id")):
            {
                **item,
                "relationship":
                    "GROUPED",
                "distance_meters":
                    (
                        round(
                            haversine_distance_meters(
                                report.get("latitude"),
                                report.get("longitude"),
                                item.get("latitude"),
                                item.get("longitude")
                            )
                        )
                        if (
                            report.get("latitude") is not None
                            and report.get("longitude") is not None
                            and item.get("latitude") is not None
                            and item.get("longitude") is not None
                        )
                        else None
                    )
            }
        for item in get_group_members(
            report,
            all_reports
        )
    }

    if (
        report.get("latitude") is None
        or report.get("longitude") is None
    ):
        return list(
            related.values()
        )

    try:

        created_at = pd.to_datetime(
            report.get("created_at"),
            utc=True
        )

    except Exception:

        created_at = None

    for item in all_reports:

        item_id = str(
            item.get(
                "id",
                ""
            )
        )

        if (
            not item_id
            or item_id == report_id
        ):
            continue

        decision = decision_lookup.get(
            (report_id, item_id)
        )

        if decision == "SEPARATE":
            continue

        if item_id in related:
            continue

        if (
            item.get("latitude") is None
            or item.get("longitude") is None
        ):
            continue

        distance = (
            haversine_distance_meters(
                report.get("latitude"),
                report.get("longitude"),
                item.get("latitude"),
                item.get("longitude")
            )
        )

        if distance > DUPLICATE_RADIUS_METERS:
            continue

        # Municipal view intentionally does NOT require the
        # same AI waste type. Nearby reports can still refer to
        # the same incident even when AI labels differ.
        # The officer makes the final decision.

        if created_at is not None:

            try:

                other_time = pd.to_datetime(
                    item.get("created_at"),
                    utc=True
                )

                difference_hours = abs(
                    (
                        created_at
                        -
                        other_time
                    ).total_seconds()
                ) / 3600

                if (
                    difference_hours
                    >
                    DUPLICATE_LOOKBACK_HOURS
                ):
                    continue

            except Exception:
                pass

        related[item_id] = {
            **item,
            "relationship":
                (
                    "GROUPED"
                    if decision
                    == "GROUPED"
                    else
                    "POSSIBLE"
                ),
            "distance_meters":
                round(distance)
        }

    return sorted(
        related.values(),
        key=lambda item: (
            0
            if item.get(
                "relationship"
            )
            == "GROUPED"
            else 1,
            item.get(
                "distance_meters"
            )
            if item.get(
                "distance_meters"
            )
            is not None
            else 999999
        )
    )


def duplicate_indicator(
    report,
    all_reports,
    decision_lookup
):

    related = find_related_reports(
        report,
        all_reports,
        decision_lookup
    )

    if not related:
        return "—"

    grouped_count = sum(
        1
        for item in related
        if item.get(
            "relationship"
        )
        == "GROUPED"
    )

    possible_count = (
        len(related)
        -
        grouped_count
    )

    if (
        grouped_count
        and possible_count
    ):

        return (
            f"🔗 {grouped_count} grouped / "
            f"⚠️ {possible_count} possible"
        )

    if grouped_count:

        return (
            f"🔗 {grouped_count} grouped"
        )

    return (
        f"⚠️ {possible_count} nearby"
    )


# ============================================================
# CSV EXPORT
# ============================================================

EXPORT_COLUMNS = [
    "id",
    "created_at",
    "status",
    "priority",
    "priority_score",
    "hazard_score",
    "waste_type",
    "estimated_volume",
    "location_address",
    "landmark",
    "latitude",
    "longitude",
    "citizen_description",
    "ai_description",
    "visible_hazards",
    "road_access",
    "recommended_vehicle",
    "confidence",
    "municipal_notes",
    "incident_group_id",
    "image_url"
]


def reports_to_csv(
    reports
):

    output = io.StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=EXPORT_COLUMNS,
        extrasaction="ignore"
    )

    writer.writeheader()

    for report in reports:

        row = dict(report)

        hazards = row.get(
            "visible_hazards"
        )

        if isinstance(
            hazards,
            list
        ):

            row["visible_hazards"] = (
                "; ".join(
                    str(item)
                    for item in hazards
                )
            )

        group_id = row.get(
            "incident_group_id"
        )

        if group_id:

            row["incident_group_id"] = (
                format_group_label(
                    group_id
                )
            )

        writer.writerow(
            {
                column:
                    row.get(
                        column,
                        ""
                    )
                for column
                in EXPORT_COLUMNS
            }
        )

    return output.getvalue()


def get_export_reports(
    reports,
    filtered_reports,
    export_scope,
    selected_group_id=None
):

    if export_scope == "Current Filtered View":

        return filtered_reports

    if export_scope == "Submitted Reports":

        return [
            report
            for report in reports
            if str(
                report.get(
                    "status",
                    ""
                )
            ).upper()
            == "SUBMITTED"
        ]

    if export_scope == "Reviewed Reports":

        return [
            report
            for report in reports
            if str(
                report.get(
                    "status",
                    ""
                )
            ).upper()
            == "REVIEWED"
        ]

    if export_scope == "Grouped Reports":

        return [
            report
            for report in reports
            if report.get(
                "incident_group_id"
            )
        ]

    if export_scope == "Ungrouped Reports":

        return [
            report
            for report in reports
            if not report.get(
                "incident_group_id"
            )
        ]

    if export_scope == "High Priority Reports":

        return [
            report
            for report in reports
            if str(
                report.get(
                    "priority",
                    ""
                )
            ).upper()
            == "HIGH"
        ]

    if (
        export_scope
        == "Specific Incident Group"
        and
        selected_group_id
    ):

        return [
            report
            for report in reports
            if str(
                report.get(
                    "incident_group_id"
                )
            )
            == str(
                selected_group_id
            )
        ]

    return reports


@st.dialog("Export Municipal Reports")
def render_export_dialog(
    reports,
    filtered_reports
):

    st.subheader(
        "📤 Export Reports"
    )

    st.caption(
        "Choose which municipal reports to export. "
        "The download is generated as a CSV file."
    )

    export_scope = st.selectbox(
        "Export",
        [
            "All Reports",
            "Current Filtered View",
            "Submitted Reports",
            "Reviewed Reports",
            "Grouped Reports",
            "Ungrouped Reports",
            "High Priority Reports",
            "Specific Incident Group"
        ],
        key="municipal_export_scope"
    )

    selected_group_id = None

    if (
        export_scope
        == "Specific Incident Group"
    ):

        group_ids = sorted(
            {
                str(
                    report.get(
                        "incident_group_id"
                    )
                )
                for report in reports
                if report.get(
                    "incident_group_id"
                )
            }
        )

        if group_ids:

            group_label_lookup = {
                format_group_label(
                    group_id
                ):
                    group_id
                for group_id
                in group_ids
            }

            selected_label = st.selectbox(
                "Incident Group",
                list(
                    group_label_lookup.keys()
                ),
                key="municipal_export_group"
            )

            selected_group_id = (
                group_label_lookup[
                    selected_label
                ]
            )

        else:

            st.info(
                "There are no grouped reports to export yet."
            )

    export_reports = (
        get_export_reports(
            reports,
            filtered_reports,
            export_scope,
            selected_group_id
        )
    )

    st.caption(
        f"{len(export_reports)} report(s) "
        "will be included in this export."
    )

    filename_part = (
        export_scope
        .lower()
        .replace(" ", "_")
    )

    if (
        export_scope
        == "Specific Incident Group"
        and
        selected_group_id
    ):

        filename_part = (
            "incident_group_"
            +
            format_group_label(
                selected_group_id
            )
            .lower()
            .replace("-", "_")
        )

    csv_data = (
        reports_to_csv(
            export_reports
        )
    )

    st.download_button(
        "⬇️ Download CSV",
        data=csv_data,
        file_name=(
            "cleansight_"
            f"{filename_part}.csv"
        ),
        mime="text/csv",
        use_container_width=True,
        disabled=(
            len(export_reports)
            == 0
        ),
        key="municipal_export_download"
    )


# ============================================================
# FILTERING
# ============================================================

def apply_filters(
    reports,
    search_text,
    priority_filter,
    hazard_filter,
    status_filter
):

    query = (
        search_text
        .strip()
        .lower()
    )

    filtered = []

    for report in reports:

        if query:

            searchable = " ".join(
                str(
                    report.get(
                        field,
                        ""
                    )
                )
                for field in [
                    "id",
                    "waste_type",
                    "location_address",
                    "landmark",
                    "municipal_notes",
                    "citizen_description",
                    "ai_description",
                    "priority",
                    "status",
                    "road_access",
                    "recommended_vehicle"
                ]
            ).lower()

            if query not in searchable:
                continue

        if (
            priority_filter != "All"
            and
            str(
                report.get(
                    "priority",
                    ""
                )
            ).upper()
            != priority_filter
        ):
            continue

        if (
            hazard_filter != "All"
            and
            get_hazard_level(
                report.get(
                    "hazard_score"
                )
            )
            != hazard_filter
        ):
            continue

        if (
            status_filter != "All"
            and
            str(
                report.get(
                    "status",
                    ""
                )
            ).upper()
            != status_filter
        ):
            continue

        filtered.append(
            report
        )

    return filtered


# ============================================================
# METRICS
# ============================================================

def render_metrics(reports):

    total = len(reports)

    high_priority = sum(
        1
        for report in reports
        if str(
            report.get(
                "priority",
                ""
            )
        ).upper()
        == "HIGH"
    )

    high_hazard = sum(
        1
        for report in reports
        if get_hazard_level(
            report.get(
                "hazard_score"
            )
        )
        == "High"
    )

    submitted = sum(
        1
        for report in reports
        if str(
            report.get(
                "status",
                ""
            )
        ).upper()
        == "SUBMITTED"
    )

    reviewed = sum(
        1
        for report in reports
        if str(
            report.get(
                "status",
                ""
            )
        ).upper()
        == "REVIEWED"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Total Reports", total)
    c2.metric("High Priority", high_priority)
    c3.metric("High Hazard", high_hazard)
    c4.metric("Submitted", submitted)
    c5.metric("Reviewed", reviewed)


# ============================================================
# ACTION DROPDOWN CALLBACK
# ============================================================

def on_row_action_change(
    report_id,
    action_key
):
    """
    Handle actions immediately when the dropdown changes.
    Status actions are written to Supabase directly here.
    Dialog actions are queued for the next rerun.
    """

    action = st.session_state.get(
        action_key,
        "Select action"
    )

    if action == "Select action":
        return

    # --------------------------------------------------------
    # REVIEWED - UPDATE DATABASE IMMEDIATELY
    # --------------------------------------------------------

    if action == "Reviewed":

        try:

            update_report_status(
                report_id,
                "REVIEWED"
            )

            st.session_state.municipal_notice = (
                f"Report #{short_id(report_id)} "
                f"updated to REVIEWED."
            )

        except Exception as e:

            st.session_state.municipal_error = (
                str(e)
            )

        # Safe inside callback
        st.session_state[action_key] = (
            "Select action"
        )

        return

    # --------------------------------------------------------
    # SUBMITTED - UPDATE DATABASE IMMEDIATELY
    # --------------------------------------------------------

    if action == "Submitted":

        try:

            update_report_status(
                report_id,
                "SUBMITTED"
            )

            st.session_state.municipal_notice = (
                f"Report #{short_id(report_id)} "
                f"updated to SUBMITTED."
            )

        except Exception as e:

            st.session_state.municipal_error = (
                str(e)
            )

        # Safe inside callback
        st.session_state[action_key] = (
            "Select action"
        )

        return

    # --------------------------------------------------------
    # OTHER ACTIONS
    # --------------------------------------------------------

    st.session_state.pending_municipal_action = {
        "report_id": report_id,
        "action": action
    }

    # Safe inside callback
    st.session_state[action_key] = (
        "Select action"
    )


# ============================================================
# DETAILS DIALOG
# ============================================================

@st.dialog(
    "Incident Details",
    width="large"
)
def show_details(report, all_reports=None, decision_lookup=None):

    st.caption(
        f"Report #{short_id(report.get('id'))}"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Priority",
        report.get(
            "priority",
            "Unknown"
        )
    )

    c2.metric(
        "Hazard",
        f"{report.get('hazard_score', '?')}/10"
    )

    c3.metric(
        "Volume",
        report.get(
            "estimated_volume",
            "Unknown"
        )
    )

    confidence = report.get(
        "confidence"
    )

    if confidence is None:

        confidence_text = "Unknown"

    else:

        try:

            confidence_text = (
                f"{float(confidence) * 100:.0f}%"
            )

        except Exception:

            confidence_text = str(
                confidence
            )

    c4.metric(
        "AI Confidence",
        confidence_text
    )

    st.divider()

    left, right = st.columns(
        [1, 1]
    )

    with left:

        st.markdown(
            "#### Photograph"
        )

        image_url = report.get(
            "image_url"
        )

        if image_url:

            st.image(
                image_url,
                use_container_width=True
            )

        else:

            st.info(
                "No photograph available."
            )

    with right:

        st.markdown(
            "#### Report Information"
        )

        st.write(
            "**Waste Type:**",
            report.get(
                "waste_type",
                "Unknown"
            )
        )

        st.write(
            "**Status:**",
            report.get(
                "status",
                "Unknown"
            )
        )

        st.write(
            "**Priority Score:**",
            report.get(
                "priority_score",
                "Unknown"
            )
        )

        st.write(
            "**Reported:**",
            format_date(
                report.get(
                    "created_at"
                )
            )
        )

    st.divider()

    st.markdown(
        "#### 📍 Location"
    )

    st.write(
        report.get(
            "location_address",
            "Unknown Location"
        )
    )

    st.write(
        "**Landmark / Nearby Place:**",
        get_landmark_display(
            report
        )
    )

    if (
        report.get("latitude") is not None
        and
        report.get("longitude") is not None
    ):

        st.caption(
            f"{report.get('latitude')}, "
            f"{report.get('longitude')}"
        )

    st.markdown(
        "#### 👤 Citizen Description"
    )

    st.write(
        report.get(
            "citizen_description"
        )
        or
        "No additional description provided."
    )

    st.divider()

    st.markdown(
        "#### 🤖 AI Assessment"
    )

    st.write(
        "**AI Description**"
    )

    st.write(
        report.get(
            "ai_description"
        )
        or
        "No AI description available."
    )

    a1, a2 = st.columns(2)

    with a1:

        st.write(
            "**Road Access**"
        )

        st.write(
            report.get(
                "road_access",
                "Unknown"
            )
        )

        st.write(
            "**Recommended Vehicle**"
        )

        st.write(
            report.get(
                "recommended_vehicle",
                "Unknown"
            )
        )

    with a2:

        st.write(
            "**Hazard Level**"
        )

        st.write(
            get_hazard_level(
                report.get(
                    "hazard_score"
                )
            )
        )

        st.write(
            "**Estimated Volume**"
        )

        st.write(
            report.get(
                "estimated_volume",
                "Unknown"
            )
        )

    st.write(
        "**Visible Hazards**"
    )

    hazards = (
        report.get(
            "visible_hazards"
        )
        or []
    )

    if (
        isinstance(
            hazards,
            list
        )
        and
        hazards
    ):

        for hazard in hazards:

            st.write(
                f"• {hazard}"
            )

    else:

        st.write(
            "No visible hazards identified."
        )

    st.divider()

    st.markdown(
        "#### 📝 Municipal Officer Notes"
    )

    st.write(
        display_optional(
            report.get(
                "municipal_notes"
            )
        )
    )



    # ========================================================
    # RELATED / DUPLICATE REPORTS
    # ========================================================

    if all_reports is not None:

        if decision_lookup is None:
            decision_lookup = {}

        related_reports = find_related_reports(
            report,
            all_reports,
            decision_lookup
        )

        st.divider()

        st.markdown(
            "#### 🔗 Related / Possible Duplicate Reports"
        )

        if not related_reports:

            st.write(
                "No related reports detected."
            )

        else:

            st.caption(
                "Nearby reports are automatically flagged when they are "
                "within 200 m and were reported within 7 days. "
                "They may be the same incident or separate waste piles. "
                "The municipal officer makes the final decision."
            )

            for related in related_reports:

                relationship = related.get(
                    "relationship",
                    "POSSIBLE"
                )

                if relationship == "GROUPED":
                    badge = "🔗 Grouped"
                else:
                    badge = "⚠️ Possible duplicate"

                distance = related.get(
                    "distance_meters"
                )

                distance_text = (
                    f"{distance} m away"
                    if distance is not None
                    else "Distance unavailable"
                )

                row1, row2, row3 = st.columns(
                    [2.2, 2.1, 1.25],
                    vertical_alignment="center"
                )

                with row1:

                    st.write(
                        f"**#{short_id(related.get('id'))}**"
                    )

                    st.caption(
                        (
                            f"{badge} • "
                            f"{distance_text}"
                        )
                    )

                with row2:

                    st.write(
                        related.get(
                            "waste_type",
                            "Unknown"
                        )
                    )

                    st.caption(
                        shorten_location(
                            related.get(
                                "location_address"
                            )
                        )
                    )

                with row3:

                    if st.button(
                        "View Report",
                        use_container_width=True,
                        key=(
                            "view_related_"
                            f"{report.get('id')}_"
                            f"{related.get('id')}"
                        )
                    ):

                        st.session_state.pending_municipal_action = {
                            "report_id":
                                related.get("id"),
                            "action":
                                "View Details"
                        }

                        st.rerun()



# ============================================================
# EDIT DIALOG
# ============================================================

@st.dialog(
    "Edit Incident",
    width="large"
)
def edit_dialog(report, all_reports=None, decision_lookup=None):

    report_id = report.get(
        "id"
    )

    st.caption(
        f"Report #{short_id(report_id)}"
    )

    st.info(
        "Municipal corrections represent "
        "human verification of the AI assessment."
    )

    waste_type = st.text_input(
        "Waste Type",
        value=str(
            report.get(
                "waste_type",
                ""
            )
            or
            ""
        ),
        key=f"edit_waste_{report_id}"
    )

    location_address = st.text_input(
        "Location",
        value=str(
            report.get(
                "location_address",
                ""
            )
            or
            ""
        ),
        key=f"edit_location_{report_id}"
    )

    landmark = st.text_input(
        "Landmark / Nearby Place",
        value=str(
            report.get(
                "landmark",
                ""
            )
            or
            ""
        ),
        placeholder=(
            "Example: Near Keells, bus stop, school gate"
        ),
        key=f"edit_landmark_{report_id}"
    )

    hazard_score = st.number_input(
        "Hazard Score",
        min_value=1,
        max_value=10,
        value=int(
            report.get(
                "hazard_score"
            )
            or
            1
        ),
        step=1,
        key=f"edit_hazard_{report_id}"
    )

    priority_options = [
        "HIGH",
        "MEDIUM",
        "LOW"
    ]

    current_priority = str(
        report.get(
            "priority",
            "LOW"
        )
    ).upper()

    if current_priority not in priority_options:
        current_priority = "LOW"

    priority = st.selectbox(
        "Priority",
        priority_options,
        index=priority_options.index(
            current_priority
        ),
        key=f"edit_priority_{report_id}"
    )

    road_access = st.text_input(
        "Road Access",
        value=str(
            report.get(
                "road_access",
                ""
            )
            or
            ""
        ),
        key=f"edit_road_{report_id}"
    )

    recommended_vehicle = st.text_input(
        "Recommended Vehicle",
        value=str(
            report.get(
                "recommended_vehicle",
                ""
            )
            or
            ""
        ),
        key=f"edit_vehicle_{report_id}"
    )

    municipal_notes = st.text_area(
        "Municipal Officer Notes",
        value=str(
            report.get(
                "municipal_notes",
                ""
            )
            or
            ""
        ),
        placeholder=(
            "Add verification notes, access instructions, "
            "observations, or follow-up information..."
        ),
        key=f"edit_notes_{report_id}"
    )

    # ========================================================
    # RELATED / DUPLICATE REPORTS INSIDE EDIT
    # ========================================================

    if all_reports is not None:

        if decision_lookup is None:
            decision_lookup = {}

        related_reports = find_related_reports(
            report,
            all_reports,
            decision_lookup
        )

        st.divider()

        st.markdown(
            "### 🔗 Related / Duplicate Reports"
        )

        current_group = report.get(
            "incident_group_id"
        )

        st.write(
            "**Current Group:**",
            format_group_label(
                current_group
            )
        )

        if related_reports:

            st.caption(
                "You can review, group, separate, "
                "or remove this report from a group."
            )

            selected_related = []

            for related in related_reports:

                relationship = related.get(
                    "relationship",
                    "POSSIBLE"
                )

                distance = related.get(
                    "distance_meters"
                )

                related_group = related.get(
                    "incident_group_id"
                )

                label = (
                    f"#{short_id(related.get('id'))} | "
                    f"{related.get('waste_type', 'Unknown')} | "
                    f"{distance if distance is not None else '?'} m | "
                    f"{relationship} | "
                    f"{format_group_label(related_group)}"
                )

                if st.checkbox(
                    label,
                    value=False,
                    key=(
                        "edit_dup_select_"
                        f"{report_id}_"
                        f"{related.get('id')}"
                    )
                ):

                    selected_related.append(
                        related.get("id")
                    )

            action_col1, action_col2 = (
                st.columns(2)
            )

            with action_col1:

                if st.button(
                    "🔗 Group Selected",
                    use_container_width=True,
                    disabled=(
                        len(
                            selected_related
                        )
                        == 0
                    ),
                    key=(
                        "edit_group_"
                        f"{report_id}"
                    )
                ):

                    try:

                        group_ids = [
                            report_id,
                            *selected_related
                        ]

                        group_id = (
                            set_incident_group(
                                group_ids,
                                current_group
                            )
                        )

                        for related_id in (
                            selected_related
                        ):

                            save_duplicate_decision(
                                report_id,
                                related_id,
                                "GROUPED"
                            )

                        st.session_state.municipal_notice = (
                            "Reports grouped under "
                            f"{format_group_label(group_id)}."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            "Could not group the selected reports."
                        )

                        st.exception(e)

            with action_col2:

                if st.button(
                    "Mark Selected as Separate",
                    use_container_width=True,
                    disabled=(
                        len(
                            selected_related
                        )
                        == 0
                    ),
                    key=(
                        "edit_separate_"
                        f"{report_id}"
                    )
                ):

                    try:

                        for related_id in (
                            selected_related
                        ):

                            save_duplicate_decision(
                                report_id,
                                related_id,
                                "SEPARATE"
                            )

                        st.session_state.municipal_notice = (
                            "Selected reports marked as separate."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            "Could not save the separate decision."
                        )

                        st.exception(e)

        else:

            st.info(
                "No nearby or grouped reports are currently linked."
            )

        if current_group:

            st.warning(
                "This report currently belongs to "
                f"{format_group_label(current_group)}."
            )

            if st.button(
                "Break This Report Out of Group",
                use_container_width=True,
                key=(
                    "edit_break_group_"
                    f"{report_id}"
                )
            ):

                try:

                    remove_report_from_group(
                        report_id
                    )

                    st.session_state.municipal_notice = (
                        "Report removed from its group."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Could not remove the report from its group."
                    )

                    st.exception(e)

    if st.button(
        "Save Changes",
        type="primary",
        use_container_width=True,
        key=f"save_edit_{report_id}"
    ):

        try:

            update_report(
                report_id,
                {
                    "waste_type":
                        waste_type,

                    "location_address":
                        location_address,

                    "landmark":
                        landmark.strip() or None,

                    "municipal_notes":
                        municipal_notes.strip() or None,

                    "hazard_score":
                        int(
                            hazard_score
                        ),

                    "priority":
                        priority,

                    "road_access":
                        road_access,

                    "recommended_vehicle":
                        recommended_vehicle,

                    "status":
                        "REVIEWED"
                }
            )

            st.session_state.municipal_notice = (
                "Report updated and marked as REVIEWED."
            )

            st.rerun()

        except Exception as e:

            st.error(
                "Could not update this report."
            )

            st.exception(e)


# ============================================================
# DELETE DIALOG
# ============================================================

@st.dialog(
    "Delete Incident"
)
def delete_dialog(report):

    report_id = report.get(
        "id"
    )

    st.error(
        "This permanently deletes the report."
    )

    confirm = st.checkbox(
        "I understand this report will be deleted permanently.",
        key=f"confirm_delete_{report_id}"
    )

    if st.button(
        "Delete Report",
        type="primary",
        use_container_width=True,
        disabled=not confirm,
        key=f"delete_{report_id}"
    ):

        try:

            delete_report(
                report_id
            )

            st.session_state.municipal_notice = (
                "Report deleted."
            )

            st.rerun()

        except Exception as e:

            st.error(
                "Could not delete this report."
            )

            st.exception(e)



# ============================================================
# DUPLICATE MANAGEMENT DIALOG
# ============================================================

@st.dialog(
    "Duplicate Management",
    width="large"
)
def duplicate_management_dialog(
    report,
    all_reports,
    decision_lookup
):

    related_reports = find_related_reports(
        report,
        all_reports,
        decision_lookup
    )

    st.caption(
        f"Report #{short_id(report.get('id'))}"
    )

    if not related_reports:

        st.info(
            "No related reports are currently detected."
        )

        return

    st.write(
        "Select nearby reports below, then either group them as "
        "the same operational incident or mark them as separate. "
        "Grouping keeps every original report and its own address, "
        "location, image and citizen information."
    )

    selected_ids = []

    for related in related_reports:

        relationship = related.get(
            "relationship",
            "POSSIBLE"
        )

        distance = related.get(
            "distance_meters"
        )

        label = (
            f"#{short_id(related.get('id'))} — "
            f"{related.get('waste_type', 'Unknown')} — "
            f"{distance if distance is not None else '?'} m — "
            f"{relationship}"
        )

        if st.checkbox(
            label,
            value=False,
            key=(
                "duplicate_select_"
                f"{report.get('id')}_"
                f"{related.get('id')}"
            )
        ):

            selected_ids.append(
                related.get("id")
            )

    st.divider()

    group_col, separate_col = st.columns(2)

    with group_col:

        if st.button(
            "🔗 Group Selected Reports",
            type="primary",
            use_container_width=True,
            disabled=(
                len(selected_ids) == 0
            ),
            key=(
                "group_selected_"
                f"{report.get('id')}"
            )
        ):

            try:

                group_ids = [
                    report.get("id"),
                    *selected_ids
                ]

                group_id = set_incident_group(
                    group_ids
                )

                for related_id in selected_ids:

                    save_duplicate_decision(
                        report.get("id"),
                        related_id,
                        "GROUPED"
                    )

                st.session_state.municipal_notice = (
                    f"{len(group_ids)} reports grouped "
                    f"under incident group "
                    f"{str(group_id)[:8]}."
                )

                st.rerun()

            except Exception as e:

                st.error(
                    "Could not group the selected reports."
                )

                st.exception(e)

    with separate_col:

        if st.button(
            "Mark Selected as Separate",
            use_container_width=True,
            disabled=(
                len(selected_ids) == 0
            ),
            key=(
                "separate_selected_"
                f"{report.get('id')}"
            )
        ):

            try:

                for related_id in selected_ids:

                    save_duplicate_decision(
                        report.get("id"),
                        related_id,
                        "SEPARATE"
                    )

                st.session_state.municipal_notice = (
                    "Selected reports marked as separate."
                )

                st.rerun()

            except Exception as e:

                st.error(
                    "Could not save the duplicate decision."
                )

                st.exception(e)



# ============================================================
# PROCESS PENDING ACTION
# ============================================================

def process_pending_action(all_reports, decision_lookup):

    pending = st.session_state.pop(
        "pending_municipal_action",
        None
    )

    if not pending:
        return

    report_id = pending.get(
        "report_id"
    )

    action = pending.get(
        "action"
    )

    if not report_id or not action:
        return

    report = get_report_by_id(
        report_id
    )

    if report is None:

        st.session_state.municipal_error = (
            "The selected report could not be found."
        )

        return

    if action == "View Details":

        show_details(
            report,
            all_reports,
            decision_lookup
        )

        return

    if action == "Duplicate Management":

        duplicate_management_dialog(
            report,
            all_reports,
            decision_lookup
        )

        return

    if action == "Edit":

        edit_dialog(
            report,
            all_reports,
            decision_lookup
        )

        return

    if action == "Delete":

        delete_dialog(
            report
        )

        return


# ============================================================
# PAGINATION
# ============================================================

def get_page_data(reports):

    total_reports = len(
        reports
    )

    total_pages = max(
        1,
        math.ceil(
            total_reports
            /
            ROWS_PER_PAGE
        )
    )

    if (
        "municipal_page"
        not in st.session_state
    ):

        st.session_state.municipal_page = (
            1
        )

    if (
        st.session_state.municipal_page
        >
        total_pages
    ):

        st.session_state.municipal_page = (
            total_pages
        )

    current_page = (
        st.session_state.municipal_page
    )

    start = (
        current_page - 1
    ) * ROWS_PER_PAGE

    end = (
        start
        +
        ROWS_PER_PAGE
    )

    return (
        reports[start:end],
        current_page,
        total_pages
    )


def render_pagination(
    current_page,
    total_pages,
    total_reports
):

    if total_pages <= 1:

        st.caption(
            f"Showing {total_reports} report(s)"
        )

        return

    c1, c2, c3 = st.columns(
        [1, 3, 1]
    )

    with c1:

        if st.button(
            "← Previous",
            use_container_width=True,
            disabled=(
                current_page <= 1
            ),
            key="previous_page"
        ):

            st.session_state.municipal_page -= 1

            st.rerun()

    with c2:

        start_item = (
            (current_page - 1)
            *
            ROWS_PER_PAGE
            +
            1
        )

        end_item = min(
            current_page
            *
            ROWS_PER_PAGE,
            total_reports
        )

        st.markdown(
            (
                "<div style='text-align:center;"
                "padding-top:8px;'>"
                f"Page <b>{current_page}</b> "
                f"of <b>{total_pages}</b>"
                f"<br><small>"
                f"Showing {start_item}–{end_item} "
                f"of {total_reports}"
                f"</small>"
                "</div>"
            ),
            unsafe_allow_html=True
        )

    with c3:

        if st.button(
            "Next →",
            use_container_width=True,
            disabled=(
                current_page >= total_pages
            ),
            key="next_page"
        ):

            st.session_state.municipal_page += 1

            st.rerun()


# ============================================================
# TABLE WITH ACTION DROPDOWN
# ============================================================

def render_table(reports, all_reports, decision_lookup):

    st.subheader(
        "📋 Incident Table"
    )

    grouped_reports = [
        report
        for report in reports
        if report.get(
            "incident_group_id"
        )
    ]

    group_ids = sorted(
        {
            report.get(
                "incident_group_id"
            )
            for report in grouped_reports
        }
    )

    if group_ids:

        st.markdown(
            "#### 🔗 Incident Groups"
        )

        group_columns = st.columns(
            min(
                4,
                len(group_ids)
            )
        )

        for index, group_id in enumerate(
            group_ids
        ):

            members = [
                report
                for report in reports
                if report.get(
                    "incident_group_id"
                )
                == group_id
            ]

            with group_columns[
                index
                %
                len(group_columns)
            ]:

                st.metric(
                    format_group_label(
                        group_id
                    ),
                    f"{len(members)} reports"
                )

        st.caption(
            "Reports sharing the same Group ID belong "
            "to the same confirmed operational incident."
        )

        st.divider()

    if not reports:

        st.info(
            "No reports match the selected filters."
        )

        return

    reports = sort_reports(
        reports
    )

    (
        page_reports,
        current_page,
        total_pages
    ) = get_page_data(
        reports
    )

    st.caption(
        "Select an action directly from the row. "
        "Reviewed or Submitted updates the "
        "database and table immediately."
    )

    header = st.columns(
        [
            0.72,
            0.62,
            0.74,
            0.95,
            1.25,
            1.05,
            0.9,
            0.68,
            0.9,
            1.15,
            0.78,
            1.15
        ]
    )

    headings = [
        "Report ID",
        "Priority",
        "Hazard",
        "Waste Type",
        "Location",
        "Landmark",
        "Description",
        "Confidence",
        "Group",
        "Related",
        "Status",
        "Actions"
    ]

    for col, heading in zip(
        header,
        headings
    ):

        with col:

            st.markdown(
                f"**{heading}**"
            )

    st.divider()

    for row_number, report in enumerate(
        page_reports
    ):

        report_id = (
            report.get(
                "id"
            )
        )

        cols = st.columns(
            [
                0.72,
                0.62,
                0.74,
                0.95,
                1.25,
                1.05,
                0.9,
                0.68,
                0.9,
                1.15,
                0.78,
                1.15
            ],
            vertical_alignment="center"
        )

        with cols[0]:

            st.write(
                f"#{short_id(report_id)}"
            )

        with cols[1]:

            st.write(
                report.get(
                    "priority",
                    "Unknown"
                )
            )

        with cols[2]:

            st.write(
                (
                    f"{get_hazard_level(report.get('hazard_score'))} "
                    f"({report.get('hazard_score', '?')}/10)"
                )
            )

        with cols[3]:

            st.write(
                report.get(
                    "waste_type",
                    "Unknown"
                )
            )

        with cols[4]:

            st.write(
                shorten_location(
                    report.get(
                        "location_address"
                    )
                )
            )

        with cols[5]:

            st.write(
                get_landmark_display(
                    report
                )
            )

        with cols[6]:

            st.write(
                description_indicator(
                    report
                )
            )

        with cols[7]:

            st.write(
                format_confidence(
                    report.get(
                        "confidence"
                    )
                )
            )

        with cols[8]:

            st.write(
                format_group_label(
                    report.get(
                        "incident_group_id"
                    )
                )
            )

        with cols[9]:

            st.write(
                duplicate_indicator(
                    report,
                    all_reports,
                    decision_lookup
                )
            )

        with cols[10]:

            current_status = str(
                report.get(
                    "status",
                    "SUBMITTED"
                )
            ).upper()

            if current_status == "REVIEWED":

                st.success(
                    "REVIEWED"
                )

            elif current_status == "SUBMITTED":

                st.info(
                    "SUBMITTED"
                )

            else:

                st.write(
                    current_status
                )

        with cols[11]:

            action_key = (
                f"action_"
                f"{current_page}_"
                f"{report_id}"
            )

            st.selectbox(
                "Actions",
                [
                    "Select action",
                    "View Details",
                    "Duplicate Management",
                    "Reviewed",
                    "Submitted",
                    "Edit",
                    "Delete"
                ],
                key=action_key,
                label_visibility="collapsed",
                on_change=on_row_action_change,
                args=(
                    report_id,
                    action_key
                )
            )

        if (
            row_number
            <
            len(page_reports)
            -
            1
        ):

            st.markdown(
                "<hr style='margin:0.25rem 0;'>",
                unsafe_allow_html=True
            )

    st.divider()

    render_pagination(
        current_page,
        total_pages,
        len(reports)
    )


# ============================================================
# MAP
# ============================================================

def render_map(reports):

    st.subheader(
        "Incident Map"
    )

    valid_reports = [
        report
        for report in reports
        if (
            report.get(
                "latitude"
            )
            is not None
            and
            report.get(
                "longitude"
            )
            is not None
        )
    ]

    if not valid_reports:

        st.info(
            "No mapped incidents match "
            "the selected filters."
        )

        return

    first = (
        valid_reports[0]
    )

    incident_map = folium.Map(
        location=[
            float(
                first[
                    "latitude"
                ]
            ),
            float(
                first[
                    "longitude"
                ]
            )
        ],
        zoom_start=12
    )

    for report in valid_reports:

        priority = str(
            report.get(
                "priority",
                "LOW"
            )
        ).upper()

        if priority == "HIGH":

            marker_color = "red"

        elif priority == "MEDIUM":

            marker_color = "orange"

        else:

            marker_color = "green"

        popup = (
            f"<b>Report:</b> "
            f"#{short_id(report.get('id'))}<br>"
            f"<b>Priority:</b> "
            f"{priority}<br>"
            f"<b>Hazard:</b> "
            f"{report.get('hazard_score', '?')}/10<br>"
            f"<b>Status:</b> "
            f"{report.get('status', 'Unknown')}<br>"
            f"<b>Waste:</b> "
            f"{report.get('waste_type', 'Unknown')}<br>"
            f"<b>Location:</b> "
            f"{shorten_location(report.get('location_address'))}"
        )

        folium.Marker(
            [
                float(
                    report[
                        "latitude"
                    ]
                ),
                float(
                    report[
                        "longitude"
                    ]
                )
            ],
            tooltip=(
                f"{priority} | "
                f"{report.get('waste_type', 'Incident')}"
            ),
            popup=popup,
            icon=folium.Icon(
                color=marker_color
            )
        ).add_to(
            incident_map
        )

    st_folium(
        incident_map,
        height=500,
        use_container_width=True,
        key="municipal_map"
    )


# ============================================================
# LOGOUT CONFIRMATION
# ============================================================

@st.dialog("Confirm Log Out")
def confirm_municipal_logout():

    st.write(
        "Do you want to log out of the municipal dashboard?"
    )

    cancel_col, logout_col = st.columns(2)

    with cancel_col:

        if st.button(
            "Cancel",
            use_container_width=True,
            key="municipal_logout_cancel"
        ):

            st.rerun()

    with logout_col:

        if st.button(
            "Yes, Log Out",
            type="primary",
            use_container_width=True,
            key="municipal_logout_confirm"
        ):

            try:

                sign_out_user()

            except Exception:

                pass

            for key in [
                "auth_user",
                "user_role",
                "app_view",
                "auth_page",
                "pending_municipal_action",
                "municipal_notice",
                "municipal_error"
            ]:

                st.session_state.pop(
                    key,
                    None
                )

            st.session_state.app_view = "Citizen"
            st.session_state.auth_page = None

            st.rerun()


# ============================================================
# MAIN MUNICIPAL VIEW
# ============================================================

def show_municipal_view():

    # ========================================================
    # HEADER + LOGOUT
    # ========================================================

    # ============================================================
# MUNICIPAL HEADER
# ============================================================

    title_col, export_col, logout_col = st.columns(
        [7.2, 1.6, 1.4],
        vertical_alignment="center"
    )

    with title_col:

        logo_col, text_col = st.columns(
            [1.2, 4.8],
            vertical_alignment="center"
        )

        with logo_col:

            st.image(
                "assets/cleansight_logo.png",
                width=130
            )

        with text_col:

            st.title(
                "Municipal Dashboard"
            )

           


    with export_col:

        if st.button(
            "📤 Export",
            use_container_width=True,
            key="municipal_export_header"
        ):

            st.session_state.open_export_dialog = True


    with logout_col:

        if st.button(
            "Log Out",
            use_container_width=True,
            key="municipal_logout"
        ):

            confirm_municipal_logout()
    # ========================================================
    # MESSAGE
    # ========================================================

    notice = st.session_state.pop(
        "municipal_notice",
        None
    )

    if notice:

        st.success(
            notice
        )

    error_message = st.session_state.pop(
        "municipal_error",
        None
    )

    if error_message:

        st.error(
            error_message
        )

    # ========================================================
    # LOAD LIVE DATA
    # ========================================================

    try:

        reports = (
            load_reports()
        )

    except Exception as e:

        st.error(
            "Could not load municipal reports."
        )

        st.exception(e)

        return

    if not reports:

        st.info(
            "No waste reports have been submitted yet."
        )

        return

    duplicate_decisions = (
        load_duplicate_decisions()
    )

    decision_lookup = (
        build_decision_lookup(
            duplicate_decisions
        )
    )

    # Process any table/dialog action only after the live
    # reports and duplicate decisions are available.
    process_pending_action(
        reports,
        decision_lookup
    )

    # ========================================================
    # METRICS
    # ========================================================

    render_metrics(
        reports
    )

    st.divider()

    # ========================================================
    # SEARCH & FILTERS
    # ========================================================

    st.subheader(
        "Search & Filters"
    )

    search_text = st.text_input(
        "Search reports",
        placeholder=(
            "Search location, waste type, "
            "description or report ID..."
        ),
        key="municipal_search"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        priority_filter = st.selectbox(
            "Priority",
            [
                "All",
                "HIGH",
                "MEDIUM",
                "LOW"
            ],
            key="priority_filter"
        )

    with c2:

        hazard_filter = st.selectbox(
            "Hazard Level",
            [
                "All",
                "High",
                "Medium",
                "Low"
            ],
            key="hazard_filter"
        )

    with c3:

        status_filter = st.selectbox(
            "Municipal Status",
            [
                "All",
                "SUBMITTED",
                "REVIEWED"
            ],
            key="status_filter"
        )

    filter_signature = (
        search_text,
        priority_filter,
        hazard_filter,
        status_filter
    )

    if (
        st.session_state.get(
            "last_filter_signature"
        )
        != filter_signature
    ):

        st.session_state.last_filter_signature = (
            filter_signature
        )

        st.session_state.municipal_page = 1

    filtered_reports = apply_filters(
        reports,
        search_text,
        priority_filter,
        hazard_filter,
        status_filter
    )

    st.caption(
        f"Showing {len(filtered_reports)} "
        f"of {len(reports)} reports"
    )

    if st.session_state.pop(
        "open_export_dialog",
        False
    ):

        render_export_dialog(
            reports,
            filtered_reports
        )

    st.divider()

    # ========================================================
    # TABLE
    # ========================================================

    render_table(
        filtered_reports,
        reports,
        decision_lookup
    )

    st.divider()

    # ========================================================
    # MAP
    # ========================================================

    render_map(
        filtered_reports
    )
