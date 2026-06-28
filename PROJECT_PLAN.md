# EchoLoop Architecture and Implementation Plan

EchoLoop is a language-learning flashcard generator built as a multi-agent application. It turns simple German vocabulary inputs into rich, contextual, illustrated study cards (German to English) complete with context, difficulty estimation, synonyms, and spaced repetition scheduling.

We are designing this application using **Google's Agent Development Kit (ADK)** and deploying it to **Google Cloud Platform (GCP)**.

---

## Architecture & Technology Stack

- **Orchestration**: ADK (Agent Development Kit) agents coordinating sequentially.
- **Model**: Google Gemini Developer API models (e.g., `gemini-1.5-flash` or newer).
- **Deployment Target**: Google Cloud Platform (using `agent_runtime` or `cloud_run` via `agents-cli`).
- **Database**: Normalized SQLite database for cards, examples, synonyms, and reviews.
- **Frontend**: Streamlit (Python-only UI) for the MVP prototype.
- **Language Scope**: German (target language) to English (native/base language).

---

## User Flow — Card Generation

```
User enters one German word
        │
        ▼
SynonymsAgent  →  returns up to 5 synonyms
        │
        ▼
UI shows original word + synonyms as a checklist
User deselects any words they don't want cards for
        │
        ▼
[Generate] button
        │
        ▼
AgentPipeline.generate_card_batch(selected_words, inferred_level)
  ├── Infers user level once (RepetitionEngine.get_inferred_user_level())
  ├── For each selected word (original + checked synonyms):
  │     ContextAgent  →  FlashcardContext
  │     → Save card + example to CardStore   (skip if word already exists)
  │     → Stream card to UI as it arrives
  └── After all complete: show summary panel listing saved words
      (words that failed are listed separately at the end)
```

```mermaid
graph TD
    Client[Streamlit UI] -->|1. Enter word| SynonymsAgent[Synonyms Agent]
    SynonymsAgent -->|2. Return synonym list| Client
    Client -->|3. User checks words, clicks Generate| Pipeline[AgentPipeline.generate_card_batch]

    Pipeline -->|4. Infer user level once| RepetitionEngine[Repetition Engine]
    RepetitionEngine -->|reads level distribution| CardStore[Card Store · SQLite]

    subgraph AgentPipeline [ADK Agent Generation Pipeline — per selected word]
        Pipeline -->|5. For each word| ContextAgent[Context & Difficulty Agent]
        ContextAgent -..->|Future Extension| ImageAgent[Image Illustration Agent]
    end

    ContextAgent -->|6a. Stream card to UI| Client
    ContextAgent -->|6b. Save card + example| CardStore

    Client -->|Starts study session| RepetitionEngine
    RepetitionEngine -->|Queries & updates SM-2 state| CardStore
```

---

## Module Breakdown

### 1. Agentic Generation Pipeline (`AgentPipeline`)
- **Seam**: A single batch entry point called by the UI.
- **Implementation**: Written using the Google ADK Python SDK.
- **Orchestration**: Runs `SynonymsAgent` once on the entered word to get candidate words, then runs `ContextAgent` sequentially for each user-selected word (original + synonyms). Image generation is deferred as a future hook.
- **Interface**:
  - `def get_synonyms(word: str) -> SynonymsOutput` — calls `SynonymsAgent`; returns the structured synonym list so the UI can render the checklist.
  - `def generate_card_batch(words: list[str], inferred_level: str) -> Iterator[FlashcardResult]` — yields one `FlashcardResult` per word as each `ContextAgent` call completes; skips words already in the DB; captures per-word failures without aborting the batch.
- **`FlashcardResult`** (new data class):
  - `word: str`
  - `card: FlashcardContext | None` — `None` on failure or if word was already in DB
  - `status: Literal["saved", "skipped", "failed"]`
  - `error: str | None`

### 2. Storage Adapter (`CardStore`)
- **Seam**: An interface managing raw data persistence and queries.
- **Implementation**: SQLite database adapter using a normalized schema.
- **Schema**:
  - `cards`: `id`, `word`, `translation`, `detected_level`, `easiness_factor`, `interval_days`, `repetitions`, `next_review_date`
  - `examples`: `id`, `card_id` (FK), `sentence`, `translation`
  - `synonyms`: `id`, `card_id` (FK), `synonym_word`, `translation`
  - `reviews`: `id`, `card_id` (FK), `timestamp`, `rating_score`
- **Depth**: Hides raw connections, cursors, foreign key constraints, indices, and database-specific SQL queries.

### 3. Spaced Repetition Engine (`RepetitionEngine`)
- **Seam**: Coordinates study session assembly and calculates learning metrics.
- **Depth**: Houses the SM-2 algorithm calculation logic. Infers the user's level dynamically by analyzing the distribution of `detected_level` values in the existing `cards` database.
- **Interface**:
  - `def calculate_next_review(card: Card, review_score: int) -> CardMetrics`
  - `def get_inferred_user_level() -> str`

### 4. User Interface (`UI`)
- **Seam**: Interactive Streamlit interface — two pages.
- **Depth**: Hides view layout, form handling, streaming card display, progress bars, and transient session queues.

#### Page 1 — Add Card
1. Word input form.
2. On submit: call `AgentPipeline.get_synonyms(word)` → display checklist of original word + synonyms.
3. User checks/unchecks words → clicks **Generate**.
4. Calls `AgentPipeline.generate_card_batch(selected, inferred_level)` and streams results: each card appears as it arrives.
5. After all complete: summary panel — list of saved words + any failures.

#### Page 2 — Review (Interactive Session-based Review)
- Fetches all due cards upfront into `st.session_state`.
- Shows word prompt → reveal → 0–5 SM-2 rating → advance.
- End of session: summary + option to start another session.

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Level inference timing | Once per batch | Simpler; consistent context for all cards in the batch |
| Already-in-DB words | Skip silently, status = `"skipped"` | Avoids duplicates without blocking the user |
| Batch failure handling | Skip failed words, report at end | Partial success is more useful than all-or-nothing |
| Card streaming | Stream as each arrives | Reduces perceived latency for large batches |
| Post-generation UX | Summary panel, stay on Add Card page | User may want to add another word immediately |

---

## Verification Plan

### Automated Tests
- Python unit tests (`uv run pytest`) verifying the SM-2 calculations in `RepetitionEngine` and CRUD joins in `CardStore`.
- Unit tests for `AgentPipeline.generate_card_batch` covering skip, failure, and happy-path status values.
- ADK-integrated evaluations (`agents-cli eval`) to verify agent language outputs and translation accuracy.

### Manual Verification
- Testing interactive card creation and reviews using the local Streamlit dashboard.

---

## Deployment Architecture (GCP)

To keep the MVP simple, cost-effective, and fully containerized, we target **Google Cloud Run** for hosting both components. Cloud Run scales to zero, minimizing idle running costs.

### Architecture Topology

```mermaid
graph LR
    User([User's Browser]) -->|HTTPS: Port 8501| UI[Streamlit UI Container · Cloud Run]
    UI -->|Local File system / Mount| SQLite[(SQLite Database: echoloop.db)]
    UI -->|In-Process ADK Engine| Agents[Agent Modules: context_agent & synonyms_agent]
    Agents -->|gRPC / REST API| Gemini[Gemini Developer API / Vertex AI]
```

* **Single Consolidated Container Deployment (Streamlit + Agents + DB)**:
  * Since our current architecture runs the ADK agents in-process via `runner.py` (which configures the SDK and makes calls to Gemini), we do not need to deploy a separate FastAPI agent server for the Streamlit UI to work.
  * The Streamlit UI container runs as a Cloud Run Service. It executes the Python application, imports the agents locally, and writes directly to `echoloop.db`.
  * **Persistent Storage**: Cloud Run container filesystems are ephemeral. For the SQLite database (`echoloop.db`) to survive container restarts, we mount a **Cloud Storage bucket** as a network volume using Cloud Run's integrated Cloud Storage volume mounts (configured as a writeable mount at `/data`), and redirect our DB path to `/data/echoloop.db`.
  * **Vertex AI / Gemini API Integration**: Cloud Run uses its default Service Account (with appropriate IAM roles like `Vertex AI User`) to authenticate calls to Gemini seamlessly via Application Default Credentials (ADC).

---

## Deployment Plan & Steps

### Prerequisites
1. **Google Cloud SDK (`gcloud`)** installed and authenticated.
2. An active GCP Project with billing enabled.
3. Enabled APIs: Cloud Run (`run.googleapis.com`), Artifact Registry (`artifactregistry.googleapis.com`), and Vertex AI (`aiplatform.googleapis.com`).

### Step 1: Create a Cloud Storage Bucket for SQLite Persistence
Create a GCS bucket to store the SQLite file so it persists across container restarts:
```bash
gcloud storage buckets create gs://echoloop-sqlite-store --location=us-east1
```

### Step 2: Write a Dockerfile
Create a `Dockerfile` at the root of the project to package the application.
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files and install them
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application files
COPY echoloop/ ./echoloop/

# Expose Streamlit port
EXPOSE 8501

# Environment variable to point database to mounted GCS bucket path
ENV ECHOLOOP_DB_DIR=/data
ENV PORT=8501

# Run the UI app
CMD ["uv", "run", "streamlit", "run", "echoloop/ui/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Step 3: Configure Database Directory Override in Code
We update `constants.py` to check for the `ECHOLOOP_DB_DIR` environment variable, defaulting to `/data/echoloop.db` when deployed, but fallback to the repository root locally.

### Step 4: Build and Deploy to Google Cloud Run
Deploy using the inline build capability of Cloud Run (which leverages Cloud Build under the hood):
```bash
gcloud run deploy echoloop-ui \
    --source . \
    --port 8501 \
    --region us-east1 \
    --allow-unauthenticated \
    --update-env-vars GOOGLE_GENAI_USE_VERTEXAI=True \
    --add-volume=name=sqlite-volume,type=gcs,bucket=echoloop-sqlite-store \
    --add-volume-mount=volume=sqlite-volume,mount-path=/data
```

### Step 5: Verify the Deployed App
Retrieve the Service URL from the command output and open it in your browser. Verify that words can be added, and that refresh/restarts preserve the database card count.
