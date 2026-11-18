import numpy as np

try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from analytics import _load_dataframes


def predict_student_performance():
    """
    Estimate each student's next assessment score using Linear Regression
    on their chronological assessment percentages, and classify support priority
    using both current average and predicted trajectory.
    """
    students_df, assessments_df = _load_dataframes()
    if students_df.empty or assessments_df.empty:
        return {
            "model": "Scikit-learn LinearRegression" if SKLEARN_AVAILABLE else "NumPy Linear Trend",
            "disclaimer": "Estimates are based solely on historical assessment trends and should support—not replace—teacher judgement.",
            "predictions": [],
        }

    predictions = []
    for _, student in students_df.iterrows():
        sid = int(student["id"])
        s_df = assessments_df[assessments_df["student_id"] == sid].sort_values(
            by=["assessed_date", "id"]
        )

        if s_df.empty:
            continue

        scores = s_df["percentage"].to_numpy(dtype=float)
        current_avg = round(float(np.mean(scores)), 1)
        n = len(scores)

        if n >= 2:
            x = np.arange(n).reshape(-1, 1)
            if SKLEARN_AVAILABLE:
                model = LinearRegression()
                model.fit(x, scores)
                slope = float(model.coef_[0])
                raw_pred = float(model.predict(np.array([[n]]))[0])
            else:
                slope = float(np.polyfit(np.arange(n), scores, 1)[0])
                raw_pred = float(scores[-1] + slope)

            estimated_next = round(max(0.0, min(100.0, raw_pred)), 1)
            slope_rounded = round(slope, 2)
        else:
            estimated_next = current_avg
            slope_rounded = 0.0

        # Combine current average, predicted score, and declining trend for accurate support flags
        if current_avg < 50.0 or estimated_next < 50.0:
            risk = "High Support Priority"
        elif current_avg < 65.0 or estimated_next < 65.0 or slope_rounded <= -3.0:
            risk = "Monitor"
        else:
            risk = "On Track"

        predictions.append(
            {
                "student_id": sid,
                "roll_number": student["roll_number"],
                "name": student["name"],
                "department": student["department"],
                "semester": student["semester"],
                "assessments_count": n,
                "current_average": current_avg,
                "estimated_next_score": estimated_next,
                "trend_slope": slope_rounded,
                "support_estimate": risk,
                "confidence_note": "Low (<3 tests)" if n < 3 else "Moderate",
            }
        )

    predictions.sort(key=lambda p: p["estimated_next_score"])
    return {
        "model": "Scikit-learn LinearRegression" if SKLEARN_AVAILABLE else "NumPy Linear Trend (install scikit-learn)",
        "disclaimer": "Estimates are based solely on historical assessment trends and should support—not replace—teacher judgement.",
        "predictions": predictions,
    }
