<div align="center">

# ♻️ CleanSight AI

### AI-Assisted Civic Waste Reporting and Response System

**A smart civic reporting platform that helps citizens report waste incidents and helps municipal officers review, prioritize, group, map, and manage reports.**

`Python` · `Streamlit` · `Gemini` · `Supabase` · `PostgreSQL` · `Folium`

> **AI supports decision-making. Final municipal decisions remain with human officers.**

</div>

---

## ✨ Overview

CleanSight AI improves the way civic waste incidents are reported and reviewed.

Citizens can upload an image, provide a description and location, and receive AI-assisted analysis before submitting the report.

Municipal officers can then review reports, correct AI-generated information, identify priority incidents, manage related reports, view incidents on a map, and export report data.

---

## 🚀 Key Features

### 🧑 Citizen

* Report waste as a guest or signed-in user
* Upload waste images
* Add a simple everyday address
* Use GPS/current location
* Add landmarks and descriptions
* Run AI-assisted waste analysis
* Review the generated analysis
* Submit reports to the municipality

### 🏢 Municipal Officer

* Secure municipal sign-in
* Dashboard with submitted reports
* Search and filtering
* Interactive report map
* Review AI-generated analysis
* Correct report information
* Add municipal notes
* Update report status
* Detect and group related reports
* Export report data as CSV

---

## 🤖 AI-Assisted Analysis

CleanSight AI uses **Google Gemini multimodal AI** to analyse uploaded waste images.

The analysis can include:

* waste type
* estimated waste volume
* visible hazards
* hazard score
* road accessibility
* recommended collection vehicle
* AI confidence

The AI output is treated as **decision support**, not as a final municipal decision.

---

## ⚡ Priority Calculation

The current priority score considers:

| Factor       | Weight |
| ------------ | -----: |
| Hazard       |    70% |
| Waste Volume |    30% |

Priority levels:

```text
Score >= 75  → HIGH
Score >= 45  → MEDIUM
Otherwise    → LOW
```

---

## 🔗 Related Report Handling

Potentially related or duplicate reports are handled on the **municipal side**.

Municipal officers can:

* compare nearby reports
* group reports belonging to the same incident
* mark reports as separate
* remove reports from an existing group

Original citizen reports are always preserved.

---

# 📸 Screenshots

Click a section below to view its screenshots.

<details>
<summary><strong>🏠 Landing Page</strong></summary>

<br>

<img width="1366" height="678" alt="CleanSight-AI-·-Streamlit (12)" src="https://github.com/user-attachments/assets/64e2bb19-4379-4c01-8b49-cfa5e2a304df" />

</details>

<details>
<summary><strong>🧑 Citizen Reporting</strong></summary>

<br>

### Upload Waste Image

<img width="1366" height="2157" alt="CleanSight-AI-·-Streamlit (1)" src="https://github.com/user-attachments/assets/c2d05404-8a9e-4a76-88c4-bf3417484c96" />

### Location

<img width="1366" height="2209" alt="CleanSight-AI-·-Streamlit (4)" src="https://github.com/user-attachments/assets/7afbfe19-728e-44df-8823-c0888d16884e" />

### AI Analysis
<img width="1366" height="1440" alt="CleanSight-AI-·-Streamlit (5)" src="https://github.com/user-attachments/assets/13b0fcb6-e013-47aa-a8e7-29225f9b33f1" />

<img width="1366" height="1538" alt="CleanSight-AI-·-Streamlit (7)" src="https://github.com/user-attachments/assets/624230aa-0c4c-40bf-a4d4-d35c158cadd1" />


### Review & Submit

<img width="1366" height="1716" alt="CleanSight-AI-·-Streamlit (8)" src="https://github.com/user-attachments/assets/7ba105e8-eb7d-484b-bd0f-2cddb3ad9ef3" />
<img width="1366" height="778" alt="CleanSight-AI-·-Streamlit (9)" src="https://github.com/user-attachments/assets/2b87aca2-b289-4ca5-b4ad-d189345eaff5" />
<img width="1366" height="885" alt="CleanSight-AI-·-Streamlit (10)" src="https://github.com/user-attachments/assets/9e7a3ab0-6851-404f-8296-02f67e2d96a8" />



</details>

<details>
<summary><strong>🏢 Municipal Dashboard</strong></summary>

<br>

### Dashboard

<img width="1366" height="2413" alt="CleanSight-AI-·-Streamlit (11)" src="https://github.com/user-attachments/assets/dbd01a8a-78ee-4957-86c9-29c5f1670765" />



</details>

<details>
<summary><strong>🔐 Authentication</strong></summary>

<br>

### Sign In

<img width="1366" height="679" alt="CleanSight-AI-·-Streamlit (13)" src="https://github.com/user-attachments/assets/d303e5c7-e8d6-4b22-aabb-518b31780afe" />

### Sign Up

<img width="1366" height="1171" alt="CleanSight-AI-·-Streamlit (14)" src="https://github.com/user-attachments/assets/3ffe06f8-ba0e-47ba-bc12-ed69a7b91e1b" />

</details>

---

# 🔑 Demo Access

## Citizen

Citizens can use the guest reporting option or create an account through the application.

## Municipal Officer

Use the following account to access the municipal demonstration dashboard.

```text
Municipal Email:    municipal2@example.com
Password:           municipal123
```

---

# 🏗️ Architecture

```text
Citizen / Municipal Browser
            │
            ▼
      Streamlit App
       /         \
      ▼           ▼
  Supabase      Gemini
 Auth / DB      Multimodal AI
 Storage
      │
      ▼
 PostgreSQL
```

### Main Flow

```text
Citizen uploads report
        ↓
AI analyses waste image
        ↓
CleanSight AI calculates priority
        ↓
Citizen reviews and submits
        ↓
Report stored in Supabase
        ↓
Municipal officer reviews
        ↓
Officer confirms or corrects report
```

Current report lifecycle:

```text
SUBMITTED → REVIEWED
```

Future versions may extend this to:

```text
SUBMITTED → REVIEWED → ASSIGNED → IN PROGRESS → COMPLETED
```

---

# 🧰 Technology Stack

| Area                 | Technology                |
| -------------------- | ------------------------- |
| Web Application      | Streamlit                 |
| Programming Language | Python                    |
| AI                   | Google Gemini Multimodal  |
| Backend              | Supabase                  |
| Database             | PostgreSQL                |
| Authentication       | Supabase Auth             |
| Storage              | Supabase Storage          |
| Mapping              | Folium                    |
| Geocoding            | Geopy                     |
| Data Processing      | Pandas                    |
| Image Processing     | Pillow                    |
| Deployment           | Streamlit Community Cloud |
| Source Control       | GitHub                    |

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
│   ├── sign_in.py
│   └── sign_up.py
│
├── services/
│   ├── supabase_service.py
│   ├── auth_service.py
│   ├── ai_service.py
│   ├── location_service.py
│   └── report_service.py
│
├── assets/
│   └── cleansight_logo.png
│
└── docs/
    └── screenshots/
```

---

# 🚀 Local Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd CleanSight-AI
```

### 2. Create a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Add Streamlit secrets

Create:

```text
.streamlit/secrets.toml
```

Add:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"
```

### 5. Run CleanSight AI

```powershell
python -m streamlit run app.py
```

---

# 🔐 Security

Never commit API keys, passwords, `.env` files, or Streamlit secrets to GitHub.

Recommended `.gitignore`:

```gitignore
venv/
.venv/

__pycache__/
*.pyc

.streamlit/secrets.toml
secrets.toml

.env
.env.*

.vscode/
.idea/

.DS_Store
Thumbs.db
```

Municipal accounts should be assigned the appropriate role through a controlled administrative process.

---

# ⚠️ Current Limitations

* AI analysis may occasionally be incorrect or uncertain.
* AI confidence is not a calibrated probability.
* Sri Lankan address matching may sometimes be inconsistent.
* Related-report detection currently relies mainly on location and time.
* The current lifecycle primarily uses `SUBMITTED` and `REVIEWED`.
* The system is an MVP and requires further production security and evaluation.

---

# 🛣️ Future Improvements

Planned improvements include:

* stronger role-based security
* improved Sri Lankan location handling
* image/text similarity for duplicate detection
* expanded incident lifecycle
* audit history
* municipal assignment
* route optimisation
* waste hotspot analytics
* collection tracking and ETA prediction

---

# 📌 Disclaimer

CleanSight AI is an **AI-assisted civic reporting and municipal decision-support system**.

AI-generated information may contain errors and should be reviewed by municipal officers before being treated as verified information.

---

# 📄 License

This project is licensed under the **MIT License**.

See [`LICENSE`](LICENSE) for details.

---

<div align="center">

## ♻️ CleanSight AI

### Smarter reporting. Clearer municipal decisions. Cleaner communities.

</div>
