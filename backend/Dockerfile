FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Runtime PostgreSQL driver required by SQLAlchemy postgresql:// URL
RUN pip install --no-cache-dir psycopg2-binary==2.9.10

# Ensure backend runtime dependencies are installed
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt
RUN python -m pip install --no-cache-dir psycopg2-binary==2.9.10
