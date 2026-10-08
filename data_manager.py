import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataManager")

CSV_FILE = "resume_records.csv"
FIELDNAMES = [
    "id", "name", "skills", "it_experience_years", "certificates",
    "it_certs", "missing_skills_count", "score", "outcome", "timestamp",
]

COLUMN_SEPARATOR = "||"
ITEM_SEPARATOR = ","
INDUSTRY_SEPARATOR = ";"