import os
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def generate_ai_recommendations(report):
    """
    Generate personalized study recommendations grounded strictly in verified
    student analytics from analytics.py. Covers all identified learning gaps.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here" or not GENAI_AVAILABLE:
        return {
            "source": "Rule-Based Analytics (add GEMINI_API_KEY in .env to enable Gemini AI)",
            "suggestions": report.get("recommendations", []),
        }

    student = report["student"]
    gaps = report.get("learning_gaps", [])
    gaps_text = (
        "\n".join(
            f"- {g['subject']} / {g['topic']}: {g['average']}% ({g['level']})"
            for g in gaps
        )
        or "No critical topic gaps detected (<65%)."
    )
    subjects_text = "\n".join(
        f"- {s['subject']}: {s['average']}% ({s['status']})"
        for s in report.get("subject_breakdown", [])
    )

    prompt = (
        f"You are an academic tutor helping a teacher support a student.\n"
        f"Student: {student['name']} ({student['department']}, {student['semester']})\n"
        f"Overall Average: {report['overall_average']}% | Trend: {report['trend']}\n\n"
        f"Subject Averages:\n{subjects_text}\n\n"
        f"Identified Learning Gaps:\n{gaps_text}\n\n"
        f"Based ONLY on the verified scores above, provide one concise, actionable study "
        f"recommendation (1-2 sentences) for EACH identified learning gap or weak subject "
        f"(and an overall study tip if all subjects are strong). Format as plain bullet points, "
        f"one per line, without inventing scores or making permanent ability judgements."
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        lines = [
            line.lstrip("-*•0123456789. ").strip()
            for line in response.text.splitlines()
            if line.strip()
        ]
        return {
            "source": "Gemini AI (gemini-2.5-flash)",
            "suggestions": lines if lines else report.get("recommendations", []),
        }
    except Exception as exc:
        return {
            "source": f"Rule-Based Fallback (Gemini error: {exc})",
            "suggestions": report.get("recommendations", []),
        }
