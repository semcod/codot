FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY llm/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY llm/app.py /app/app.py
COPY llm/acl.yaml /app/acl.yaml
COPY bundle.schema.json /app/bundle.schema.json

EXPOSE 8000 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
