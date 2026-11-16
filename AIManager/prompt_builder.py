
#building of instructions that is send to gemini API with the resumes attached
def build_prompt(filenames):

    #turns the file name into a list so the API knows which resume it was given
    file_list = "\n".join(f"- {name}" for name in filenames)
    return (
        "You are an information extraction engine. You will be given "
        f"{len(filenames)} resumes as attached files:\n{file_list}\n\n"
        #the things we want to extract out of the resume. the names must match ResumeData so LogicManager can compare later
        "For EACH resume, extract:\n"
        "  - filename: the exact file name of the resume\n"
        "  - name: the candidate's full name as it appears on the resume\n"
        "  - skills: a list of technical/professional skills mentioned\n"
        #all tech jobs go under "IT" in order to match the fields for our grading later on
        "  - experience_by_field: an object mapping each professional field/industry the "
        "candidate has worked in to their total years of experience in that field, e.g. "
        '{"IT": 4, "Finance": 1}. Use your best judgement to categorize roles into fields '
        "(e.g. IT, Finance, Marketing, Healthcare, Education, Sales, Engineering, Business). "
        "Software, data, analytics, business intelligence, cloud, cybersecurity and other "
        "technology roles must ALL be filed under the single field name \"IT\" - do not invent "
        "separate names such as \"Data Analytics\" or \"Software\". "
        "If experience is not clearly tied to a field, categorize it under \"General\".\n"
        "  - certificates_by_industry: an object mapping each industry to a LIST of the "
        'exact certificate names the candidate holds in that industry, e.g. '
        '{"IT": ["AWS Certified Solutions Architect", "CompTIA Security+"], "FnB": ["ServSafe"]}. '
        "Certificates in software, data, analytics, business intelligence, cloud or "
        "cybersecurity (for example Tableau, Power BI, AWS, Azure, CompTIA) must be listed under \"IT\". "
        "Use an empty object {} if no certificates are mentioned.\n\n"
        "Return ONLY a JSON array, one object per resume, with exactly these five keys. "
        "Do not include any explanation, markdown formatting, or extra text - JSON only."
    )
