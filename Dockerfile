FROM python:3.14-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir google-genai

#All the files needed for docker to run smmothly
COPY app.py ./
COPY Models/ ./Models/
COPY AIManager/ ./AIManager/
COPY IOManager/ ./IOManager/
COPY LogicManager/ ./LogicManager/
COPY DataManager/ ./DataManager/
COPY requirements.txt ./

#For the automated tests files the team created 
COPY tests/ ./tests/

#Copy all the resume that is in the resume folders
COPY resumes/ ./resumes/

#This is to create a archive folder for scanned resumes and the folder that holds the database
RUN mkdir -p scannedResume data

CMD ["python", "app.py"]
