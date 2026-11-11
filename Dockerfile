FROM python:3.14-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir google-genai

COPY app.py models.py io_manager.py ai_manager.py logic_manager.py data_manager.py review_service.py ./
COPY requirements.txt ./

COPY tests/ ./tests/

COPY resumes/ ./resumes/

RUN mkdir -p scannedResume data

CMD ["python", "app.py"]