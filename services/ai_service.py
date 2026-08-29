# ============================================================
# AI WASTE ANALYSIS SERVICE
# ============================================================
import streamlit as st
import io


from PIL import Image
from google import genai

from pydantic import (
    BaseModel,
    Field
)


# ============================================================
# CONFIGURATION
# ============================================================


GEMINI_API_KEY = st.secrets[
    "GEMINI_API_KEY"
]


if not GEMINI_API_KEY:

    raise ValueError(
        "GEMINI_API_KEY missing from secrets.toml"
    )


client = genai.Client(
    api_key=GEMINI_API_KEY
)


GEMINI_MODEL = (
    "gemini-3.5-flash-lite"
)


# ============================================================
# RESPONSE MODEL
# ============================================================

class WasteAnalysisResult(BaseModel):

    waste_present: bool

    waste_type: str

    description: str

    estimated_volume: str

    hazard_score: int = Field(
        ge=1,
        le=10
    )

    visible_hazards: list[str]

    road_access: str

    recommended_vehicle: str

    confidence: float = Field(
        ge=0,
        le=1
    )


# ============================================================
# PROMPT
# ============================================================

PROMPT = """
You are an AI assistant supporting a municipal
waste management system in Sri Lanka.

Analyze the uploaded photograph carefully.

Determine:

1. Whether unmanaged waste is visible.

2. Main waste type.

3. Brief factual description.

4. Estimated volume:
   Small, Medium, or Large.

5. Hazard score between 1 and 10.

6. Visible hazards.

7. Road accessibility:
   Narrow, Medium, Wide, or Unknown.

8. Recommended cleanup vehicle.

9. Overall confidence between 0 and 1.

Do not invent information.

If an attribute cannot reasonably be determined
from the photograph, state Unknown where appropriate
or lower confidence.

Base the analysis only on visible evidence.
"""


# ============================================================
# ANALYZE
# ============================================================

def analyze_waste_image(
    image_bytes
):

    image = Image.open(
        io.BytesIO(
            image_bytes
        )
    )


    response = (
        client.models.generate_content(

            model=GEMINI_MODEL,

            contents=[
                PROMPT,
                image
            ],

            config={
                "response_mime_type":
                    "application/json",

                "response_schema":
                    WasteAnalysisResult
            }
        )
    )


    return (
        WasteAnalysisResult
        .model_validate_json(
            response.text
        )
    )
