CREATE TABLE IF NOT EXISTS emails (
    id                INTEGER PRIMARY KEY,
    sender            TEXT NOT NULL,
    subject           TEXT NOT NULL,
    body              TEXT NOT NULL,
    received_at       TEXT NOT NULL,
    tags              TEXT DEFAULT '',
    recipient         TEXT DEFAULT 'hello@northwind.io',
    html              TEXT,                  -- formatted version of the body, if the email has one
    attachments       TEXT DEFAULT '[]',     -- JSON list of {name, mime, size, data (base64) or attachment_id}
    gmail_id          TEXT UNIQUE,           -- set for emails loaded from Gmail
    thread_id         TEXT,
    message_id        TEXT,                  -- the Message-ID header, for threaded reply drafts
    gold_category     TEXT,
    gold_urgency      INTEGER,
    gold_action       TEXT,
    gold_route_to     TEXT,
    gold_needs_reply  INTEGER,
    gold_buying_intent INTEGER                -- 0-3, leads only (0 for other emails)
);

-- Latest triage per email (the live inbox)
CREATE TABLE IF NOT EXISTS triage (
    email_id           INTEGER PRIMARY KEY REFERENCES emails(id),
    source             TEXT NOT NULL,         -- jev | rules:<name>
    model              TEXT,
    answers_json       TEXT NOT NULL,         -- the model's original answers, never modified
    probabilities_json TEXT,
    confidence_json    TEXT,
    priority           REAL,
    bucket             TEXT,
    needs_review       INTEGER,
    reviewed           INTEGER DEFAULT 0,
    latency_ms         REAL,
    input_tokens       INTEGER,
    output_tokens      INTEGER,
    cost_usd           REAL,
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS corrections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id    INTEGER REFERENCES emails(id),
    field       TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    email_id    INTEGER PRIMARY KEY REFERENCES emails(id),
    text        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'draft',  -- draft | edited
    model       TEXT,
    gmail_draft_id TEXT,                     -- set once saved to Gmail Drafts
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    mode            TEXT NOT NULL,            -- jev | llm
    model           TEXT,
    email_id        INTEGER REFERENCES emails(id),
    answers_json    TEXT,
    confidence_json TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    cost_usd        REAL,
    latency_ms      REAL,
    parse_error     INTEGER DEFAULT 0,
    error           TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bench_run ON benchmark_runs(run_id, mode);
