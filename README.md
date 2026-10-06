# 📈 Business Lead Inbox · Cloud

The **Business Lead Inbox** (Jev routes every business email, qualifies sales leads with an A–D grade, puts hot leads first, and an LLM drafts replies), made **safe to deploy publicly on Streamlit Cloud**.

Anyone with the link can explore it:
- **Try the sample inbox:** one click, 100 business emails, nothing to set up.
- **Connect your Gmail:** use your own inbox with a Google **app password**. Your mailbox is visible only to you, only in your session.

## Why an app password? (the problem it solves)

The usual "Sign in with Google" button needs the app owner to register a Google Cloud app, and **Google only lets unknown, public users connect Gmail to an app after a formal verification and paid security review**. Without that, only people the owner adds by hand (up to 100 "test users") can sign in. A public demo can't work that way.

An **app password** avoids that entirely. It's the standard way mail programs (Apple Mail, Outlook, Thunderbird) connect to Gmail over **IMAP**. Each visitor creates their own key for their own mailbox, so no Google Cloud app, no verification and no test-user list are involved. It's also free.

## How a visitor gets an app password (about 2 minutes)

1. **Turn on 2-Step Verification:** [myaccount.google.com/security](https://myaccount.google.com/security) → *2-Step Verification*. Google offers app passwords only when it's on.
2. **Create the app password:** open [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), type a name such as *Business Lead Inbox*, then click **Create**.
3. **Copy the 16-letter password** Google shows (e.g. `abcd efgh ijkl mnop`).
4. In the app, enter your **Gmail address** and that **app password**, then click **Connect and fetch**.

**To switch it off later:** [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) → 🗑️ next to the name. It stops working immediately.

*Can't create one?* Some work (Google Workspace) accounts have app passwords disabled by their admin, and Advanced Protection accounts can't use them. The sample inbox still works.

The same guide is built into the app, under **How do I get an app password, and why does the app need it?**

## How visitors' data is protected

| | |
|---|---|
| **App password** | Kept only in the visitor's browser session, in memory. Never written to disk, logged, or visible to the app owner or other visitors. Closing the tab or clicking **Disconnect Gmail** forgets it. |
| **What the app does with it** | **Reads** the inbox (opened read-only; emails stay unread) and **saves reply drafts** to the visitor's Drafts, threaded with the original. It never sends, deletes, moves or labels anything. |
| **Their emails** | Stored in a **private database for that session only** (one file per visitor), deleted automatically within 12 hours. Visitors never see each other's data. |
| **AI keys** | Each visitor pastes their own Jev / LLM keys in the sidebar (session only), or uses demo mode. The app owner's keys are never in the app. |
| **Owner's Gmail** | Not connected here. There are no Google sign-in files in this project. |

Emails a visitor connects are sent to Jev (and to their chosen LLM for drafts or comparisons) **using their own keys**.

## Deploy on Streamlit Community Cloud (free)

1. The code is on GitHub: [AnjaniMalhotra/JEV-Business-Leads-Inbox](https://github.com/AnjaniMalhotra/JEV-Business-Leads-Inbox), with this folder as the repo root so `.streamlit/config.toml` (the theme) is picked up.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app** → pick the repo and branch. Set the main file to `app.py`.
3. **Advanced settings → Python 3.12.** No secrets are needed.
4. Click **Deploy**. Share the link.

Costs: hosting is free for public apps; app passwords and IMAP are free. AI usage is paid by each visitor's own keys, or is free in demo mode.

## Run it locally

```bash
git clone https://github.com/AnjaniMalhotra/JEV-Business-Leads-Inbox.git
cd JEV-Business-Leads-Inbox
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

## Files that differ from the single-user Gmail version

```
gmail/client.py    IMAP sign-in with Gmail address + app password (no Google Cloud app)
gmail/fetch.py     read the inbox over IMAP, read-only; Gmail search syntax; attachments included (up to 5 MB each)
gmail/drafts.py    save a reply into the visitor's Drafts folder, threaded with the original
ui/gmail_ui.py     "Connect your Gmail" form + in-app guide; app password kept in this session only
ui/data.py         one private database per visitor session (deleted after 12 hours)
triage/config.py   lets the UI choose the database per session
views/inbox.py     empty inbox: Connect your Gmail, or Try the sample inbox
```

Everything else (Jev questions, lead scoring, pages, theme, tests) is the same as `smart inbox gmail`.

Tests: `.venv/bin/python -m pytest -q`. There are 29, all offline, using a fake mail server; one proves two visitors never see each other's emails.
