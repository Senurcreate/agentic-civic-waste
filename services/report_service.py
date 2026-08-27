# ============================================================
# REPORT DATABASE SERVICE
# ============================================================

from datetime import datetime

from services.supabase_service import (
    supabase
)


TABLE_NAME = "waste_reports"


def save_report(
    report
):

    response = (
        supabase
        .table(TABLE_NAME)
        .insert(
            report
        )
        .execute()
    )


    if not response.data:

        raise Exception(
            "Report was not saved."
        )


    return response.data[0]