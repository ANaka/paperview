FROM python:3.8-slim

# Install the system dependencies for the dependencies in the .toml file
RUN apt-get update && apt-get install -y \
    libmagickwand-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a new user and switch to it
RUN adduser --disabled-password --gecos '' paperview
USER paperview

# Create a new virtual environment and activate it
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install the dependencies from the .toml file
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-dev

# Copy the application code to the container
COPY . /app
WORKDIR /app

# Run the application
CMD ["python", "-m", "paperview"]
