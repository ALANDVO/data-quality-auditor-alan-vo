# Contributing to data-quality-auditor-alan-vo

## Development Setup

```bash
git clone https://github.com/ALANDVO/data-quality-auditor-alan-vo.git
cd data-quality-auditor-alan-vo

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend pytest backend/tests

# Frontend
cd frontend
npm install
npm test
npm run build
```

## Testing Guidelines

- Python backend: `PYTHONPATH=backend pytest backend/tests`
- Frontend: `npm test`
- Never commit credentials or API keys. Synthetic tokens in test fixtures must not match live key patterns.

---

**Alan Vo** | alanvo@gmail.com | [GitHub](https://github.com/ALANDVO)
