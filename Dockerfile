FROM python:3.12-slim-bookworm AS base

LABEL org.opencontainers.image.source="https://github.com/ORNL/pygarden"
ENV PATH="/opt/venv/bin:$PATH"
CMD ["python"]

FROM base AS core-builder
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /build
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable --no-cache --python /usr/local/bin/python

FROM core-builder AS all-builder
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*
ENV CMAKE_ARGS="-DGGML_NATIVE=OFF" CMAKE_BUILD_PARALLEL_LEVEL=2
RUN uv sync --locked --no-dev --no-editable --no-cache --extra all

FROM base AS core
COPY --from=core-builder /opt/venv /opt/venv

FROM base AS all
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libstdc++6 libodbc2 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=all-builder /opt/venv /opt/venv
