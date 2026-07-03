# EchoLoop — Multi-Agent Flashcard Generator for German Learners

<!-- Track: Agents for Good (education) -->
<!-- Word budget: ≤ 2,500 words total -->

---

## 1 Motivation

<!-- Personal story — why this problem matters to YOU. Already drafted. -->

I live and work in Germany many years already.
Over that time I have studied German on many different levels and tried many different methods and apps.
Unfortunately, none of the existing apps (e.g. Duolingo, Memrise, Anki) satisfied my needs.
I study language with a private tutor.
After each lesson I leave with a list of words and phrases to memorize.
Creating flashcards from this list is time consuming.
Besides, I believe two features are missing in the existing apps.
First, memorizing words and their direct translations is far less efficient than memorizing them in the context of a natural sentence.
Second, expanding into synonyms is extremely useful for building a rich vocabulary.
So, I decided to build a flashcard app that solves these problems.

In addition, I work as a data scientist and ML engineer but until recently avoided using LLMs and especially agentic coding in my day-to-day work.
This kaggle competition seemed to be a great opportunity to change that and I must admit, I was not disappointed.
I have learned a lot and got a huge boost in my productivity and confidence in using agentic tools.

## 2 Problem Statement

<!-- Rubric: Core Concept & Value (10 pts) — "problem relevance to the track" -->
<!-- Generalize the personal pain into a broader problem: why existing tools fail intermediate-to-advanced learners. -->

## 3 Solution Overview

<!-- Rubric: Core Concept & Value — "use of agents should be clear, meaningful and central" -->
<!-- High-level: what EchoLoop does, the three-agent pipeline, and how it differs from alternatives. -->
<!-- Include the comparison table (EchoLoop vs Duolingo vs Anki vs Lingvist). -->

### 3.1 Why Agents?

<!-- Rubric: Video criteria — "Why agents? How can agents uniquely help solve that problem?" -->
<!-- Explain why a multi-agent approach is better than a single prompt or rule-based system. -->

### 3.2 Key Features

<!-- Bullet list of user-facing capabilities: context sentences, synonyms, spaced repetition, MCP verification, etc. -->

## 4 Architecture

<!-- Rubric: Technical Implementation (50 pts) — "quality of your solution's architecture" -->
<!-- Include the Mermaid system architecture diagram from README. -->

### 4.1 Multi-Agent Pipeline (ADK)

<!-- Key concept: Agent / Multi-agent system (ADK) — demonstrate in Code -->
<!-- Describe ContextAgent → SynonymsAgent → RepetitionEngine flow. -->

### 4.2 MCP Dictionary Server

<!-- Key concept: MCP Server — demonstrate in Code -->
<!-- Describe the FastMCP Stdio server, Wiktionary API client, and how it grounds LLM output. -->

### 4.3 Spaced Repetition Engine

<!-- SM-2 algorithm, CEFR level estimation, review scheduling logic. -->

### 4.4 Data Layer

<!-- SQLite storage, CardStore adapter, schema design. -->

## 5 Key Concepts Demonstrated

<!-- Rubric: Evaluation — "must demonstrate at least 3 of 6 key concepts" -->
<!-- Summary table mapping each concept to where it is demonstrated (code/video). -->

### 5.1 Antigravity

<!-- Key concept: Antigravity — demonstrate in Video -->
<!-- How Antigravity was used during development: agentic coding, iterative design, etc. -->

### 5.2 Agent Skills (Agents CLI)

<!-- Key concept: Agent skills — demonstrate in Code or Video -->
<!-- agents-cli scaffold, eval, deploy usage. -->

### 5.3 Security Features

<!-- Key concept: Security features — demonstrate in Code or Video -->
<!-- Google SSO, email whitelist, no API keys in code, .env pattern, Secret Manager. -->

### 5.4 Deployability

<!-- Key concept: Deployability — demonstrate in Video -->
<!-- Terraform IaC, deploy.sh, Cloud Run, Docker, one-command deployment. -->

## 6 The Build — Development Journey

<!-- Rubric: Writeup (10 pts) — "your project's journey" -->
<!-- Narrative of how the project evolved: scaffolding → agents → MCP → auth → deployment. -->
<!-- Mention the role of Antigravity / agentic coding in the process. -->

## 7 Results and Demo

<!-- Rubric: Video (10 pts) — "demo of your solution" -->
<!-- Screenshots or embedded images showing the app in action. -->
<!-- Reference the YouTube video link. -->

## 8 Limitations and Future Work

<!-- Honest assessment of current limitations and what would come next. -->

## 9 Conclusion

<!-- Wrap up: what was built, what was learned, and the broader impact. -->

---

## Links

<!-- Required submission assets -->

- **GitHub Repository**: <!-- URL -->
- **Live Demo**: <!-- Cloud Run URL -->
- **YouTube Video**: <!-- URL, ≤ 5 min -->
