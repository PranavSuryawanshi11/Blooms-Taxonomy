# Bloom's Taxonomy &mdash; Academic Studio

**Turn a course syllabus into a balanced, Bloom's-Taxonomy-calibrated, college-formatted question paper in minutes.**

> **License:** Free for personal, academic and educational use. Selling, reselling or offering this software as a paid service is not permitted without written consent from Pranav Suryawanshi ([pranavsuryawanshi955@gmail.com](mailto:pranavsuryawanshi955@gmail.com)). See [LICENSE](LICENSE).

## Contents
1. [Why BloomCraft](#why-bloomcraft)
2. [Who it is for](#who-it-is-for)
3. [What it does](#what-it-does)
4. [How it works](#how-it-works)
5. [Bloom's levels used](#blooms-levels-used)
6. [Setup](#setup)
7. [In-app user guide](#in-app-user-guide)
8. [Session and progress behaviour](#session-and-progress-behaviour)
9. [Security and privacy](#security-and-privacy)
10. [Troubleshooting](#troubleshooting)

---

## Why BloomCraft

Setting a good question paper is slow and hard to get right. Faculty usually face these problems:

- **Time:** reading the syllabus, writing fresh questions every semester, and formatting the paper in the college style takes hours.
- **Uneven difficulty:** papers often lean on simple recall (remember / define) and rarely test applying, analysing or designing, so they do not match the intended learning outcomes.
- **Accreditation evidence:** NBA, NAAC and AICTE outcome-based education (OBE) expect each question mapped to a **Course Outcome (CO)** and a **Bloom's level**. Doing this mapping by hand in spreadsheets is tedious and error-prone.
- **Unit coverage:** it is easy to over-weight some units and miss others.
- **Marking consistency:** evaluators need a step-wise scheme, which is usually written separately and late.
- **Formatting:** every college has its own header, logo, numbering and instruction style that must be reproduced exactly.

BloomCraft solves these by generating the paper **from your own syllabus**, planning the cognitive mix **before** writing questions, tagging every question with its Bloom level and CO, checking the result against your targets, and exporting in **your college's format**.

---

## Who it is for

BloomCraft is built **for teachers (faculty) only**. It helps a subject teacher create a question paper quickly from their own syllabus, without writing and formatting it by hand.

A teacher can use it for:

- Unit tests, in-semester, mid-semester and end-semester papers (built-in presets for these are included).
- Papers in their own college's format, by uploading an old paper or building a custom template.
- Papers where every question already carries its Bloom's level and Course Outcome (CO), with an analytics report and marking scheme.

Each teacher signs in to a private account with their own paper history, templates and question sets. A guest option is available to try the system (one paper per device).

---

## What it does

- **Reads your syllabus** from a PDF, TXT or MD file, or from text you paste, and splits it into units, topics and Course Outcomes.
- **Uses ready or custom templates:** built-in college and exam presets (RCPIT, SVKM DJSCE, in-semester, unit test, semester end and more), **or** upload an old paper to copy its format, **or** build your own template manually.
- **Plans a blueprint:** total marks, duration, sections, per-question marks, internal choices (OR), unit-wise marks weightage and a Bloom's target mix (L1 to L6).
- **Generates the paper** with AI (free-tier providers with automatic failover), or from your own uploaded question set / question bank, or a hybrid of both.
- **Lets you edit everything** in the Paper Studio: change a question, regenerate one or all, add technical diagrams, and customise layout.
- **Validates and reports:** cognitive depth index, target vs actual Bloom's mix with deviation, CO attainment and a step-wise evaluation rubric.
- **Exports** to Word (.doc), print / Save as PDF, or JSON, and **archives** every paper in your private Past Papers history.
- **Guides new users** with an in-app step-by-step guide.

---

## How it works

```
 Syllabus (file or pasted text)
        |
        v
 1. INGEST      Parse into units, topics, COs; you review and correct
        |
        v
 2. BLUEPRINT   Template (preset / uploaded college paper / custom)
                + marks, sections, OR choices, unit weightage
                + Bloom's target mix (L1 to L6, totals 100%)
        |
        v
 3. GENERATE    Questions are written for each slot to match the unit,
                Bloom's level, CO and marks (AI, your question bank, or hybrid)
        |
        v
 4. STUDIO      Review, edit, regenerate, add diagrams, adjust layout
        |
        v
 5. ANALYTICS   Target vs actual Bloom's, CO attainment, evaluation rubric
        |
        v
 6. EXPORT      Word / PDF (print) / JSON  +  saved to Past Papers
```

**Under the hood**

- **Frontend:** a single-page web app (HTML, CSS and vanilla JavaScript) with four stages: Syllabus, Blueprint, Studio and Analytics.
- **Backend:** a Flask (Python) REST API that parses syllabi, builds blueprints, calibrates Bloom's distribution, generates questions and figures, and creates the Word export.
- **AI providers:** Groq, OpenRouter, Cerebras and Mistral free tiers. If one is busy or fails, the next configured provider is used automatically. At least one API key is required.
- **Database:** PostgreSQL stores faculty accounts, sessions, generated papers, question sets and custom templates.
- **Diagrams:** technical figures (circuits, networks, architecture and similar) are produced as SVG.

---

## Bloom's levels used

| Level | Tier | Typical verbs | What it tests |
| :---: | :--- | :--- | :--- |
| **L1** | Remember | Define, List, State, Identify | Recall of facts and definitions |
| **L2** | Understand | Explain, Describe, Summarize | Comprehension of concepts |
| **L3** | Apply | Calculate, Solve, Implement | Using techniques on concrete problems |
| **L4** | Analyze | Compare, Differentiate, Deconstruct | Breaking down systems and relationships |
| **L5** | Evaluate | Assess, Justify, Validate | Judging and trade-off analysis |
| **L6** | Create | Design, Formulate, Construct | Producing new designs and solutions |

Presets for the target mix: **Balanced Academic**, **Analytical Focus**, **Foundational** and **Advanced Synthesis**, or set your own with sliders.

---

## Setup

### 1. Requirements
- Python **3.9+**
- A **PostgreSQL** database
- At least one free LLM API key (Groq, OpenRouter, Cerebras or Mistral)

### 2. Install
```bash
git clone https://github.com/PranavSuryawanshi11/Blooms-Taxonomy.git
cd Blooms-Taxonomy

python -m venv venv
# Windows:      .\venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure
Copy `backend/.env.example` to `backend/.env` and fill it in:

```ini
# At least ONE LLM key is required
GROQ_API_KEY=
OPENROUTER_API_KEY=
CEREBRAS_API_KEY=
MISTRAL_API_KEY=

# PostgreSQL (required)
DATABASE_URL=postgresql://bloom:change-this-password@localhost:5432/bloomcraft

# Optional
# BLOOMCRAFT_LLM_ORDER=mistral,cerebras,groq,openrouter
# PORT=5000
# TRUST_PROXY=1   # when behind nginx / Render / Railway
```

Free key portals: [Groq](https://console.groq.com/keys) (recommended) &bull; [OpenRouter](https://openrouter.ai/keys) &bull; [Cerebras](https://cloud.cerebras.ai) &bull; [Mistral](https://console.mistral.ai)

### 4. Run
```bash
python backend/app.py
```
Open **http://127.0.0.1:5000**.

**Docker alternative** (starts the app and PostgreSQL together):
```bash
POSTGRES_PASSWORD=choose-a-strong-one docker compose up -d
```

---

## In-app guide (pop-ups on the exact control)

There is no long manual. Small pop-ups **point at the exact control they explain** (a highlighted box with an arrow), so a teacher is told what to do at the place where they do it. Each stage has a short tour that starts the first time the stage is opened. Use **Next / Back**, **Skip** or the close button, and the **Guide** button in the top bar to replay the current stage's tour at any time.

| Stage | Where the pop-ups appear |
| :--- | :--- |
| **Stage 1: Syllabus** | **Upload box** (PDF/TXT/MD) &rarr; **sample syllabus chips** &rarr; each course field one by one: **Course Code**, **Department / Faculty**, **Course Title**, **Academic Year**, **Year / Semester** &rarr; **paste box** (for short or scanned files: copy the text, start each unit with `UNIT 1: Title`) &rarr; **Parse & Ingest Curriculum Structure** button. After parsing, more pop-ups appear at the **unit / topic / CO counts**, the **Modules** and **Extracted Document** views, and the **continue to Stage 2** button. |
| **Stage 2: Template & blueprint** | **Template list** &rarr; **Add Your College Template** (upload an old paper) &rarr; **Custom Template** (build manually) &rarr; marks / duration / title &rarr; question-set upload and source &rarr; unit weightage &rarr; **Auto-Balance** and Bloom's sliders (100%) &rarr; sections and marks &rarr; **Generate Examination Paper**. When the college-template window opens, pop-ups appear at its **upload box**, the **Build the template manually** button, and **Save & Use Template**. |
| **Stage 3: Paper Studio** | Question **regenerate / edit** icons &rarr; paper **validation checklist** &rarr; **Customize Layout** &rarr; **Regenerate All** &rarr; **Word** export &rarr; **Print / Save PDF**. |
| **Stage 4: Analytics** | Cognitive depth index &rarr; target vs actual Bloom's mix (deviation) &rarr; CO coverage &rarr; scheme of evaluation. |

Each tour opens automatically only once per browser.

---

## Session and progress behaviour

- **Moving between stages or refreshing the page:** your work resumes exactly where you left off: the stage you were on, the syllabus, course details, blueprint, Bloom's distribution and the generated paper are all restored.
- **Closing the browser (or the tab):** the session ends. You must **sign in again**, and the workspace starts clean. Papers you generated stay in your **Past Papers** archive and can be reopened after signing in.
- **Signing out** clears the saved workspace for that browser session.
- Progress is kept per signed-in user for the current browser session only, so one faculty member never sees another's in-progress work.

> Export (Word / JSON) anything you need before closing the browser.

---

## Security and privacy

- Each faculty member has a **private, isolated** archive of papers, question sets and templates.
- Passwords are stored as salted hashes; the recovery code (shown once) is the only way to reset a forgotten password.
- API keys belong only in `backend/.env`, which is excluded from version control. Never commit it.
- Guest use is limited to one paper per device.

---

## Troubleshooting

| Problem | Fix |
| :--- | :--- |
| `DATABASE_URL is not set` | Add `DATABASE_URL` to `backend/.env` |
| Paper generation fails | Check that at least one LLM key is set and valid; try again if the service is busy |
| Syllabus upload finds few or no units | Paste the text manually and add `UNIT 1: ...` headings (guide step 1b) |
| Marks warning in the Studio | Section marks do not equal the total; fix marks in Stage 2 or on the questions |
| A stage guide does not appear again | It opens automatically once per stage per browser; click the **Guide** button to replay it |
| Asked to sign in after closing the browser | Expected: sessions end when the browser closes |
