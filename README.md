<div align="center">

# ♻️ CleanSight AI

### AI-Assisted Civic Waste Reporting and Response System

**A smart civic reporting platform that helps citizens report waste incidents clearly and helps municipal officers review, prioritize, group, map, and manage those reports.**

<br>

`Python` · `Streamlit` · `Gemini` · `Supabase` · `PostgreSQL` · `Folium`

<br>

> **AI supports the decision-making process — the final municipal decision remains with the human officer.**

</div>

---

## ✨ Overview

CleanSight AI was designed to make civic waste reporting more structured, useful, and actionable.

Traditional waste complaints can be vague. A report may say *“garbage is dumped near the road”*, but municipal officers may still need to determine:

- what type of waste is present,
- how much waste is there,
- whether it is hazardous,
- whether the road is accessible,
- what vehicle may be suitable,
- how urgent the incident is,
- and whether multiple reports refer to the same incident.

CleanSight AI helps solve this by combining **citizen evidence, AI-assisted image analysis, location data, priority scoring, municipal review, related-report grouping, mapping, and export tools** in one workflow.

---

## 👤 Project Type

**Solo Project**

This project was designed and developed by a single developer.

### Developer 
**Role:** Designer & Developer  
**Project:** CleanSight AI

---

## 🎯 Main Goals

CleanSight AI aims to:

- improve the quality of civic waste reports,
- reduce manual interpretation of incomplete complaints,
- help municipal officers identify more urgent incidents,
- support human review instead of replacing it,
- reduce duplicate-report handling effort,
- and provide a simple reporting experience for citizens.

---

## 👥 Main Users

<table>
<tr>
<td width="50%" valign="top">

### 🧑 Citizen

Citizens can:

- report waste as a guest,
- create an account and sign in,
- upload a waste image,
- add a description,
- provide GPS or typed location details,
- add a landmark,
- run AI-assisted analysis,
- review the generated result,
- and submit the final report.

</td>
<td width="50%" valign="top">

### 🏢 Municipal Officer

Municipal officers can:

- sign in securely,
- access the dashboard,
- view reports on a map,
- search and filter incidents,
- review AI analysis,
- correct report details,
- add municipal notes,
- update report status,
- manage related reports,
- group incidents,
- and export report data.

</td>
</tr>
</table>

> Signed-in citizens use the same reporting interface as guest users in the current MVP.

---

## 🔄 Current Report Lifecycle

```text
Citizen submits report
        ↓
SUBMITTED
        ↓
Municipal officer reviews / confirms / corrects
        ↓
REVIEWED
```

### `SUBMITTED`

The citizen has completed and sent the report, but a municipal officer has not yet verified it.

### `REVIEWED`

A municipal officer has checked the report and confirmed or corrected the available information.

### Planned Future Workflow

```text
SUBMITTED
→ REVIEWED
→ ASSIGNED
→ IN PROGRESS
→ COMPLETED
```

---

## 🤖 AI-Assisted Waste Analysis

CleanSight AI uses **Google Gemini multimodal AI** to analyse the uploaded waste image.

The AI returns structured information such as:

| Field | Purpose |
|---|---|
| `waste_present` | Detects whether visible waste is present |
| `waste_type` | Identifies the likely waste category |
| `description` | Produces a short structured description |
| `estimated_volume` | Estimates the amount of waste |
| `hazard_score` | Estimates visible hazard severity |
| `visible_hazards` | Lists visible risk factors |
| `road_access` | Assesses whether the location appears accessible |
| `recommended_vehicle` | Suggests a suitable municipal vehicle |
| `confidence` | Shows the model-reported confidence |

### Example AI Output

```json
{
  "waste_present": true,
  "waste_type": "Mixed household waste",
  "description": "Waste bags and loose plastic are visible beside the road.",
  "estimated_volume": "Medium",
  "hazard_score": 5,
  "visible_hazards": [
    "Possible sharp objects"
  ],
  "road_access": "Accessible by small collection vehicle",
  "recommended_vehicle": "Small garbage collection truck",
  "confidence": 0.86
}
```

> The AI result is assistive. Municipal officers can review and correct the information.

---

## ⚡ Priority Calculation

The current priority score combines:

| Factor | Weight |
|---|---:|
| Hazard | **70%** |
| Estimated Volume | **30%** |

### Volume Scores

| Volume | Score |
|---|---:|
| Small | 30 |
| Medium | 60 |
| Large | 100 |

### Priority Levels

```text
Score >= 75  → HIGH
Score >= 45  → MEDIUM
Otherwise    → LOW
```

This gives greater importance to potentially hazardous incidents while still considering waste volume.

---

## 🔗 Related / Duplicate Report Handling

Duplicate handling is performed on the **municipal side**.

Citizens are not shown a *“Submit Anyway”* duplicate warning because this could discourage valid reporting.

Municipal officers can:

- identify nearby or potentially related reports,
- compare incidents,
- group related reports under the same incident group ID,
- mark reports as separate,
- and remove reports from a group when necessary.

Original reports are preserved.

> Current related-report detection mainly uses geographic proximity and a time window.

---

# 🏗️ System Architecture

CleanSight AI is divided into four main layers.

```text
┌──────────────────────────────────────────────┐
│              PRESENTATION TIER               │
│                                              │
│  Citizen Browser       Municipal Browser     │
└──────────────────────┬───────────────────────┘
                       │ HTTPS
                       ▼
┌──────────────────────────────────────────────┐
│              APPLICATION TIER                │
│                                              │
│             Streamlit Application            │
│                                              │
│ Citizen Module        Municipal Module       │
│ Authentication        Report Management      │
│ AI Integration        Location Services      │
│ Priority Logic        Grouping / Export      │
└───────────────┬───────────────────┬──────────┘
                │ HTTPS             │ HTTPS
                ▼                   ▼
┌──────────────────────────┐   ┌──────────────────────┐
│     BACKEND / DATA       │   │ THIRD-PARTY SERVICES │
│                          │   │                      │
│        Supabase          │   │ Gemini Multimodal   │
│                          │   │ Geocoding Service   │
│ Authentication           │   │                      │
│ PostgreSQL Database      │   └──────────────────────┘
│ Storage                  │
│ Row Level Security       │
└──────────────────────────┘
```

---

## 🖥️ Presentation Tier

The presentation tier is the part users interact with directly.

It includes:

- the **Citizen Web Interface**
- the **Municipal Dashboard**

Both are accessed through a web browser.

The browser communicates with the Streamlit application through **HTTPS requests**.

---

## ⚙️ Application Tier

The main application logic runs inside the **Streamlit application**.

It handles:

- citizen reporting,
- authentication routing,
- AI requests,
- location processing,
- priority calculation,
- municipal review,
- searching and filtering,
- related-report detection,
- grouping,
- mapping,
- and CSV export.

---

## 🗄️ Backend / Data Tier

CleanSight AI uses **Supabase** as its backend platform.

Supabase provides:

- authentication,
- PostgreSQL database,
- image storage,
- API access,
- and Row Level Security.

### Main Data Stored

The system stores information such as:

- report ID,
- citizen user ID when available,
- image URL,
- location,
- latitude and longitude,
- landmark,
- citizen description,
- AI-generated analysis,
- hazard score,
- priority,
- status,
- municipal notes,
- and incident group ID.

---

## 🌐 Third-Party Services

### Gemini Multimodal AI

The Streamlit application sends the uploaded waste image to Gemini using an HTTPS API request.

#### Data Sent

- waste image,
- structured analysis instructions.

#### Data Returned

- waste type,
- description,
- estimated volume,
- hazard score,
- visible hazards,
- road-access assessment,
- recommended vehicle,
- confidence.

---

### Location / Geocoding Service

The application also communicates with a geocoding service through HTTPS.

#### Data Sent

Depending on the selected location method:

- typed address, or
- latitude and longitude.

#### Data Returned

- geographic coordinates,
- or a readable address.

---

# 🔄 Main Data Flow

```text
Citizen opens CleanSight AI
        ↓
Uploads waste image
        ↓
Adds location / GPS / landmark
        ↓
Streamlit sends image to Gemini through HTTPS
        ↓
Gemini returns structured AI analysis
        ↓
CleanSight AI calculates priority
        ↓
Citizen reviews information
        ↓
Citizen submits report
        ↓
Report data is stored in Supabase
        ↓
Status = SUBMITTED
        ↓
Municipal officer retrieves report
        ↓
Officer reviews / corrects / adds notes
        ↓
Status = REVIEWED
```

---

# 🧰 Technology Stack

| Category | Technology |
|---|---|
| Web UI / Frontend | Streamlit |
| Application Logic | Python |
| AI / Computer Vision | Google Gemini Multimodal |
| Backend Platform | Supabase |
| Database | PostgreSQL |
| Authentication | Supabase Auth |
| Image Storage | Supabase Storage |
| Mapping | Folium |
| Streamlit Map Integration | streamlit-folium |
| Location / Geocoding | Geopy / Location Service |
| GPS Integration | Streamlit Geolocation |
| Structured AI Output | Pydantic |
| Data Processing | Pandas |
| Image Processing | Pillow |
| Deployment | Streamlit Community Cloud |
| Source Control | GitHub |

---

# 📁 Project Structure

```text
CleanSight-AI/
│
├── app.py
├── citizen_view.py
├── municipal_view.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── auth/
│   ├── __init__.py
│   ├── sign_in.py
│   └── sign_up.py
│
├── services/
│   ├── __init__.py
│   ├── supabase_service.py
│   ├── auth_service.py
│   ├── ai_service.py
│   ├── location_service.py
│   └── report_service.py
│
└── assets/
    └── cleansight_logo.png
```

---

# 🚀 Local Setup

## 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd CleanSight-AI
```

## 2. Create a Virtual Environment

### Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

## 4. Run the App

```powershell
python -m streamlit run app.py
```

If required on Windows:

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

---

# 📦 requirements.txt

Typical dependencies include:

```text
streamlit
supabase
google-genai
pydantic
Pillow
geopy
folium
streamlit-folium
streamlit-geolocation
pandas
toml
```

Only packages used by the final application should remain in the final file.

---

# 🔐 Streamlit Secrets

For local development, create:

```text
.streamlit/secrets.toml
```

Add:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"
```

Read the values in Python using:

```python
import streamlit as st

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
```

> ⚠️ Never commit `.streamlit/secrets.toml` or API keys to GitHub.

---

# 🙈 Recommended .gitignore

```gitignore
venv/
.venv/

__pycache__/
*.pyc
*.pyo

.streamlit/secrets.toml
secrets.toml

.env
.env.*

.DS_Store
Thumbs.db

.vscode/
.idea/
```

---

# 🗃️ Database Structure

## `waste_reports`

```sql
CREATE TABLE IF NOT EXISTS public.waste_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID NULL,
    image_url TEXT,
    location_address TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    landmark TEXT,
    citizen_description TEXT,
    waste_type TEXT,
    ai_description TEXT,
    estimated_volume TEXT,
    hazard_score INT,
    visible_hazards JSONB DEFAULT '[]'::jsonb,
    road_access TEXT,
    recommended_vehicle TEXT,
    confidence DOUBLE PRECISION,
    priority_score DOUBLE PRECISION,
    priority TEXT,
    status TEXT DEFAULT 'SUBMITTED',
    municipal_notes TEXT,
    incident_group_id UUID
);
```

## `profiles`

```sql
CREATE TABLE IF NOT EXISTS public.profiles (
    user_id UUID PRIMARY KEY
        REFERENCES auth.users(id)
        ON DELETE CASCADE,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'citizen'
        CHECK (role IN ('citizen', 'municipal')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## `report_duplicate_decisions`

```sql
CREATE TABLE IF NOT EXISTS public.report_duplicate_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL
        REFERENCES public.waste_reports(id)
        ON DELETE CASCADE,
    related_report_id UUID NOT NULL
        REFERENCES public.waste_reports(id)
        ON DELETE CASCADE,
    decision TEXT NOT NULL
        CHECK (decision IN ('GROUPED', 'SEPARATE')),
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(report_id, related_report_id),
    CHECK(report_id <> related_report_id)
);
```

---

# 🔑 Authentication Roles

The application currently supports:

```text
citizen
municipal
```

### Citizen

Citizens may sign up publicly.

### Municipal

Municipal accounts should be created through a controlled administrative process and assigned the `municipal` role.

---

# 📤 Municipal Export

The municipal dashboard supports CSV export for:

- all reports,
- current filtered view,
- submitted reports,
- reviewed reports,
- grouped reports,
- ungrouped reports,
- high-priority reports,
- and a specific incident group.

---

# 🧪 Testing

## Citizen Testing

Recommended tests include:

- guest reporting,
- sign-up,
- sign-in,
- logout,
- image upload,
- invalid image handling,
- GPS,
- typed location,
- landmark entry,
- AI analysis,
- review step,
- final submission,
- and required-field validation.

## Municipal Testing

Recommended tests include:

- municipal sign-in,
- dashboard loading,
- statistics,
- map,
- search,
- filters,
- pagination,
- report details,
- editing,
- municipal notes,
- status changes,
- related reports,
- grouping,
- separate decisions,
- ungrouping,
- CSV export,
- and logout.

## AI Validation

Representative waste images can be manually compared against:

- expected waste type,
- expected volume,
- visible hazards,
- hazard score,
- road-access recommendation,
- recommended vehicle,
- and AI confidence.

> Formal AI accuracy should only be claimed after a structured evaluation has actually been completed.

---

# ⚠️ Current Limitations

- AI output may be inaccurate or uncertain.
- Model confidence is not a calibrated probability.
- Sri Lankan address matching can be inconsistent.
- Geographic duplicate detection may produce false matches.
- Related-report detection currently depends mainly on location and time.
- The current lifecycle mainly uses `SUBMITTED` and `REVIEWED`.
- The MVP is not yet a complete municipal fleet-management platform.
- Production security and authorization policies require further hardening.

---

# 🛣️ Future Roadmap

## Short-Term Improvements

- stronger role security,
- formal AI evaluation,
- improved Sri Lankan location handling,
- image and text similarity for duplicate detection,
- expanded incident lifecycle,
- improved audit history.

## 🚛 AI-Assisted Collection Tracking

Future versions may include:

- municipal vehicle GPS,
- route-progress tracking,
- AI-assisted ETA prediction,
- delay detection,
- route-change detection,
- citizen collection-window notifications,
- updated ETA notifications,
- and learning from historical collection patterns.

## 🤖 Future AI Agent

A future AI agent could monitor:

- vehicle location,
- route progress,
- municipal workload,
- collection delays,
- incident priority,
- and report status.

The agent could assist with ETA updates and relevant notifications while municipal staff remain in control.

## Long-Term Ideas

- citizen report history,
- citizen status tracking,
- municipal team assignment,
- route optimization,
- waste hotspot analysis,
- municipal analytics,
- and collection performance reporting.

---

# 🌍 Deployment

The application can be deployed using **Streamlit Community Cloud**.

### Deployment Flow

```text
Local Project
    ↓
GitHub Repository
    ↓
Streamlit Community Cloud
    ↓
Public Application URL
```

### Required Streamlit Cloud Secrets

```toml
GEMINI_API_KEY = "your-real-key"
SUPABASE_URL = "your-real-supabase-url"
SUPABASE_KEY = "your-real-supabase-anon-key"
```

---

# 🛡️ Security Notes

Before production use:

- keep API keys out of GitHub,
- use HTTPS,
- configure Supabase Row Level Security,
- restrict municipal actions by role,
- store only necessary personal data,
- use the Supabase anon/publishable key,
- never expose the service-role key,
- review storage permissions,
- and keep AI-generated decisions subject to human verification.

---

# 📌 Disclaimer

CleanSight AI is an **AI-assisted civic reporting and municipal decision-support system**.

AI-generated output may contain errors and should not be treated as a verified municipal decision without human review.

The current version is an MVP and requires further security, usability, AI evaluation, and operational validation before real-world municipal deployment.

---

# 📄 License

This project is licensed under the **MIT License**.

You are free to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software, provided that the original copyright notice and license terms are included.

See the [`LICENSE`](LICENSE) file for the full license text.

---

<div align="center">

## ♻️ CleanSight AI

### Smarter reporting. Clearer municipal decisions. Cleaner communities.

**Solo-designed and developed project**

</div>
