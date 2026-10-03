FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONPATH=/app/src \
    APP_ENVIRONMENT=production

WORKDIR /app

# requirements.txt is exported from uv.lock (see README)
COPY requirements.txt .
RUN pip install --require-hashes -r requirements.txt

# The package isn't pip-installed; PYTHONPATH makes src/openai_api importable
COPY src/ src/

# Create a non-root user and run the app as this user
RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# --factory: uvicorn calls create_app() to build the app
CMD ["uvicorn", "openai_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
