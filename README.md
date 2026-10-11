# AI Resume Screener

**INF1103 Programming Fundamentals with DevOps — Class LAB-P7, Group 8**

Team: Tan Bin Qian, Kieran Lee Teck Hong, Tan Jun Kang, Tay Jing Ni, Liu JiaQi

## Introduction

Recruiters read resumes manually a lot, and the same resume gets different ratings from
different reviewers. Our command-line application automates first-pass screening. The
recruiter puts resume PDFs in the `resumes/` folder and selects "Scan Resume". Every
resume is run through the Gemini AI API, which only pulls facts (name, skills, years of
experience per field, certificates per industry). The application then scores each
resume against a job requirements file and saves the result to a flat file so results can
be reviewed in later runs.

The implementation is 100% procedural (only functions, no classes) and consists of four
modules that form a pipeline:

```
io_manager  ->  ai_manager  ->  logic_manager  ->  data_manager
```

| Module | Job |
|---|---|
| `io_manager.py` | Menu, every `print()` / `input()`, reads the resume folder, moves scanned resumes |
| `ai_manager.py` | Uploads the resumes to Gemini and turns its JSON reply into one record per resume. No scoring |
| `logic_manager.py` | Reads `requirements.txt`, scores each resume out of 10 and decides the outcome |
| `data_manager.py` | Saves and loads results in `resume_records.csv`, plus `filter_records()` |

### Business rules (Logic Manager)

The score is out of 10 and has three parts:

| Part | Weight | Full marks when |
|---|---|---|
| Matched required skills | 40% | 4 or more required skills are matched |
| Years of experience in the target field (IT) | 40% | 5 or more years |
| IT certificates | 20% | 3 or more certificates |

The outcome depends on the score alone:

| Score | Outcome |
|---|---|
| above 7.5 | Accepted |
| above 4.0 up to and including 7.5 | Flagged for manual recruiter review |
| 4.0 or below | Rejected |

The job requirements text file is read for the required skills and minimum experience. It
is never sent to the AI. Skill matching is by substring, so `sql` matches a resume skill
written as `sql (postgresql, mysql)`. The weights, caps and thresholds are constants at
the top of `logic_manager.py`. `min_experience` is read from the file but does not
currently change the outcome.

## Setup and Usage

1. Use Python 3.12 or newer and install the one dependency:
   ```
   pip install google-genai
   ```
2. Put your Gemini API key in `ai_manager.py`. It is hardcoded for local use, not read
   from an environment variable:
   ```python
   API_KEY = "PASTE_YOUR_ACTUAL_KEY_HERE"
   ```
   **Never commit or push a real key to GitHub.** Before every `git push`, check that
   `API_KEY` is back to the placeholder. If a key was ever pushed, revoke it and create a
   new one.
3. Put the candidate PDFs in a folder named `resumes/` next to the `.py` files. Only `.pdf`
   files are read.
4. Edit `requirements.txt` to set the job criteria:
   ```
   required_skills: python, sql, tableau, power bi, aws, docker, kubernetes, git, linux
   min_experience: 1
   ```
   Lines starting with `#` and blank lines are ignored. This file holds the **job
   criteria**, not Python packages.
5. Run it:
   ```
   python io_manager.py
   ```

Menu:

```
=== Resume Screening System ===
1. Scan Resume
2. View Summary
3. Exit
```

- **Scan Resume** sends every PDF in `resumes/` to the AI in one batch, grades each one,
  saves the results and prints the summary table. Resumes that were processed
  successfully are moved to `scannedResume/`, which is created if it does not exist.
- **View Summary** prints every saved record from all earlier runs.
- **Exit** quits.

Example summary table:

```
| ID | Name           | Score   | Outcome  | Notes                            |
|----|----------------|---------|----------|----------------------------------|
| 03 | Arthur Goatson | 10.0/10 | Accepted |                                  |
| 05 | Samantha Vance | 6.3/10  | Flagged  | 8 skill(s) missing, 2 IT cert(s) |
```

Notes is filled in only for Flagged candidates (number of missing required skills and
number of IT certificates).

## Data Flow Diagram

Data moves through the system from the recruiter's menu choice to the summary table shown
back to them. The recruiter places the PDF resumes in a folder and lists the job
requirements in a text file. When a scan is requested, the system sends all the resumes
to an AI service (the Google Gemini API), which extracts the details of each candidate.
The system then scores them, saves the results, and shows them as a summary table when
the recruiter asks for it.

### External entities

- **E1 Recruiter:** chooses menu options, supplies resume PDFs and job requirements as
  files, and receives messages and the summary table.
- **E2 AI Service (Google Gemini API):** receives the request payload and returns the
  extracted resume data.

### Processes

| No. | Process | What it does |
|---|---|---|
| 1.0 | Validate User Input | Checks the recruiter's menu choice |
| 2.0 | Manage Resume Files | Reads the resume PDFs and, once processed, moves them to the archive folder |
| 3.0 | Build and Send AI Request | Builds the request (an extraction prompt plus the resume PDFs) and sends it to the AI Service |
| 4.0 | Process AI Response | Parses the response and checks it against the expected format |
| 5.0 | Grade Resumes | Scores each resume out of 10 using the required skills in `requirements.txt` and assigns Accepted, Flagged or Rejected |
| 6.0 | Store Records | Saves the graded records |
| 7.0 | Display Summary | Prints the summary table to the recruiter |

### Data stores

| Store | Location | Holds |
|---|---|---|
| D1 | `resumes/` | Resume PDFs waiting to be scanned |
| D2 | `requirements.txt` | The job criteria |
| D3 | `resume_records.csv` | Graded records, kept between runs |
| D4 | `scannedResume/` | Resumes that were processed successfully |

### Data flow

1. The recruiter's menu choice goes through the I/O Manager, and a scan command starts the
   resume file handling.
2. The I/O Manager reads the resumes and sends the file paths to the AI Manager, which
   sends the request to the AI Service. The raw response comes back.
3. The valid extracted records go to the Logic Manager, and the names of the processed
   resumes go back to the I/O Manager, which moves those PDFs to `scannedResume/`.
4. The Logic Manager grades the records using `requirements.txt` and sends them to the
   Data Manager, which appends them to the CSV.
5. When the recruiter chooses View Summary, the Data Manager reads the CSV and sends the
   data to the I/O Manager, which prints the summary table (ID, Name, Score, Outcome,
   Notes).

Invalid input and failed AI responses appear as return flows from processes 1.0 and 4.0.
Their handling is in the Exception Handling Matrix below.

## Data Structure and Storage Design

Data is stored in folders and files.

| Item | Contents |
|---|---|
| `resumes/` | PDFs of resumes uploaded by the user |
| `requirements.txt` | Plain text: the required skills and the minimum years of experience |
| `resume_records.csv` | The results of extraction and grading, one line per scanned resume |
| `scannedResume/` | PDFs of resumes that have already been scanned |

**`resume_records.csv` columns:**
`id`, `name`, `skills`, `it_experience_years`, `certificates`, `it_certs`,
`missing_skills_count`, `score`, `outcome`, `timestamp`

This is not a standard comma-separated file. Python's `csv` module only allows a
one-character delimiter, so `data_manager.py` writes and reads the file itself:

- Columns are separated by `||` instead of commas.
- Items inside a column are separated by `,`, for example `python,sql,docker`.
- In the `certificates` column, each industry is written as `industry:cert1,cert2`, so a
  `:` separates the industry from its certificates. Different industries are separated by
  `;`, for example `it:aws certified developer,pcep;fnb:servsafe`.
- `id` is zero-padded and starts at `01`. New scans continue from the last id.
- Skills and certificate text is stored in lower case.

Example line:

```
03||Arthur Goatson||python,flask,sql,docker,git||5||it:docker certified associate (dca),tableau certified data analyst||docker certified associate (dca),tableau certified data analyst||3||10.0||Accepted||2026-10-02 14:43:56
```

If you change the columns, delete the old `resume_records.csv` first, because old rows
will not load correctly.

## Exception Handling Matrix

| Exception scenario | Possible cause | Detection method | Handling strategy | User outcome |
|---|---|---|---|---|
| Resume folder missing | Folder deleted or renamed | `os.path.isdir()` returns false | Prints a warning and returns an empty list | Tells the user the folder doesn't exist and returns to the menu |
| No resumes to scan | Already scanned or not added | Empty list (`if not paths`) | Prints a message and skips scanning | Tells the user no resumes were found |
| File can't be moved | File open somewhere else, permission error | `try/except` around `shutil.move` | Prints the failed file name and continues with the others | Tells the user which file wasn't archived |
| Records file can't be saved | File open in Excel, no write permission | Exception on write | Catches it and logs an error | The save fails without crashing the program |
| Records file in old or wrong format | Older version of the CSV with different columns | Column count doesn't match the header, or a value can't be converted | Skips the bad rows | No crash. Unreadable rows don't appear in the table |
| Missing or invalid fields in an AI record | The AI left out a field or returned text where a number belongs | Field check and type check before scoring | Skips that record and logs it | The resume is not graded and stays in `resumes/` |
| API call failed | No internet, timeout, rate limit, service down | Exception from the API call, or no records returned | Retries up to 5 times with a growing wait, then prints an error, skips grading and saving, and does not move any files | The user is told the AI returned no usable records. Resumes remain in `resumes/` so the user can scan again |

Menu input is also validated: anything other than 1, 2 or 3 asks again.

## Automated tests

`test_logic_manager.py` tests the `logic_manager.py` functions on their own, using
hardcoded sample AI responses. It never imports `ai_manager`, so it needs no API key, no
internet and no resume files.

```
python test_logic_manager.py
```

You should see one `PASS` line per test and then `35 passed, 0 failed, 35 total`. The
script exits with code 0 when everything passes and 1 if anything fails. If you have
pytest installed, `python -m pytest test_logic_manager.py -v` also works. If you change
the weights, caps or thresholds in `logic_manager.py`, update the expected scores in the
tests too.

## Running with Docker

The `Dockerfile` copies the four modules, `requirements.txt` and the demo `resumes/`
folder into a `python:3.14-slim` image.

```
docker build -t resume-screening .
docker run -it --rm resume-screening
```

`-it` is needed because the menu waits for keyboard input. Results and moved files stay
inside the container and are lost when it exits, which resets the demo each time.

To run only the tests in the container (the Dockerfile must also contain
`COPY test_logic_manager.py .`):

```
docker run --rm resume-screening python test_logic_manager.py
```

## Project layout

```
INF1103_Team8/
├── io_manager.py          entry point and menu
├── ai_manager.py          Gemini API calls
├── logic_manager.py       scoring and outcomes
├── data_manager.py        saving and loading results
├── requirements.txt       job criteria (not pip requirements)
├── test_logic_manager.py  automated tests
├── resumes/               PDFs waiting to be scanned
├── scannedResume/         PDFs already processed
└── resume_records.csv     saved results (created on first scan)
```