# AI Resume Analyzer

## Overview

This project combines deterministic resume scoring with AI-generated coaching.
The backend still extracts skills, calculates semantic similarity, and stores
analysis history. The AI layer now supports a BYOK flow, with Gemini as the
first provider and OpenAI or Hugging Face as optional fallbacks.

## What The App Does

For each resume analysis, the app generates:

- AI fit summary
- Resume improvement recommendations
- Job alignment advice
- Tailored interview questions
- Why each question matters
- Strong answer points
- Interview answer strategy
- 7-day study plan
- Recruiter pitch

## BYOK Flow

The frontend includes an API Keys settings page where users can save their own
Gemini, OpenAI, or Hugging Face credentials locally in the browser. Those keys
are sent only with analysis requests from that browser session.

The home page includes an Add API key here button that opens the settings page.
The settings page also includes a Home button and direct links to the provider
key pages.

OpenAI API keys require billing to be enabled or a paid tier.

## Key Files

- [backend/app/services/ai_coach.py](backend/app/services/ai_coach.py)
- [backend/app/api/routes.py](backend/app/api/routes.py)
- [frontend/index.html](frontend/index.html)
- [frontend/settings.html](frontend/settings.html)
- [frontend/settings.js](frontend/settings.js)
- [frontend/app.js](frontend/app.js)
- [frontend/styles.css](frontend/styles.css)
- [.env.example](.env.example)

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8016
```

### Frontend

```bash
cd frontend
python -m http.server 5516
```

Open:

```text
http://127.0.0.1:5516
```

## Environment Variables

The sample file is [.env.example](.env.example).

Recommended defaults:

```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
ENABLE_OPENAI=true
```

You can leave `OPENAI_API_KEY` empty if you only want to use Gemini.

## Provider Priority

The backend tries providers in this order:

1. Gemini
2. Hugging Face
3. OpenAI

If a provider fails, the service falls back to the next configured option.

## API Key Links

The settings page includes direct links to:

- Gemini API keys: https://aistudio.google.com/app/apikey
- OpenAI API keys: https://platform.openai.com/api-keys
- Hugging Face tokens: https://huggingface.co/settings/tokens

## Run Tests

```bash
cd backend
pytest -q
```

## Notes

- Tests mock the AI boundary so they do not spend API credits.
- The frontend stores user-entered keys locally in the browser.
- OpenAI is supported, but the UI warns users that it needs billing or a paid
  tier.
