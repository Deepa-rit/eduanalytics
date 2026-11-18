# EduAnalytics – Student Learning and Performance Analytics System

EduAnalytics is a web-based educational analytics platform built with **Python Flask**, **SQLite**, **Pandas**, and **Chart.js** to help teachers monitor student performance, identify subject- and topic-level learning gaps, and generate explainable study recommendations.

## Project Structure

```text
eduanalytics/
├── app.py                  # Flask server & REST API endpoints
├── database.py             # SQLite connection & schema initialization
├── analytics.py            # Pandas analytics, gap detection & recommendations
├── seed_data.py            # Synthetic student & assessment dataset seeder
├── requirements.txt        # Python dependencies
├── .env.example            # Template for optional Gemini API key
├── .gitignore              # Excludes .env, venv, and local .db file
├── templates/
│   └── index.html          # Teacher-focused blue-and-white dashboard
└── static/
    ├── css/style.css       # Dashboard styling
    └── js/app.js           # Frontend logic & Chart.js visualizations
```

## Quick Start

1. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS / Linux:
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```
   The database (`eduanalytics.db`) initializes automatically on first run and seeds 10 synthetic students with 50 topic-level assessment records.

4. **Open in your browser**
   Visit `http://127.0.0.1:5000`

## Core Features (v1)

- **Teacher Dashboard**: Class KPIs (Total Students, Class Average, Pass Rate, Students Needing Support), subject-wise bar chart, assessment trend line chart, and performance distribution doughnut chart.
- **Student Management**: Add, edit, search, filter by department, and delete student records.
- **Assessment Management**: Record subject- and topic-level marks across quizzes, assignments, and internal exams.
- **Learning Gap Identification**: Automatically flags weak subjects (< 65% monitor, < 50% critical) and difficult topics with explainable study recommendations.
- **Individual Student Reports & CSV Export**: View per-student subject breakdowns, performance trends, and export class assessment data to CSV.

## Privacy & Research Note

- Uses **synthetic student data** by default.
- Performance analytics and future ML predictions should be used as **supportive educational estimates**, not definitive judgements about a student's ability.
