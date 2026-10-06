# Image prompts: Smart Inbox · Gmail architecture diagrams

Five **Excalidraw-style architecture diagrams** that together cover the whole repo: wide landscape, clean, icon-first, minimal text.

## How to use

1. Copy the **Style block**, then add **one diagram prompt** after it.
2. Generate in **landscape 16:9** (Midjourney: `--ar 16:9 --style raw`; DALL·E / GPT image: "wide 16:9"; Ideogram: "16:9, Design").
3. Add the **Avoid** line as the negative prompt where your tool supports one.
4. Each prompt lists the **only labels allowed** (1–2 words each). If a label comes out garbled, fix it in Excalidraw afterwards.

### Style block (paste before every prompt)

> Excalidraw-style hand-drawn architecture diagram, wide landscape 16:9, pure white background, clean and spacious composition with generous whitespace, sketchy hand-drawn black outlines with slight roughness, soft pastel fills with a hatched texture, rounded rectangles, hand-drawn arrows with small arrowheads, large simple flat icons inside each box (icons are the main visual, text is minimal), a few short labels in a casual handwritten font, consistent colour coding, left-to-right flow, balanced layout, no shadows, no gradients, no 3D, looks like a polished whiteboard sketch by a software architect.

### Colour legend (the same in every image)

| Colour | Means |
|---|---|
| Navy blue | **Jev** (decision model) |
| Orange | **LLM** (Gemini / OpenAI / Claude) |
| Red | **Gmail / Google** |
| Green | **Human** (you) |
| Grey | **Storage** (SQLite, files) |
| Purple | **Python code / rules** |
| Yellow | **Security / privacy** |

### Avoid (negative prompt)

> photorealistic, 3D render, gradients, drop shadows, dark background, dense paragraphs of text, long sentences, tiny unreadable text, misspelled words, code snippets, watermark, logos of real companies, clutter, isometric, neon

---

## 1 · The big picture

*Covers: the whole system end to end (`app.py`, `views/`, `triage/pipeline.py`)*

> A wide end-to-end overview in five zones from left to right. Zone 1: a red envelope stack icon labelled "Gmail". Arrow to Zone 2: a purple gear-and-funnel icon labelled "Fetch". Arrow to Zone 3, the largest, centred and highlighted: a navy-blue brain-with-lightning icon labelled "Jev", with thirteen tiny question chips orbiting it. Arrow to Zone 4: a purple balance-scale icon labelled "Decide", feeding four stacked inbox trays coloured red, amber, blue and grey, with a small flame badge on the top tray for hot leads. Arrow to Zone 5: a green person-at-laptop icon labelled "You". Below Zone 5, an orange robot-with-pen icon labelled "LLM", with a dashed arrow curving back to the red envelope labelled "Draft". Under the whole flow, a grey database cylinder labelled "SQLite" with thin dotted lines up to each zone. Only these labels: Gmail, Fetch, Jev, Decide, You, LLM, Draft, SQLite.

## 2 · Gmail in and out (fetch, safe viewing, reply drafts, privacy)

*Covers: `gmail/client.py`, `gmail/fetch.py`, `gmail/drafts.py`, `ui/gmail_ui.py`, `ui/safe_html.py`, `ui/email_view.py`, `ui/email_reply.py`, `triage/reply.py`, `db/gmail_store.py`, `secrets/`*

> A three-zone landscape separated by yellow dashed fences. Left zone, "Google": a red cloud with two permission badges, an eye (read) and a pencil (drafts), next to a crossed-out paper plane and a crossed-out trash can (never sends, never deletes). Middle zone, "Your app", as a loop. The top path goes left to right: a red envelope stack, a refresh "Fetch" button icon, then a purple gear machine splitting each email into four small icons (plain-text page, formatted web page, paperclip, chain-link thread). Then a large yellow shield filter (scissors, brick wall, closed eye) producing a clean framed email card. The bottom path goes right to left: three small tone faces (smile, formal, lightning), then an orange robot-with-pen writing a page, then a green person editing it with a pencil, then a red envelope folder with a chain link labelled "Drafts", arriving back in the Google zone. Right zone, "You": a green person holding the only paper-plane send button, and a yellow vault with a key (token) inside a grey locked folder. Only these labels: Google, Fetch, Shield, LLM, Drafts, You, Token.

## 3 · The Jev decision engine (pipeline, 8 questions, decision layer)

*Covers: `triage/pipeline.py`, `triage/text.py`, `triage/rules.py`, `triage/schema.py`, `triage/jev_client.py`, `triage/decide.py`, `config/app.yaml`*

> A left-to-right engine with four circled step numbers. Step 1, purple: a broom sweeping an envelope, labelled "Clean". Step 2, purple: a fast-forward icon with a tiny robot-reply bubble, labelled "Rules", with a dashed bypass arrow (marked with a small coin, meaning free) skipping step 3. Step 3, the largest, navy: a brain with a lightning bolt labelled "Jev", with thirteen spokes fanning out in three icon groups: a multiple-choice list header (folder, footsteps, team icons), a slider header (speedometer) and a yes/no toggle header (reply arrow, calendar flag, warning triangle, person silhouette). Each answer icon has a tiny confidence bar. A second cluster of five spokes, in a dashed box with a target icon, holds the lead questions (a rising thermometer for intent, a puzzle piece for fit, a crown for decision maker, a coin for budget, an hourglass for timeline). A bracket around all spokes is marked with a lightning bolt (one pass). Step 4, purple: a balance scale with five little sliders, labelled "Decide", plus a small target gauge producing grade cards A to D (A with a flame), pointing into four stacked trays (red, amber, blue, grey) labelled "P1", "P2", "P3", "P4". A red lightning shortcut runs from the warning triangle straight to P1. Below step 4, a turnstile gate with a confidence gauge sends low-confidence emails down to a green person with a magnifying glass, labelled "Review". Only these labels: Clean, Rules, Jev, Decide, Leads, P1, P2, P3, P4, Review.

## 4 · Trust and evaluation (human in the loop, accuracy, compare models)

*Covers: `ui/email_decision.py`, `db/feedback.py`, `ui/accuracy.py`, `views/dashboard.py`, `views/compare.py`, `triage/benchmark.py`, `triage/scoring.py`, `db/benchmarks.py`*

> Two halves side by side. Left half, a circular feedback loop of hand-drawn arrows: a navy brain producing answer cards (one card has a small padlock: original answers are never changed), then a green person at a screen with a green check and a pencil icon, labelled "Check", then a grey drawer with a gold star answer key, labelled "Answer key", then a dashboard showing a dark-diagonal heatmap and rising bars over confidence gauges, labelled "Accuracy", with an arrow back to the brain. Right half, a race track: the same envelopes split into lanes. Top lane: a fast navy brain with a short stopwatch and a single coin. Middle lanes: slower orange robots with long stopwatches and coin stacks. Bottom lane, "Smart combo": the navy brain handles most envelopes and a dashed side path sends only a few question-marked envelopes to an orange robot. The lanes end at a hand-drawn scoreboard with icon columns (stopwatch, coin stack, target, warning triangle) and a small trophy on the navy row. Only these labels: Check, Answer key, Accuracy, Jev, LLM, Smart combo.

## 5 · Under the hood (screens, code layers, data, keys, tests)

*Covers: `views/`, `ui/`, `triage/`, `gmail/`, `db/schema.sql`, `ui/sidebar.py`, `triage/config.py`, `triage/mock.py`, `tests/`*

> A wide blueprint in three columns. Left column: a hand-drawn browser wireframe with a top bar of three tab icons (inbox tray, bar chart, two opposing arrows), a collapsible sidebar with a key icon and a slider icon, a toolbar (magnifier, coloured pills, funnel), a sparkle button and a refresh button, and email rows of squiggly lines with coloured chips. Middle column: five stacked pastel bands, each with a big icon: a monitor ("views"), building blocks ("ui"), a navy brain with purple gears ("triage", the widest band), then two side-by-side blocks, a red envelope ("gmail") and a grey database ("db"). Arrows point only downward; a no-entry sign sits on an upward arrow. Right column, top: a key ring inside a browser-session bubble with a crossed-out hard drive (keys never saved), splitting into a solid arrow to the brain and robots ("Real AI") and a dashed arrow to a practice-dummy robot ("Demo"). Right column, bottom: a dotted glass lab box with a fake envelope wearing a theatre mask, a dummy robot and a small temporary database with a clock, a crossed-out Wi-Fi sign outside, and a row of green check circles ("Tests"). Only these labels: views, ui, triage, gmail, db, Real AI, Demo, Tests.

---

### Tips for a consistent set

- Generate **diagram 1 first**, then use it as a style reference (or add "same visual style and colour legend as the previous image") for diagrams 2–5.
- If extra text appears, add: *"labels limited to the exact words listed, nothing else written anywhere"*.
- For slides, export at 1920×1080 or larger. To fix a label, import the PNG into excalidraw.com and retype it.
