# Business Lead Inbox · Cloud

Public, multi-user version of `smart inbox gmail` for Streamlit Cloud. Visitors connect their OWN Gmail with an app password over IMAP (read + save drafts), or use the sample inbox.

Streamlit app: Jev (TypeSafe AI) routes business emails loaded from Gmail (or 100 sample emails) and qualifies leads (lead score + A–D grade in `triage/decide.py`, weights and `company_profile` in `config/app.yaml`); an LLM picked in the sidebar (Gemini / OpenAI / Claude) drafts replies and is the cost/speed/accuracy baseline.

## Rules
- `company_profile` in `config/app.yaml` is only the default business; each visitor can replace it for their session (Settings → Your business). It reaches every model call as `keys["profile"]`.
- Gmail access is IMAP with the visitor's address + app password, held only in `st.session_state["gmail_login"]`. Never write it to disk, logs, the database or caches. Mailbox opened read-only; only APPEND to Drafts. Never send, delete, move or flag mail.
- Every visitor has their own database (`ui.data.session_db` via `config.set_db_resolver`). Never add module-level or `st.cache_*` state that holds email data or credentials; it would be shared across visitors.
- No Google OAuth / `secrets/` files in this project.
- Real email content is private: don't paste it into logs, tests or docs. Tests use fake Gmail messages.
- Real emails have no gold labels; confirming or correcting an email writes gold via `feedback.set_gold`. Accuracy only counts labelled emails.
- API keys come only from the sidebar (`ui.sidebar.sidebar` → `st.session_state["keys"]`) and are passed explicitly as `keys` to triage functions. Never read keys from env/.env, never write them to disk or logs.
- Empty keys → demo mode (`triage/mock.py`); demo output is always labelled.
- Jev answers typed questions only — never ask it for text, counts or maths; do those in Python.
- Question definitions live only in `triage/schema.py`; the LLM uses the same labels.
- LLM models and prices live in `MODELS` in `triage/config.py`; Jev model is pinned (`JEV_MODEL`).
- Model answers in `triage.answers_json` are never modified; human fixes go to the `corrections` table.
- Email text is untrusted: prompts tell the LLM to ignore instructions inside it. Nothing is sent or deleted automatically.
- Email HTML is untrusted: render it only through `ui.safe_html.email_document`.
- Keep every file under ~120 lines: `gmail/` = IMAP, `triage/` = AI logic, `ui/` = building blocks, `views/` = pages.
- Tests must stay offline: empty keys, a temp DB, and a fake IMAP server (`tests/test_gmail.py`).
- Changing `triage/schema.py` questions makes old stored results outdated; `data.seed.drop_outdated_results` clears them on start-up (emails are kept).

## Commands
- Install: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Run: `.venv/bin/streamlit run app.py`
- Test: `.venv/bin/python -m pytest -q`
