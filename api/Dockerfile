# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app


# --- deps: capa cacheable, solo se reconstruye si cambian los requirements ---
FROM base AS deps
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r requirements.txt


FROM deps AS deps-dev
COPY requirements-dev.txt .
RUN /opt/venv/bin/pip install -r requirements-dev.txt


# --- dev: hot reload, el código llega por bind mount desde compose ---
FROM base AS dev
COPY --from=deps-dev /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# --- prod: sin dependencias de desarrollo, usuario sin privilegios ---
FROM base AS prod
COPY --from=deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN useradd --create-home --uid 1000 app
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
