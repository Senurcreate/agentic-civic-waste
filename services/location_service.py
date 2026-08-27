import re

from geopy.geocoders import Nominatim, ArcGIS, Photon
from geopy.exc import (
    GeocoderTimedOut,
    GeocoderServiceError,
    GeocoderUnavailable,
)


# ============================================================
# GEOCODERS
# ============================================================

nominatim = Nominatim(
    user_agent="cleansight_ai_application",
    timeout=10
)

arcgis = ArcGIS(
    timeout=10
)

photon = Photon(
    user_agent="cleansight_ai_application",
    timeout=10
)


# ============================================================
# ADDRESS CLEANING
# ============================================================

def normalize_address(address):

    text = (address or "").strip()

    # Collapse repeated spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    # Clean spaces around commas
    text = re.sub(
        r"\s*,\s*",
        ", ",
        text
    )

    # Everyday abbreviations
    replacements = {
        r"\brd\b": "Road",
        r"\bst\b": "Street",
        r"\bave\b": "Avenue",
        r"\bln\b": "Lane",
        r"\bjn\b": "Junction",
        r"\bmaw\b": "Mawatha",
    }

    for pattern, replacement in replacements.items():

        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE
        )

    # Common spelling variation in this area
    text = re.sub(
        r"\bjambugassmulla\b",
        "Jambugasmulla",
        text,
        flags=re.IGNORECASE
    )

    return text.strip(" ,")


# ============================================================
# HOUSE NUMBER HELPERS
# ============================================================

def looks_like_house_number(value):

    value = value.strip()

    return bool(
        re.fullmatch(
            r"(?i)(?:no\.?\s*)?\d+[a-z]?(?:[/\-]\w+)?",
            value
        )
    )


def remove_house_number(address):

    parts = [
        part.strip()
        for part in address.split(",")
        if part.strip()
    ]

    if (
        parts
        and
        looks_like_house_number(parts[0])
    ):
        parts = parts[1:]

    return ", ".join(parts)


# ============================================================
# BUILD FLEXIBLE SEARCH QUERIES
# ============================================================

def build_search_candidates(address):

    cleaned = normalize_address(
        address
    )

    without_house = remove_house_number(
        cleaned
    )

    parts = [
        part.strip()
        for part in without_house.split(",")
        if part.strip()
    ]

    candidates = []

    def add(query, precision):

        query = query.strip(" ,")

        if not query:
            return

        if "sri lanka" not in query.lower():
            query = f"{query}, Sri Lanka"

        if not any(
            old_query.lower() == query.lower()
            for old_query, _ in candidates
        ):
            candidates.append(
                (query, precision)
            )

    # Full address first
    add(cleaned, "exact")

    # Remove house number
    add(without_house, "road")

    # Road + each locality separately
    if parts:

        road = parts[0]

        for locality in parts[1:]:

            add(
                f"{road}, {locality}",
                "road"
            )

        # Road only
        add(
            road,
            "road"
        )

    # Try combinations of locality information
    if len(parts) >= 2:

        for index in range(
            1,
            len(parts)
        ):

            add(
                ", ".join(
                    parts[index:]
                ),
                "area"
            )

    # Every individual locality as final fallback
    for part in parts[1:]:

        add(
            part,
            "area"
        )

    return candidates


# ============================================================
# CONVERT GEOPY RESULT
# ============================================================

def result_to_dict(
    location,
    query,
    precision,
    provider
):

    if location is None:
        return None

    return {
        "address":
            location.address,

        "latitude":
            float(
                location.latitude
            ),

        "longitude":
            float(
                location.longitude
            ),

        "matched_query":
            query,

        "match_precision":
            precision,

        "provider":
            provider,
    }


# ============================================================
# TRY NOMINATIM
# ============================================================

def try_nominatim(
    query,
    precision
):

    try:

        location = nominatim.geocode(
            query,
            exactly_one=True,
            country_codes="lk",
            addressdetails=True,
            timeout=10
        )

        return result_to_dict(
            location,
            query,
            precision,
            "OpenStreetMap"
        )

    except (
        GeocoderTimedOut,
        GeocoderServiceError,
        GeocoderUnavailable
    ):

        return None


# ============================================================
# TRY ARCGIS
# ============================================================

def try_arcgis(
    query,
    precision
):

    try:

        location = arcgis.geocode(
            query,
            exactly_one=True,
            timeout=10
        )

        return result_to_dict(
            location,
            query,
            precision,
            "ArcGIS"
        )

    except (
        GeocoderTimedOut,
        GeocoderServiceError,
        GeocoderUnavailable
    ):

        return None


# ============================================================
# TRY PHOTON
# ============================================================

def try_photon(
    query,
    precision
):

    try:

        location = photon.geocode(
            query,
            exactly_one=True,
            timeout=10
        )

        return result_to_dict(
            location,
            query,
            precision,
            "Photon"
        )

    except (
        GeocoderTimedOut,
        GeocoderServiceError,
        GeocoderUnavailable
    ):

        return None


# ============================================================
# MAIN FORWARD GEOCODING FUNCTION
# ============================================================

def geocode_address(address):

    if not address or not address.strip():
        return None

    candidates = build_search_candidates(
        address
    )

    # First try OpenStreetMap for every candidate
    for query, precision in candidates:

        result = try_nominatim(
            query,
            precision
        )

        if result:
            return result

    # If OSM cannot resolve it, try ArcGIS
    for query, precision in candidates:

        result = try_arcgis(
            query,
            precision
        )

        if result:
            return result

    # Final fallback provider
    for query, precision in candidates:

        result = try_photon(
            query,
            precision
        )

        if result:
            return result

    return None


# ============================================================
# REVERSE GEOCODING
# ============================================================

def reverse_geocode(
    latitude,
    longitude
):

    # First try OpenStreetMap
    try:

        location = nominatim.reverse(
            (
                latitude,
                longitude
            ),
            exactly_one=True,
            language="en",
            timeout=10
        )

        if location is not None:
            return location.address

    except (
        GeocoderTimedOut,
        GeocoderServiceError,
        GeocoderUnavailable
    ):
        pass

    # ArcGIS fallback
    try:

        location = arcgis.reverse(
            (
                latitude,
                longitude
            ),
            exactly_one=True,
            timeout=10
        )

        if location is not None:
            return location.address

    except (
        GeocoderTimedOut,
        GeocoderServiceError,
        GeocoderUnavailable
    ):
        pass

    return (
        f"{latitude:.6f}, "
        f"{longitude:.6f}"
    )