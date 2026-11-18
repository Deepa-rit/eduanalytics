from database import get_connection, init_db

# 5 default synthetic students (privacy-safe illustrative data)
SYNTHETIC_STUDENTS = [
    ("CS2401", "Aarav Sharma", "CSE", "Sem 4"),
    ("CS2402", "Priya Nair", "CSE", "Sem 4"),
    ("CS2403", "Karthik Subramanian", "CSE", "Sem 4"),
    ("AI2404", "Divya Krishnan", "AI & DS", "Sem 4"),
    ("AI2405", "Rohan Verma", "AI & DS", "Sem 4"),
]

SYNTHETIC_ASSESSMENTS = [
    # Aarav Sharma (Strong overall, slight dip in Math)
    ("CS2401", "Python Programming", "Object-Oriented Programming", "Internal 1", 86, 100, "2026-09-10"),
    ("CS2401", "DBMS", "SQL Joins & Subqueries", "Internal 1", 82, 100, "2026-09-14"),
    ("CS2401", "Mathematics", "Linear Algebra", "Assignment", 62, 100, "2026-09-20"),
    ("CS2401", "Computer Networks", "IP Addressing & Subnetting", "Quiz", 78, 100, "2026-09-28"),
    ("CS2401", "Artificial Intelligence", "Search Algorithms", "Internal 2", 91, 100, "2026-10-08"),

    # Priya Nair (Strong across all)
    ("CS2402", "Python Programming", "Loops & Functions", "Internal 1", 92, 100, "2026-09-10"),
    ("CS2402", "DBMS", "Normalization", "Internal 1", 88, 100, "2026-09-14"),
    ("CS2402", "Mathematics", "Probability & Statistics", "Assignment", 84, 100, "2026-09-20"),
    ("CS2402", "Computer Networks", "OSI & TCP/IP Layers", "Quiz", 85, 100, "2026-09-28"),
    ("CS2402", "Artificial Intelligence", "Machine Learning Basics", "Internal 2", 94, 100, "2026-10-08"),

    # Karthik Subramanian (Needs support in Math & CN)
    ("CS2403", "Python Programming", "File Handling & Exceptions", "Internal 1", 68, 100, "2026-09-10"),
    ("CS2403", "DBMS", "SQL Joins & Subqueries", "Internal 1", 58, 100, "2026-09-14"),
    ("CS2403", "Mathematics", "Linear Algebra", "Assignment", 38, 100, "2026-09-20"),
    ("CS2403", "Computer Networks", "IP Addressing & Subnetting", "Quiz", 42, 100, "2026-09-28"),
    ("CS2403", "Artificial Intelligence", "Search Algorithms", "Internal 2", 61, 100, "2026-10-08"),

    # Divya Krishnan (Improving trend)
    ("AI2404", "Python Programming", "Object-Oriented Programming", "Internal 1", 72, 100, "2026-09-10"),
    ("AI2404", "DBMS", "Transactions & Indexing", "Internal 1", 75, 100, "2026-09-14"),
    ("AI2404", "Mathematics", "Probability & Statistics", "Assignment", 79, 100, "2026-09-20"),
    ("AI2404", "Computer Networks", "Routing Algorithms", "Quiz", 81, 100, "2026-09-28"),
    ("AI2404", "Artificial Intelligence", "Machine Learning Basics", "Internal 2", 89, 100, "2026-10-08"),

    # Rohan Verma (Needs support)
    ("AI2405", "Python Programming", "Loops & Functions", "Internal 1", 48, 100, "2026-09-10"),
    ("AI2405", "DBMS", "Normalization", "Internal 1", 44, 100, "2026-09-14"),
    ("AI2405", "Mathematics", "Calculus & Optimization", "Assignment", 39, 100, "2026-09-20"),
    ("AI2405", "Computer Networks", "IP Addressing & Subnetting", "Quiz", 51, 100, "2026-09-28"),
    ("AI2405", "Artificial Intelligence", "Knowledge Representation", "Internal 2", 54, 100, "2026-10-08"),
]


def seed_database(force=False):
    """Populate SQLite with 5 default synthetic students if empty (or when force=True)."""
    init_db()
    with get_connection() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if existing > 0 and not force:
            return False

        if force:
            conn.execute("DELETE FROM assessments")
            conn.execute("DELETE FROM students")

        roll_to_id = {}
        for roll, name, dept, sem in SYNTHETIC_STUDENTS:
            cur = conn.execute(
                "INSERT INTO students (roll_number, name, department, semester) VALUES (?, ?, ?, ?)",
                (roll, name, dept, sem),
            )
            roll_to_id[roll] = cur.lastrowid

        for roll, subj, topic, atype, score, max_score, dt in SYNTHETIC_ASSESSMENTS:
            conn.execute(
                """
                INSERT INTO assessments
                (student_id, subject, topic, assessment_type, score, max_score, assessed_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (roll_to_id[roll], subj, topic, atype, score, max_score, dt),
            )
        conn.commit()
    return True


if __name__ == "__main__":
    seed_database(force=True)
    print("Seeded EduAnalytics database with 5 default synthetic students.")
