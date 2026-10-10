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

# Convert a list of column values into a single pipe-delimited line string
def _row_to_line(values):
    return COLUMN_SEPARATOR.join(str(v) for v in values)

# Parses a pipe-delimited line string back into a list of column values
def _line_to_row(line):
    return line.rstrip("\n").split(COLUMN_SEPARATOR)

# Loads and parses stored records into dictionaries, handling missing or corrupt files safely
def load_records(path=CSV_FILE):
    records = []
    if not os.path.exists(path):
        logger.info(f"{path} not found. Starting with an empty record set.")
        return records

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Error reading {path}: {e}. Returning empty record set.")
        return []

    if not lines:
        return records

    header = _line_to_row(lines[0])
    for line in lines[1:]:
        values = _line_to_row(line)
        if len(values) != len(header):
            logger.warning(f"Skipping malformed row (column count mismatch): {line!r}")
            continue
        row = dict(zip(header, values))
        try:
            records.append({
                "id": row.get("id", ""),
                "name": row.get("name", ""),
                "skills": _cell_to_list(row.get("skills", "")),
                "it_experience_years": float(row.get("it_experience_years") or 0),
                "certificates": _cell_to_certs_dict(row.get("certificates", "")),
                "it_certs": _cell_to_list(row.get("it_certs", "")),
                "missing_skills_count": int(float(row.get("missing_skills_count") or 0)),
                "score": float(row.get("score") or 0),
                "outcome": row.get("outcome", ""),
                "timestamp": row.get("timestamp", ""),
            })
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping corrupt row: {row} ({e})")

    return records

# Determines the next sequential ID by counting existing records in the csv file
def _next_id(path):
    existing = load_records(path)
    return len(existing) + 1

# Appends a batch of records to csv database, writing headers if needed and using sequential IDs
def save_records(records, path=CSV_FILE):
    """
    Appends a batch of graded records to the file, assigning each a
    sequential, zero-padded id that continues from the existing data.
    Writes a '||'-separated header line if the file doesn't exist yet.
    """
    file_exists = os.path.exists(path)
    start_id = _next_id(path)

    try:
        with open(path, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write(_row_to_line(FIELDNAMES) + "\n")
            for i, record in enumerate(records):
                row = [
                    f"{start_id + i:02d}",
                    record.get("name", ""),
                    _list_to_cell(record.get("skills", [])),
                    record.get("it_experience_years", 0),
                    _certs_dict_to_cell(record.get("certificates", {})),
                    _list_to_cell(record.get("it_certs", [])),
                    record.get("missing_skills_count", 0),
                    record.get("score", 0),
                    record.get("outcome", ""),
                    record.get("timestamp", ""),
                ]
                f.write(_row_to_line(row) + "\n")
    except Exception as e:
        logger.error(f"Failed to save records to {path}: {e}")