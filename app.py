import csv
import io
import sqlite3
import pandas as pd
from flask import Flask, Response, jsonify, render_template, request

from ai_recommender import generate_ai_recommendations
from analytics import get_dashboard_analytics, get_student_report
from database import get_connection, init_db
from ml_predictor import predict_student_performance
from seed_data import seed_database

app = Flask(__name__)

# Initialize DB and seed 5 default synthetic students on first startup
init_db()
seed_database(force=False)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    return jsonify(get_dashboard_analytics())


@app.route("/api/predictions", methods=["GET"])
def api_predictions():
    return jsonify(predict_student_performance())


@app.route("/api/metadata", methods=["GET"])
def api_metadata():
    """Return distinct departments, semesters, subjects, and assessment types for filter dropdowns."""
    with get_connection() as conn:
        depts = [
            r["department"]
            for r in conn.execute(
                "SELECT DISTINCT department FROM students ORDER BY department ASC"
            ).fetchall()
        ]
        sems = [
            r["semester"]
            for r in conn.execute(
                "SELECT DISTINCT semester FROM students ORDER BY semester ASC"
            ).fetchall()
        ]
        subjects = [
            r["subject"]
            for r in conn.execute(
                "SELECT DISTINCT subject FROM assessments ORDER BY subject ASC"
            ).fetchall()
        ]
        types = [
            r["assessment_type"]
            for r in conn.execute(
                "SELECT DISTINCT assessment_type FROM assessments ORDER BY assessment_type ASC"
            ).fetchall()
        ]
    return jsonify(
        {
            "departments": depts,
            "semesters": sems,
            "subjects": subjects,
            "assessment_types": types,
        }
    )


@app.route("/api/subjects", methods=["GET"])
def api_list_subjects():
    with get_connection() as conn:
        rows = conn.execute("SELECT DISTINCT subject FROM assessments ORDER BY subject ASC").fetchall()
    return jsonify([r["subject"] for r in rows])


@app.route("/api/students", methods=["GET"])
def api_list_students():
    search = request.args.get("q", "").strip().lower()
    dept = request.args.get("department", "").strip()
    sem = request.args.get("semester", "").strip()
    status = request.args.get("status", "").strip()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.*,
                   ROUND(AVG(a.score * 100.0 / a.max_score), 1) AS average_pct,
                   COUNT(a.id) AS assessment_count
            FROM students s
            LEFT JOIN assessments a ON s.id = a.student_id
            GROUP BY s.id
            ORDER BY s.roll_number ASC
            """
        ).fetchall()

    students = [dict(r) for r in rows]
    if search:
        students = [
            s
            for s in students
            if search in s["name"].lower() or search in s["roll_number"].lower()
        ]
    if dept:
        students = [s for s in students if s["department"] == dept]
    if sem:
        students = [s for s in students if s["semester"] == sem]
    if status == "strong":
        students = [s for s in students if s["average_pct"] is not None and s["average_pct"] >= 75]
    elif status == "monitor":
        students = [s for s in students if s["average_pct"] is not None and 50 <= s["average_pct"] < 75]
    elif status == "support":
        students = [s for s in students if s["average_pct"] is not None and s["average_pct"] < 50]

    return jsonify(students)


@app.route("/api/students", methods=["POST"])
def api_create_student():
    data = request.get_json(silent=True) or {}
    roll_number = (data.get("roll_number") or "").strip().upper()
    name = (data.get("name") or "").strip()
    department = (data.get("department") or "").strip()
    semester = (data.get("semester") or "").strip()

    if not all([roll_number, name, department, semester]):
        return jsonify({"error": "All student fields are required."}), 400

    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO students (roll_number, name, department, semester) VALUES (?, ?, ?, ?)",
                (roll_number, name, department, semester),
            )
            conn.commit()
            return jsonify({"id": cur.lastrowid, "message": "Student added."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Roll number {roll_number} already exists."}), 409


@app.route("/api/students/<int:student_id>", methods=["PUT"])
def api_update_student(student_id):
    data = request.get_json(silent=True) or {}
    roll_number = (data.get("roll_number") or "").strip().upper()
    name = (data.get("name") or "").strip()
    department = (data.get("department") or "").strip()
    semester = (data.get("semester") or "").strip()

    if not all([roll_number, name, department, semester]):
        return jsonify({"error": "All student fields are required."}), 400

    try:
        with get_connection() as conn:
            cur = conn.execute(
                """
                UPDATE students
                SET roll_number = ?, name = ?, department = ?, semester = ?
                WHERE id = ?
                """,
                (roll_number, name, department, semester, student_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Student not found."}), 404
            return jsonify({"message": "Student updated."})
    except sqlite3.IntegrityError:
        return jsonify({"error": f"Roll number {roll_number} already exists."}), 409


@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def api_delete_student(student_id):
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Student not found."}), 404
    return jsonify({"message": "Student deleted."})


@app.route("/api/students/<int:student_id>/report", methods=["GET"])
def api_student_report(student_id):
    report = get_student_report(student_id)
    if report is None:
        return jsonify({"error": "Student not found."}), 404
    return jsonify(report)


@app.route("/api/students/<int:student_id>/ai-recommendations", methods=["POST"])
def api_student_ai_recommendations(student_id):
    report = get_student_report(student_id)
    if report is None:
        return jsonify({"error": "Student not found."}), 404
    return jsonify(generate_ai_recommendations(report))


@app.route("/api/assessments", methods=["GET"])
def api_list_assessments():
    search = request.args.get("q", "").strip().lower()
    dept = request.args.get("department", "").strip()
    subject = request.args.get("subject", "").strip()
    atype = request.args.get("assessment_type", "").strip()
    status = request.args.get("status", "").strip()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.*, s.roll_number, s.name AS student_name, s.department,
                   ROUND(a.score * 100.0 / a.max_score, 1) AS percentage
            FROM assessments a
            JOIN students s ON a.student_id = s.id
            ORDER BY a.assessed_date DESC, a.id DESC
            """
        ).fetchall()

    results = [dict(r) for r in rows]
    if search:
        results = [
            r
            for r in results
            if search in r["student_name"].lower()
            or search in r["roll_number"].lower()
            or search in r["topic"].lower()
        ]
    if dept:
        results = [r for r in results if r["department"] == dept]
    if subject:
        results = [r for r in results if r["subject"] == subject]
    if atype:
        results = [r for r in results if r["assessment_type"] == atype]
    if status == "strong":
        results = [r for r in results if r["percentage"] >= 75]
    elif status == "monitor":
        results = [r for r in results if 50 <= r["percentage"] < 75]
    elif status == "support":
        results = [r for r in results if r["percentage"] < 50]

    return jsonify(results)


@app.route("/api/assessments", methods=["POST"])
def api_create_assessment():
    data = request.get_json(silent=True) or {}
    try:
        student_id = int(data.get("student_id"))
        score = float(data.get("score"))
        max_score = float(data.get("max_score", 100))
    except (TypeError, ValueError):
        return jsonify({"error": "Valid student_id, score, and max_score are required."}), 400

    subject = (data.get("subject") or "").strip()
    topic = (data.get("topic") or "").strip()
    assessment_type = (data.get("assessment_type") or "").strip()
    assessed_date = (data.get("assessed_date") or "").strip()

    if not all([subject, topic, assessment_type, assessed_date]):
        return jsonify({"error": "Subject, topic, assessment type, and date are required."}), 400
    if max_score <= 0 or score < 0 or score > max_score:
        return jsonify({"error": "Score must be between 0 and max_score."}), 400

    with get_connection() as conn:
        student_exists = conn.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student_exists:
            return jsonify({"error": "Selected student does not exist."}), 404
        cur = conn.execute(
            """
            INSERT INTO assessments
            (student_id, subject, topic, assessment_type, score, max_score, assessed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, subject, topic, assessment_type, score, max_score, assessed_date),
        )
        conn.commit()
        return jsonify({"id": cur.lastrowid, "message": "Assessment recorded."}), 201


@app.route("/api/assessments/<int:assessment_id>", methods=["DELETE"])
def api_delete_assessment(assessment_id):
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Assessment not found."}), 404
    return jsonify({"message": "Assessment deleted."})


@app.route("/api/import/template", methods=["GET"])
def api_import_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "roll_number",
            "name",
            "department",
            "semester",
            "subject",
            "topic",
            "assessment_type",
            "score",
            "max_score",
            "assessed_date",
        ]
    )
    writer.writerow(
        ["CS2406", "Meera Sundaram", "CSE", "Sem 4", "Data Structures", "Binary Trees", "Quiz", "82", "100", "2026-10-15"]
    )
    writer.writerow(
        ["CS2407", "Arjun Patel", "IT", "Sem 4", "", "", "", "", "", ""]
    )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=eduanalytics_import_template.csv"},
    )


@app.route("/api/import/csv", methods=["POST"])
def api_import_csv():
    if "file" not in request.files:
        return jsonify({"error": "No CSV file uploaded."}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a valid .csv file."}), 400

    try:
        df = pd.read_csv(file)
    except Exception as exc:
        return jsonify({"error": f"Could not parse CSV: {exc}"}), 400

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    required_student_cols = {"roll_number", "name", "department", "semester"}
    if not required_student_cols.issubset(set(df.columns)):
        return jsonify(
            {"error": "CSV must include columns: roll_number, name, department, semester."}
        ), 400

    students_added = 0
    assessments_added = 0

    with get_connection() as conn:
        for _, row in df.iterrows():
            roll = str(row.get("roll_number", "")).strip().upper()
            name = str(row.get("name", "")).strip()
            dept = str(row.get("department", "")).strip()
            sem = str(row.get("semester", "")).strip()
            if not roll or roll == "NAN" or not name or name == "NAN":
                continue

            existing = conn.execute(
                "SELECT id FROM students WHERE roll_number = ?", (roll,)
            ).fetchone()
            if existing:
                student_id = existing["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO students (roll_number, name, department, semester) VALUES (?, ?, ?, ?)",
                    (roll, name, dept or "General", sem or "Sem 1"),
                )
                student_id = cur.lastrowid
                students_added += 1

            subj = str(row.get("subject", "")).strip()
            topic = str(row.get("topic", "")).strip()
            atype = str(row.get("assessment_type", "")).strip()
            dt = str(row.get("assessed_date", "")).strip()
            score_val = row.get("score")
            max_val = row.get("max_score", 100)

            if (
                subj and subj.lower() != "nan"
                and topic and topic.lower() != "nan"
                and pd.notna(score_val)
            ):
                try:
                    score = float(score_val)
                    max_score = float(max_val) if pd.notna(max_val) else 100.0
                    if max_score > 0 and 0 <= score <= max_score:
                        conn.execute(
                            """
                            INSERT INTO assessments
                            (student_id, subject, topic, assessment_type, score, max_score, assessed_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                student_id,
                                subj,
                                topic,
                                atype if atype and atype.lower() != "nan" else "Assessment",
                                score,
                                max_score,
                                dt if dt and dt.lower() != "nan" else "2026-10-15",
                            ),
                        )
                        assessments_added += 1
                except (TypeError, ValueError):
                    continue

        conn.commit()

    return jsonify(
        {
            "message": f"Imported {students_added} new student(s) and {assessments_added} assessment(s).",
            "students_added": students_added,
            "assessments_added": assessments_added,
        }
    )


@app.route("/api/export/csv", methods=["GET"])
def api_export_csv():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.roll_number, s.name, s.department, s.semester,
                   a.subject, a.topic, a.assessment_type, a.score, a.max_score,
                   ROUND(a.score * 100.0 / a.max_score, 1) AS percentage, a.assessed_date
            FROM assessments a
            JOIN students s ON a.student_id = s.id
            ORDER BY s.roll_number, a.assessed_date
            """
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Roll Number",
            "Student Name",
            "Department",
            "Semester",
            "Subject",
            "Topic",
            "Assessment Type",
            "Score",
            "Max Score",
            "Percentage (%)",
            "Date",
        ]
    )
    for r in rows:
        writer.writerow(list(r))

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=eduanalytics_report.csv"},
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)
