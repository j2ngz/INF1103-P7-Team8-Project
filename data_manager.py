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

def _list_to_cell(items):
    return ITEM_SEPARATOR.join(str(i).strip().lower() for i in items) if items else ""


def _cell_to_list(cell):
    return [s.strip() for s in cell.split(ITEM_SEPARATOR) if s.strip()] if cell else []