"""
AI Manager
----------
Core engine - every resume record passes through here.

Responsibilities:
  - Build a prompt from the batch of resumes
  - Upload resumes to the AI API (Gemini) and call it
  - Validate the response schema - reject/retry on malformed output
  - Handle API failures gracefully (log and continue, never crash)
  - Split the batch response into one record per resume

Zero domain logic lives here - only API interaction and response plumbing.
The AI never sees job requirements; it only extracts facts from each resume.

NOTE: API_KEY is hardcoded below for LOCAL USE ONLY.
Do NOT commit/push this file to GitHub with a real key in it.
"""

import os
import json
import time
import logging
from typing import Any

from google import genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIManager")

# --- Hardcoded for local use only ---
API_KEY = "API KEY"
_client = genai.Client(api_key=API_KEY)
# -----------------------------------------

MODEL_NAME = "gemini-3.5-flash-lite"  # update if your team switches models
MAX_RETRIES = 5

REQUIRED_FIELDS = {"filename", "name", "skills", "experience_by_field", "certificates_by_industry"}


def _build_prompt(filenames: list[str]) -> str:
    #Builds the instruction text sent alongside the uploaded resume files.
    file_list = "\n".join(f"- {name}" for name in filenames)
    return (
        "You are an information extraction engine. You will be given "
        f"{len(filenames)} resumes as attached files:\n{file_list}\n\n"
        "For EACH resume, extract:\n"
        "  - filename: the exact file name of the resume\n"
        "  - name: the candidate's full name as it appears on the resume\n"
        "  - skills: a list of technical/professional skills mentioned\n"
        "  - experience_by_field: an object mapping each professional field/industry the "
        "candidate has worked in to their total years of experience in that field, e.g. "
        '{"IT": 4, "Finance": 1}. Use your best judgement to categorize roles into fields '
        "(e.g. IT, Finance, Marketing, Healthcare, Education, Sales, Engineering, Business). "
        "If experience is not clearly tied to a field, categorize it under \"General\".\n"
        "  - certificates_by_industry: an object mapping each industry to a LIST of the "
        'exact certificate names the candidate holds in that industry, e.g. '
        '{"IT": ["AWS Certified Solutions Architect", "CompTIA Security+"], "FnB": ["ServSafe"]}. '
        "Use an empty object {} if no certificates are mentioned.\n\n"
        "Return ONLY a JSON array, one object per resume, with exactly these five keys. "
        "Do not include any explanation, markdown formatting, or extra text - JSON only."
    )


def _upload_resumes(resume_paths: list[str]) -> list[Any]:
    #Uploads each resume file to the API's file store and returns the file handles.
    uploaded = []
    for path in resume_paths:
        try:
            file_ref = _client.files.upload(file=path)
            uploaded.append(file_ref)
        except Exception as e:
            logger.error(f"Failed to upload {path}: {e}")
    return uploaded


def _validate_record(record: dict[str, Any]) -> bool:
    #Checks a single parsed record has the required fields and correct types.
    if not isinstance(record, dict):
        return False
    if not REQUIRED_FIELDS.issubset(record.keys()):
        return False
    if not isinstance(record.get("name"), str):
        return False
    if not isinstance(record.get("skills"), list):
        return False

    experience_by_field = record.get("experience_by_field")
    if not isinstance(experience_by_field, dict):
        return False
    if not all(isinstance(v, (int, float)) for v in experience_by_field.values()):
        return False

    certs_by_industry = record.get("certificates_by_industry")
    if not isinstance(certs_by_industry, dict):
        return False
    for industry_certs in certs_by_industry.values():
        if not isinstance(industry_certs, list):
            return False
        if not all(isinstance(c, str) for c in industry_certs):
            return False

    return True


def _parse_response(raw_text: str) -> list[dict[str, Any]] | None:
    """Parses the model's raw text output into a list of dicts. Returns None on failure."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    return data


def process_resume_batch(resume_paths: list[str]) -> list[dict[str, Any]]:
    if not resume_paths:
        return []

    filenames = [os.path.basename(p) for p in resume_paths]
    prompt = _build_prompt(filenames)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            uploaded_files = _upload_resumes(resume_paths)
            if not uploaded_files:
                logger.error("No resumes were successfully uploaded.")
                return []

            response = _client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, *uploaded_files],
                config={"response_mime_type": "application/json"},
            )
            records = _parse_response(response.text)

            if records is None:
                logger.warning(f"Attempt {attempt}: malformed JSON response, retrying...")
                continue

            valid_records = [r for r in records if _validate_record(r)]
            if len(valid_records) < len(records):
                logger.warning(
                    f"Attempt {attempt}: {len(records) - len(valid_records)} record(s) "
                    "failed schema validation and were dropped."
                )

            if valid_records:
                return valid_records

            logger.warning(f"Attempt {attempt}: no valid records parsed, retrying...")

        except Exception as e:
            logger.error(f"Attempt {attempt}: API call failed: {e}")
            time.sleep(5 * attempt)

    logger.error("All retries exhausted. Returning empty result for this batch.")
    return []