# EchoLoop 🔁

A multi-agent, multi-modal language learning application that utilizes collaborative LLM agents to dynamically generate contextual, visual, and adaptive flashcards powered by spaced repetition.

This project is a submission to the Kaggle [AI Agents: Intensive Vibe Coding Capstone Project](https://www.kaggle.com/competitions/vibecoding-agents-capstone-project). More info about the submission requirements are [here](./KAGGLE.md).

## User Guide

Clone the repository
```bash
git clone https://github.com/khrapovs/echoloop-multiagent-flashcards.git
cd echoloop-multiagent-flashcards
```

Install dependencies:
```bash
uv sync
```

Set your API key:
```bash
export GOOGLE_API_KEY="your-key-here"
```

> **Tip:** Add this line to your shell profile (`.zshrc`, `.bashrc`, etc.) so you don't have to repeat it.

Run the UI:
```bash
uv run echoloop
```
This opens the EchoLoop Streamlit interface in your browser at `http://localhost:8501`.

## Development

Run unit tests:
```bash
uv run pytest tests/unit
```

Run integration tests (requires `GOOGLE_API_KEY`):
```bash
uv run pytest tests/integration
```
