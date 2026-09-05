FROM node:22-bookworm-slim AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
COPY backend/ ./backend/
RUN pip install --no-cache-dir .
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

RUN python -c "from backend.app.domains.materials.corpus import load_curated_material_corpus; from backend.app.domains.materials.curated_import import validate_curated_material_media; validate_curated_material_media(load_curated_material_corpus())"

RUN addgroup --system herbwire \
    && adduser --system --ingroup herbwire herbwire \
    && chown -R herbwire:herbwire /app
USER herbwire

EXPOSE 8000
CMD ["python", "-m", "backend.app.web"]
