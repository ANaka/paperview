FROM python:3.8-slim

# install dependencies
RUN apt-get update && apt-get install -y \
    libmagickwand-dev \
    && rm -rf /var/lib/apt/lists/*

# Configure Poetry
ENV POETRY_VERSION=1.2.0
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

# Install poetry separated from system interpreter
RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

# Add `poetry` to PATH
ENV PATH="${PATH}:${POETRY_VENV}/bin"

# copy your repository files into the container
COPY . /app

WORKDIR /app

# Install dependencies
RUN poetry install
