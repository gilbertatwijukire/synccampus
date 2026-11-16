import os

FRONTEND_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv("FRONTEND_ORIGINS", "").split(",") if origin.strip()]

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./saagi.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ACCESS_CODE_PEPPER = os.getenv("ACCESS_CODE_PEPPER", "dev-pepper-change-me")
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "480"))
ESCALATION_CHECK_SECONDS = int(os.getenv("ESCALATION_CHECK_SECONDS", "300"))

# Priority score weights (must sum to 1.0). Calibrate from questionnaire Q16.
WEIGHTS = {"S": 0.25, "U": 0.20, "N": 0.20, "D": 0.15, "R": 0.20}
LEVEL_BANDS = [(80, "Critical"), (60, "High"), (40, "Medium"), (0, "Low")]
STUDENTS_CAP = 25      # N = min(affected / STUDENTS_CAP, 1)
RELATED_CAP = 4        # R = min(related reports / RELATED_CAP, 1)
RESPONSE_LIMIT_HRS = 24   # expected response limit used by the duration factor D
URGENCY_MAP = {1: 0.25, 2: 0.50, 3: 0.75, 4: 1.00}   # low .. critical

# Related-concern thresholds (cosine similarity)
RELATED_THRESHOLD = 0.50
DUPLICATE_THRESHOLD = 0.80

# Delegate score weights
DELEGATE_WEIGHTS = {"M": 0.50, "L": 0.30, "E": 0.20}

# Default reminder / escalation hours by priority level. Calibrate from Q22.
ESCALATION_HOURS = {
    "Critical": {"reminder": 3, "escalate": 6},
    "High": {"reminder": 12, "escalate": 24},
    "Medium": {"reminder": 48, "escalate": 72},
    "Low": {"reminder": 120, "escalate": 168},
}
