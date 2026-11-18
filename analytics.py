import pandas as pd
from database import get_connection

SUPPORT_THRESHOLD = 50.0
MONITOR_THRESHOLD = 65.0

STUDY_RESOURCES = {
    "Python Programming": {
        "Loops & Functions": "Practice iterative problem sets and trace function call stacks on Python Tutor.",
        "Object-Oriented Programming": "Review class/object design patterns and implement 3 mini-exercises on inheritance.",
        "File Handling & Exceptions": "Work through try/except/finally labs and CSV/JSON read-write exercises.",
    },
    "DBMS": {
        "SQL Joins & Subqueries": "Solve 10 multi-table JOIN and nested query problems using sample schemas.",
        "Normalization": "Practice decomposing unnormalized tables step-by-step from 1NF to BCNF.",
        "Transactions & Indexing": "Review ACID properties, locking protocols, and B-Tree index lookup examples.",
    },
    "Mathematics": {
        "Linear Algebra": "Revise matrix operations, eigenvalues, and Gaussian elimination with worked examples.",
        "Probability & Statistics": "Practise conditional probability, Bayes' theorem, and distribution problems.",
        "Calculus & Optimization": "Work through derivative rules, partial derivatives, and gradient descent basics.",
    },
    "Computer Networks": {
        "OSI & TCP/IP Layers": "Map protocols to each OSI/TCP-IP layer and trace packet encapsulation.",
        "IP Addressing & Subnetting": "Complete 10 CIDR subnetting and network/broadcast address calculation drills.",
        "Routing Algorithms": "Compare Dijkstra's link-state and Bellman-Ford distance-vector routing tables.",
    },
    "Artificial Intelligence": {
        "Search Algorithms": "Trace BFS, DFS, and A* heuristic search trees on grid pathfinding examples.",
        "Knowledge Representation": "Practise propositional vs. first-order logic translations and inference rules.",
        "Machine Learning Basics": "Review supervised vs. unsupervised workflows, train/test splits, and evaluation metrics.",
    },
}


def _load_dataframes():
    """Load students and assessments into Pandas DataFrames."""
    with get_connection() as conn:
        students_df = pd.read_sql_query("SELECT * FROM students", conn)
        assessments_df = pd.read_sql_query("SELECT * FROM assessments", conn)

    if not assessments_df.empty:
        assessments_df["percentage"] = (
            assessments_df["score"] / assessments_df["max_score"]
        ) * 100.0
    return students_df, assessments_df


def get_dashboard_analytics():
    """Compute class-level KPIs, subject averages, trends, and learning gaps."""
    students_df, assessments_df = _load_dataframes()
    total_students = int(len(students_df))

    if total_students == 0 or assessments_df.empty:
        return {
            "kpis": {
                "total_students": total_students,
                "average_performance": 0.0,
                "pass_rate": 0.0,
                "students_needing_support": 0,
                "subjects_monitored": 0,
            },
            "subject_performance": [],
            "assessment_trend": [],
            "performance_distribution": {"strong": 0, "moderate": 0, "needs_support": 0},
            "topic_gaps": [],
            "support_students": [],
        }

    overall_avg = round(float(assessments_df["percentage"].mean()), 1)

    student_avgs = (
        assessments_df.groupby("student_id")["percentage"]
        .mean()
        .reset_index(name="avg_pct")
    )
    merged_students = students_df.merge(
        student_avgs, left_on="id", right_on="student_id", how="left"
    )
    assessed_students = merged_students.dropna(subset=["avg_pct"])

    pass_count = int((assessed_students["avg_pct"] >= SUPPORT_THRESHOLD).sum())
    assessed_count = len(assessed_students)
    pass_rate = round((pass_count / assessed_count) * 100.0, 1) if assessed_count else 0.0

    support_df = assessed_students[assessed_students["avg_pct"] < MONITOR_THRESHOLD].sort_values(
        by="avg_pct"
    )
    students_needing_support = int(len(assessed_students[assessed_students["avg_pct"] < SUPPORT_THRESHOLD]))

    strong_count = int((assessed_students["avg_pct"] >= 75.0).sum())
    moderate_count = int(
        ((assessed_students["avg_pct"] >= SUPPORT_THRESHOLD) & (assessed_students["avg_pct"] < 75.0)).sum()
    )
    needs_support_count = int((assessed_students["avg_pct"] < SUPPORT_THRESHOLD).sum())

    subject_df = (
        assessments_df.groupby("subject")["percentage"]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values(by="mean")
    )
    subject_performance = [
        {
            "subject": row["subject"],
            "average": round(float(row["mean"]), 1),
            "count": int(row["count"]),
            "status": (
                "Needs Attention"
                if row["mean"] < SUPPORT_THRESHOLD
                else "Monitor"
                if row["mean"] < MONITOR_THRESHOLD
                else "Strong"
            ),
        }
        for _, row in subject_df.iterrows()
    ]

    trend_df = (
        assessments_df.groupby("assessed_date")["percentage"]
        .mean()
        .reset_index()
        .sort_values(by="assessed_date")
    )
    assessment_trend = [
        {"date": row["assessed_date"], "average": round(float(row["percentage"]), 1)}
        for _, row in trend_df.iterrows()
    ]

    topic_df = (
        assessments_df.groupby(["subject", "topic"])["percentage"]
        .agg(["mean", "count"])
        .reset_index()
    )
    weak_topics = topic_df[topic_df["mean"] < MONITOR_THRESHOLD].sort_values(by="mean")
    topic_gaps = [
        {
            "subject": row["subject"],
            "topic": row["topic"],
            "average": round(float(row["mean"]), 1),
            "assessments": int(row["count"]),
            "severity": "Critical" if row["mean"] < SUPPORT_THRESHOLD else "Moderate",
            "recommendation": STUDY_RESOURCES.get(row["subject"], {}).get(
                row["topic"],
                f"Review core concepts and assign targeted practice exercises in {row['topic']}.",
            ),
        }
        for _, row in weak_topics.iterrows()
    ]

    support_students = [
        {
            "id": int(row["id"]),
            "roll_number": row["roll_number"],
            "name": row["name"],
            "department": row["department"],
            "average": round(float(row["avg_pct"]), 1),
            "priority": "High" if row["avg_pct"] < SUPPORT_THRESHOLD else "Medium",
        }
        for _, row in support_df.iterrows()
    ]

    return {
        "kpis": {
            "total_students": total_students,
            "average_performance": overall_avg,
            "pass_rate": pass_rate,
            "students_needing_support": students_needing_support,
            "subjects_monitored": int(assessments_df["subject"].nunique()),
        },
        "subject_performance": subject_performance,
        "assessment_trend": assessment_trend,
        "performance_distribution": {
            "strong": strong_count,
            "moderate": moderate_count,
            "needs_support": needs_support_count,
        },
        "topic_gaps": topic_gaps,
        "support_students": support_students,
    }


def get_student_report(student_id):
    """Build detailed analytics, learning gaps, trend, and recommendations for one student."""
    students_df, assessments_df = _load_dataframes()
    student_row = students_df[students_df["id"] == student_id]
    if student_row.empty:
        return None

    student = student_row.iloc[0].to_dict()
    student_assessments = assessments_df[assessments_df["student_id"] == student_id].sort_values(
        by="assessed_date"
    )

    if student_assessments.empty:
        return {
            "student": student,
            "overall_average": 0.0,
            "trend": "No data yet",
            "subject_breakdown": [],
            "learning_gaps": [],
            "recommendations": [
                "Record at least one assessment to generate performance insights and study recommendations."
            ],
            "assessments": [],
        }

    overall_avg = round(float(student_assessments["percentage"].mean()), 1)

    # Simple explainable trend calculation (first half vs second half of assessments)
    if len(student_assessments) >= 2:
        mid = len(student_assessments) // 2
        first_half = student_assessments.iloc[:mid]["percentage"].mean()
        second_half = student_assessments.iloc[mid:]["percentage"].mean()
        diff = second_half - first_half
        if diff >= 5.0:
            trend = "Improving"
        elif diff <= -5.0:
            trend = "Declining"
        else:
            trend = "Stable"
    else:
        trend = "Single assessment recorded"

    subj_df = (
        student_assessments.groupby("subject")["percentage"]
        .mean()
        .reset_index()
        .sort_values(by="percentage")
    )
    subject_breakdown = [
        {
            "subject": row["subject"],
            "average": round(float(row["percentage"]), 1),
            "status": (
                "Needs Attention"
                if row["percentage"] < SUPPORT_THRESHOLD
                else "Monitor Progress"
                if row["percentage"] < MONITOR_THRESHOLD
                else "Strong Performance"
            ),
        }
        for _, row in subj_df.iterrows()
    ]

    topic_df = (
        student_assessments.groupby(["subject", "topic"])["percentage"]
        .mean()
        .reset_index()
        .sort_values(by="percentage")
    )
    weak_topics = topic_df[topic_df["percentage"] < MONITOR_THRESHOLD]

    learning_gaps = []
    recommendations = []
    for _, row in weak_topics.iterrows():
        gap_level = "Critical" if row["percentage"] < SUPPORT_THRESHOLD else "Moderate"
        learning_gaps.append(
            {
                "subject": row["subject"],
                "topic": row["topic"],
                "average": round(float(row["percentage"]), 1),
                "level": gap_level,
            }
        )
        advice = STUDY_RESOURCES.get(row["subject"], {}).get(
            row["topic"],
            f"Focus on {row['topic']} fundamentals in {row['subject']} and complete targeted practice sets.",
        )
        recommendations.append(f"{row['subject']} — {row['topic']} ({round(float(row['percentage']), 1)}%): {advice}")

    if not recommendations:
        recommendations.append(
            "Consistent performance across all assessed topics. Encourage advanced problem-solving or peer mentoring."
        )

    assessments_list = [
        {
            "id": int(r["id"]),
            "subject": r["subject"],
            "topic": r["topic"],
            "assessment_type": r["assessment_type"],
            "score": float(r["score"]),
            "max_score": float(r["max_score"]),
            "percentage": round(float(r["percentage"]), 1),
            "assessed_date": r["assessed_date"],
        }
        for _, r in student_assessments.iterrows()
    ]

    return {
        "student": student,
        "overall_average": overall_avg,
        "trend": trend,
        "subject_breakdown": subject_breakdown,
        "learning_gaps": learning_gaps,
        "recommendations": recommendations,
        "assessments": assessments_list,
    }
