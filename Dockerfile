FROM python:3.14-slim

RUN pip install --no-cache-dir uv==0.11.21

WORKDIR /code

COPY ./pyproject.toml ./README.md ./uv.lock* ./

COPY ./src ./src

RUN uv sync --frozen

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "echoloop.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
