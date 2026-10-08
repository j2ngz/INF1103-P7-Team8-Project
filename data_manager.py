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

# Covert python list to a single comma separated lowercase string
def _list_to_cell(items):
    return ITEM_SEPARATOR.join(str(i).strip().lower() for i in items) if items else ""

# Parses comma separated string into python list of strings
def _cell_to_list(cell):
    return [s.strip() for s in cell.split(ITEM_SEPARATOR) if s.strip()] if cell else []

# Convert dictionary of industry certs into a formatted colon/semicolon string
def _certs_dict_to_cell(certs_by_industry):
    if not certs_by_industry:
        return ""
    sections = []
    for industry, certs in certs_by_industry.items():
        cert_list = ITEM_SEPARATOR.join(c.strip().lower() for c in certs)
        sections.append(f"{industry.strip().lower()}:{cert_list}")
    return INDUSTRY_SEPARATOR.join(sections)

# Parses formatted cert string into a dictionary of lists by industry
def _cell_to_certs_dict(cell):
    result = {}
    if not cell:
        return result
    for section in cell.split(INDUSTRY_SEPARATOR):
        if ":" not in section:
            continue
        industry, cert_list = section.split(":", 1)
        certs = [c.strip() for c in cert_list.split(ITEM_SEPARATOR) if c.strip()]
        result[industry.strip()] = certs
    return result