# EchoLoop 🔁

A multi-agent, multi-modal language learning application that utilizes collaborative LLM agents to dynamically generate contextual, visual, and adaptive flashcards powered by spaced repetition.

This project is a submission to the Kaggle [AI Agents: Intensive Vibe Coding Capstone Project](https://www.kaggle.com/competitions/vibecoding-agents-capstone-project). More info about the submission requirements are [here](./KAGGLE.md).

---

## Usage Guide

### Prerequisites

| Tool | Install |
|---|---|
| [Python 3.14+](https://www.python.org/downloads/) | Required runtime |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Fast Python package manager (`curl -LsSf https://astral.sh/uv/install.sh \| sh`) |
| [Gemini API key](https://aistudio.google.com/apikey) | Free key from Google AI Studio |

### 1 — Clone the repository

```bash
git clone https://github.com/khrapovs/echoloop-multiagent-flashcards.git
cd echoloop-multiagent-flashcards
```

### 2 — Install dependencies

```bash
uv sync
```

This creates a `.venv` and installs all dependencies (including Streamlit) in one step.

### 3 — Set your API key

```bash
export GOOGLE_API_KEY="your-key-here"
```

> **Tip:** Add this line to your shell profile (`.zshrc`, `.bashrc`, etc.) so you don't have to repeat it.

### 4 — Run the UI

```bash
uv run echoloop
```

This opens the EchoLoop Streamlit interface in your browser at `http://localhost:8501`.

---

## Development

### Run unit tests

```bash
uv run pytest tests/unit
```

### Run integration tests (requires `GOOGLE_API_KEY`)

```bash
uv run pytest tests/integration -m "not e2e"
```
