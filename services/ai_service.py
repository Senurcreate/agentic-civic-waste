# ============================================================
# AI WASTE ANALYSIS SERVICE
# ============================================================

import io
import streamlit as st

from PIL import Image
from google import genai

from pydantic import (
    BaseModel,
    Field
)


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_API_KEY = str(
    st.secrets[
        "GEMINI_API_KEY"
    ]
).strip()


if not GEMINI_API_KEY:

    raise ValueError(
        "GEMINI_API_KEY is missing from Streamlit secrets."
    )


# Create Gemini client
client = genai.Client(
    api_key=GEMINI_API_KEY
)


# Gemini model used by CleanSight AI
GEMINI_MODEL = (
    "gemini-3.5-flash-lite"
)


# ============================================================
# STRUCTURED AI RESPONSE MODEL
# ============================================================

class WasteAnalysisResult(
    BaseModel
):

    # Whether waste is actually visible
    waste_present: bool

    # Main category of waste
    waste_type: str

    # Short factual AI description
    description: str

    # Small / Medium / Large
    estimated_volume: str

    # Hazard severity from 1 to 10
    hazard_score: int = Field(
        ge=1,
        le=10
    )

    # Visible risks detected in the image
    visible_hazards: list[str]

    # Narrow / Medium / Wide / Unknown
    road_access: str

    # Suggested municipal cleanup vehicle
    recommended_vehicle: str

    # Model-reported confidence from 0 to 1
    confidence: float = Field(
        ge=0,
        le=1
    )


# ============================================================
# GEMINI ANALYSIS PROMPT
# ============================================================

PROMPT = """
You are an AI assistant supporting a municipal
waste management system in Sri Lanka.

Analyze the uploaded photograph carefully.

Your role is to provide structured decision-support
information for a municipal waste officer.

Determine the following:

1. Whether unmanaged waste is visibly present.

2. The main visible waste type.

3. A brief factual description of the visible waste.

4. Estimated waste volume:
   - Small
   - Medium
   - Large

5. Hazard score from 1 to 10.

   1 means very low visible hazard.
   10 means extremely serious visible hazard.

6. Visible hazards.

   Examples may include:
   - sharp objects
   - broken glass
   - medical waste
   - chemical containers
   - burning waste
   - blocked drainage
   - exposed organic waste
   - other clearly visible hazards

7. Road accessibility:
   - Narrow
   - Medium
   - Wide
   - Unknown

8. Recommended cleanup vehicle.

   Suggest a reasonable municipal vehicle based only
   on the visible waste volume and apparent road access.

9. Overall confidence between 0 and 1.

IMPORTANT RULES:

- Base the analysis only on visible evidence.
- Do not invent information.
- Do not assume hazards that are not visible.
- Do not assume exact measurements.
- If something cannot reasonably be determined from
  the photograph, use "Unknown" where appropriate.
- Lower the confidence when the image is unclear,
  incomplete, distant, dark, obstructed, or ambiguous.
- The output will assist a municipal officer and must
  not be treated as a final municipal decision.
"""


# ============================================================
# IMAGE PREPARATION
# ============================================================

def prepare_image(
    image_bytes
):

    if not image_bytes:

        raise ValueError(
            "No image data was provided."
        )


    try:

        image = Image.open(
            io.BytesIO(
                image_bytes
            )
        )

        # Convert unsupported image modes to RGB
        if image.mode not in (
            "RGB",
            "RGBA"
        ):

            image = image.convert(
                "RGB"
            )

        return image


    except Exception as e:

        raise ValueError(
            "The uploaded file could not be opened "
            "as a valid image."
        ) from e


# ============================================================
# ANALYZE WASTE IMAGE
# ============================================================

def analyze_waste_image(
    image_bytes
):

    # --------------------------------------------------------
    # Prepare image
    # --------------------------------------------------------

    image = prepare_image(
        image_bytes
    )


    # --------------------------------------------------------
    # Send image + prompt to Gemini
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Validate Gemini response
    # --------------------------------------------------------

    if not response:

        raise ValueError(
            "Gemini returned no response."
        )


    if not response.text:

        raise ValueError(
            "Gemini returned an empty analysis."
        )


    # --------------------------------------------------------
    # Convert JSON response into Pydantic model
    # --------------------------------------------------------

    try:

        result = (
            WasteAnalysisResult
            .model_validate_json(
                response.text
            )
        )

    except Exception as e:

        raise ValueError(
            "Gemini returned an invalid "
            "structured response."
        ) from e


    # --------------------------------------------------------
    # Normalize values
    # --------------------------------------------------------

    result.waste_type = (
        result.waste_type.strip()
        if result.waste_type
        else "Unknown"
    )


    result.description = (
        result.description.strip()
        if result.description
        else "Unknown"
    )


    # Normalize volume
    volume = (
        result.estimated_volume
        .strip()
        .title()
        if result.estimated_volume
        else "Unknown"
    )


    if volume not in (
        "Small",
        "Medium",
        "Large"
    ):

        volume = "Unknown"


    result.estimated_volume = volume


    # Normalize road access
    road_access = (
        result.road_access
        .strip()
        .title()
        if result.road_access
        else "Unknown"
    )


    if road_access not in (
        "Narrow",
        "Medium",
        "Wide",
        "Unknown"
    ):

        road_access = "Unknown"


    result.road_access = (
        road_access
    )


    # Normalize recommended vehicle
    result.recommended_vehicle = (
        result.recommended_vehicle.strip()
        if result.recommended_vehicle
        else "Unknown"
    )


    # Remove blank hazard strings
    result.visible_hazards = [

        str(hazard).strip()

        for hazard
        in result.visible_hazards

        if str(hazard).strip()
    ]


    return result
