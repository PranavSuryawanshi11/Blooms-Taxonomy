/**
 * BloomCraft AI - In-context Guide
 * Small pop-ups that point at the exact control they explain (the upload box, the Parse button,
 * the template list...). Each stage has a short tour that starts the first time the teacher reaches
 * that stage; a few extra pop-ups appear when a step becomes available (e.g. after parsing, or when
 * the college-template window opens). The "Guide" button in the top bar replays the current stage.
 */
window.StageGuide = {
  SEEN_KEY: "bloom_stage_guide_seen_v2",
  pop: null, ring: null, key: null, steps: [], idx: 0, target: null, raf: 0,

  /* ---------- Content ---------- */
  tours: {
    syllabus: [
      { sel: "#syllabus-dropzone", title: "Step 1: Upload your syllabus file",
        text: "Click here or drag and drop your syllabus <b>PDF, TXT or MD</b> file. It is read automatically and split into units, topics and Course Outcomes, shown on the right. If the file is too short or cannot be read (for example a scanned PDF), use the paste box further down instead." },
      { sel: "#sample-chips-container", title: "Or try a sample syllabus",
        text: "No syllabus handy? Click one of these ready-made engineering syllabi to see how the system works." },
      { sel: "#course-code", up: ".form-group", title: "Step 2: Course Code (subject code)",
        text: "Type the subject code of your course, for example <code>CS501</code>. It is printed on the question paper header." },
      { sel: "#course-dept", up: ".form-group", title: "Department / Faculty",
        text: "Type your department or faculty, for example <code>Computer Science &amp; Engineering</code>." },
      { sel: "#course-name", up: ".form-group", title: "Course Title (subject name)",
        text: "Type the full subject name, for example <code>Database Management Systems</code>. Questions and the paper header use this name." },
      { sel: "#academic-year", up: ".form-group", title: "Academic Year (A.Y.)",
        text: "Type the academic year, for example <code>2026-2027</code>. It is printed on the paper, print view and Word export." },
      { sel: "#year-semester", up: ".form-group", title: "Year / Semester",
        text: "Type the class and semester, for example <code>Year: III / Semester V</code>. Leave it empty to keep the template's own wording." },
      { sel: "#syllabus-text-input", title: "Step 3: Paste the syllabus text",
        text: "File too short or not extracting? <b>Copy the syllabus text</b> from your PDF or Word file and <b>paste it here</b>. Start each unit on its own line, like <code>UNIT 1: ER Model and Relational Schemas</code>, followed by its topics." },
      { sel: "#btn-parse-text", title: "Step 4: Parse &amp; Ingest Curriculum Structure",
        text: "After pasting the text and filling the course details above, click this button. BloomCraft reads your text and builds the units, topics and Course Outcomes for the next stage." }
    ],
    blueprint: [
      { sel: "#select-exam-template", title: "1. Choose an exam template",
        text: "Pick a ready template. It sets the paper header, total marks, duration and sections automatically." },
      { sel: "#btn-add-college-template", title: "Need a different template? (option A)",
        text: "Click here and <b>upload your college's old question paper</b> (PDF, Word or photo). BloomCraft copies its header, logo, numbering and sections." },
      { sel: "#btn-create-custom-template", title: "Or build your own (option B)",
        text: "Click here to <b>create a template manually</b>: college details, style, sections and marks per question." },
      { sel: "#blueprint-total-marks", title: "2. Marks, duration and title",
        text: "Adjust <b>Total Marks</b>, <b>Duration</b> and <b>Exam Title</b> if your exam differs from the template. Question numbering style is just below." },
      { sel: "#qset-upload-card", title: "3. Use your own questions (optional)",
        text: "Upload your own question paper or bank here (PDF, DOCX, TXT, MD, CSV, JSON) and the paper is built from your questions." },
      { sel: "#select-generation-source", title: "Question source",
        text: "Choose where questions come from: the built-in engine, your question sets, or Hybrid. <b>Manage Question Sets</b> lets you add your own questions." },
      { sel: "#unit-planner-card", title: "4. Unit-wise marks",
        text: "Decide how many marks each unit carries. <b>Distribute evenly</b> is a quick start." },
      { sel: "#btn-auto-balance", title: "5. Bloom's level mix",
        text: "The Bloom's levels (L1 to L6) must total <b>100%</b>. Click <b>Auto-Balance</b> to fix the total automatically." },
      { sel: "#bloom-sliders-container", title: "Set the cognitive mix",
        text: "Pick a preset or drag the sliders to choose how much of the paper tests remembering, applying, analysing, designing and so on." },
      { sel: "#blueprint-sections-container", place: "left", title: "6. Sections and marks",
        text: "Edit the marks of each question here, tick <b>Add OR</b> for choices, and use <b>Add Section</b> if needed. The section total should equal the Total Marks." },
      { sel: "#btn-generate-paper", title: "7. Generate the paper",
        text: "All set? Click <b>Generate Examination Paper</b> and wait while the paper is written. You will land in Stage 3." }
    ],
    studio: [
      { sel: "#exam-sheet-container .question-item .btn-icon", title: "Edit each question",
        text: "These icons are on every question: <b>regenerate</b> it with a new one, or <b>edit</b> its wording, marks, Bloom level, CO and diagram." },
      { sel: "#exam-sheet-container", title: "Check your paper",
        text: "Before exporting, check:<ul class=\"sg-check\"><li>Header details are correct</li><li>Marks add up to the total (no marks warning)</li><li>Every unit and CO is covered</li><li>No repeated or vague questions</li><li>OR choices have equal marks; figures are correct</li></ul>" },
      { sel: "#btn-open-layout-customizer", title: "Customise the layout",
        text: "Change the college name, exam title, fonts, columns and which tags are shown on the paper." },
      { sel: "#btn-regenerate-all", title: "Not happy with the paper?",
        text: "<b>Regenerate All</b> writes the whole paper again from the same blueprint." },
      { sel: "#btn-export-word", title: "Export",
        text: "Download the paper as <b>Word</b>. <b>Export JSON</b> saves the raw data. Every paper is also saved in <b>Past Papers</b>." },
      { sel: "#btn-print-paper", title: "Print or save as PDF",
        text: "Opens the print window. Choose <i>Save as PDF</i> in it to get a PDF." }
    ],
    analytics: [
      { sel: "#analytics-empty-state", title: "Generate a paper first",
        text: "The report appears here once a paper has been generated in Stage 2 and 3." },
      { sel: "#metric-cog-index", up: ".metric-card", title: "Cognitive Depth Index",
        text: "A score out of 6 showing how demanding the paper is, with total marks and question count." },
      { sel: "#analytics-table-body", up: ".glass-panel", title: "Target vs Actual Bloom's mix",
        text: "Compare the Bloom's levels you planned with what the paper has. A large <b>deviation</b> means you should edit or regenerate questions in Stage 3." },
      { sel: "#analytics-co-breakdown-container", title: "Course Outcome coverage",
        text: "See how many marks and which questions cover each CO. A CO with no questions needs attention." },
      { sel: "#rubrics-container", title: "Scheme of Evaluation",
        text: "A step-wise marking rubric for every question, ready for evaluators." }
    ]
  },

  // Extra pop-ups that appear when a control becomes available
  nudges: [
    { key: "parsed", watch: "#btn-proceed-blueprint", steps: [
      { sel: "#stat-total-units", up: ".metric-card", title: "Syllabus read successfully",
        text: "These cards show how many <b>units</b>, <b>key topics</b> and <b>Course Outcomes</b> were found. Compare them with your syllabus." },
      { sel: "#btn-view-modules", title: "Modules view",
        text: "Each unit is listed below with its topics. Make sure no unit is missing or merged with another." },
      { sel: "#btn-view-extracted-doc", title: "Extracted Document view",
        text: "Click here to read the full text that was found. If something is wrong, fix the text, paste it in the paste box and click <b>Parse &amp; Ingest</b> again." },
      { sel: "#btn-proceed-blueprint", title: "Looks right? Continue",
        text: "Click here to go to Stage 2 and set up the template and marking scheme." }
    ]},
    { key: "tpl-upload", watch: "#tpl-dropzone", steps: [
      { sel: "#tpl-dropzone", title: "Upload your old question paper",
        text: "Click here or drop your college's old paper (<b>PDF, Word or a clear photo</b>, up to 8 MB). The header, logo, numbering and sections are copied for you." },
      { sel: "#btn-tpl-manual", title: "No old paper?",
        text: "Click here to <b>build the template manually</b> instead." }
    ]},
    { key: "tpl-save", watch: "#btn-tpl-save", steps: [
      { sel: "#btn-tpl-save", title: "Review, then save",
        text: "Check the preview and correct any detail (college name, exam title, style, sections and marks; use <b>Build structure</b> for sections). Then click <b>Save &amp; Use Template</b>." }
    ]}
  ],

  /* ---------- State ---------- */
  seen() { try { return JSON.parse(localStorage.getItem(this.SEEN_KEY) || "{}"); } catch (e) { return {}; } },
  markSeen(k) { try { const s = this.seen(); s[k] = 1; localStorage.setItem(this.SEEN_KEY, JSON.stringify(s)); } catch (e) {} },
  loggedIn() { return !!(window.AuthModule && window.AuthModule.currentUser); },

  resolve(step) {
    let el = document.querySelector(step.sel);
    if (el && step.up) el = el.closest(step.up) || el;
    return (el && el.getClientRects().length) ? el : null;
  },

  /* ---------- Triggers ---------- */
  // Called by switchTab: end any running tour and start this stage's tour the first time
  onTab(tab) {
    this.end();
    if (!this.loggedIn() || !this.tours[tab] || this.seen()[tab]) return;
    setTimeout(() => {
      if (window.AppState.currentTab === tab && !this.key) this.start(tab, this.tours[tab]);
    }, 350);
  },

  init() {
    const btn = document.getElementById("btn-open-guide");
    if (btn) btn.addEventListener("click", () => {
      if (this.key) { this.end(); return; }
      const tab = window.AppState.currentTab;
      if (this.tours[tab]) this.start(tab, this.tours[tab]);
    });
    // Watch for controls becoming available (after parsing, when the template window opens...)
    setInterval(() => {
      if (this.key || !this.loggedIn()) return;
      const seen = this.seen();
      for (const n of this.nudges) {
        if (seen[n.key]) continue;
        const w = document.querySelector(n.watch);
        if (w && w.getClientRects().length) { this.start(n.key, n.steps); break; }
      }
    }, 600);
    document.addEventListener("keydown", e => { if (e.key === "Escape" && this.key) this.end(); });
    window.addEventListener("scroll", () => this.schedule(), { passive: true, capture: true });
    window.addEventListener("resize", () => this.schedule());
  },

  /* ---------- Tour engine ---------- */
  start(key, steps) {
    this.markSeen(key);
    this.key = key;
    this.steps = steps;
    this.idx = -1;
    if (!this.pop) this.build();
    this.go(1);
  },

  end() {
    this.key = null; this.target = null;
    if (this.pop) this.pop.classList.remove("show");
    if (this.ring) this.ring.classList.remove("show");
  },

  // Move to the next/previous step that has a visible target
  go(dir) {
    let i = this.idx + dir;
    while (i >= 0 && i < this.steps.length) {
      const el = this.resolve(this.steps[i]);
      if (el) { this.idx = i; this.target = el; this.render(); return; }
      i += dir;
    }
    if (dir > 0) this.end();
  },

  build() {
    this.ring = document.createElement("div");
    this.ring.className = "sg-ring no-print";
    this.pop = document.createElement("div");
    this.pop.className = "sg-pop no-print";
    this.pop.setAttribute("role", "dialog");
    this.pop.setAttribute("aria-label", "Guide");
    this.pop.innerHTML = `
      <span class="sg-arrow"></span>
      <div class="sg-head"><strong class="sg-title"></strong><button type="button" class="sg-x" aria-label="Close guide">&times;</button></div>
      <div class="sg-body"></div>
      <div class="sg-foot">
        <span class="sg-count"></span>
        <span class="sg-btns">
          <button type="button" class="guide-link sg-skip">Skip</button>
          <button type="button" class="btn btn-secondary btn-sm sg-prev">Back</button>
          <button type="button" class="btn btn-primary btn-sm sg-next">Next</button>
        </span>
      </div>`;
    document.body.appendChild(this.ring);
    document.body.appendChild(this.pop);
    const q = s => this.pop.querySelector(s);
    q(".sg-x").addEventListener("click", () => this.end());
    q(".sg-skip").addEventListener("click", () => this.end());
    q(".sg-prev").addEventListener("click", () => this.go(-1));
    q(".sg-next").addEventListener("click", () => {
      if (this.idx >= this.steps.length - 1) this.end(); else this.go(1);
    });
  },

  render() {
    const s = this.steps[this.idx], q = x => this.pop.querySelector(x);
    q(".sg-title").innerHTML = s.title;
    q(".sg-body").innerHTML = s.text;
    q(".sg-count").textContent = `${this.idx + 1} / ${this.steps.length}`;
    const hasPrev = this.steps.slice(0, this.idx).some(x => this.resolve(x));
    const hasNext = this.steps.slice(this.idx + 1).some(x => this.resolve(x));
    q(".sg-prev").style.visibility = hasPrev ? "visible" : "hidden";
    q(".sg-next").textContent = hasNext ? "Next" : "Got it";
    q(".sg-skip").style.visibility = hasNext ? "visible" : "hidden";

    // Bring the control into view, clear of the sticky top bar
    const nav = document.querySelector(".navbar");
    const navB = nav ? nav.getBoundingClientRect().bottom : 0;
    const el = this.target, r = el.getBoundingClientRect();
    const tall = r.height > window.innerHeight * 0.6;
    el.style.scrollMarginTop = (navB + 16) + "px";
    el.style.scrollMarginBottom = "16px";
    try { el.scrollIntoView({ behavior: "smooth", block: tall ? "start" : "center" }); } catch (e) { el.scrollIntoView(); }

    this.pop.classList.add("show");
    this.ring.classList.add("show");
    this.place();
    // keep following while the smooth scroll settles
    const t0 = performance.now();
    const loop = () => { this.place(); if (this.key && performance.now() - t0 < 700) requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  },

  schedule() {
    if (!this.key || this.raf) return;
    this.raf = requestAnimationFrame(() => { this.raf = 0; this.place(); });
  },

  // Position the highlight ring and the pop-up next to the target
  place() {
    if (!this.key || !this.target || !this.target.isConnected) return;
    const el = this.target, r = el.getBoundingClientRect();
    const vw = window.innerWidth, vh = window.innerHeight, gap = 14, m = 8;
    const nav = document.querySelector(".navbar");
    const top0 = Math.max(nav ? nav.getBoundingClientRect().bottom : 0, 0) + m;

    // Highlight ring (clipped to the visible part of the page)
    const rt = Math.max(r.top, 0), rb = Math.min(r.bottom, vh);
    const ring = this.ring.style;
    ring.top = (r.top - 4) + "px"; ring.left = (r.left - 4) + "px";
    ring.width = (r.width + 8) + "px"; ring.height = (r.height + 8) + "px";

    const pop = this.pop, ps = pop.style;
    const pw = Math.min(340, vw - 2 * m);
    ps.width = pw + "px";
    const ph = pop.offsetHeight;
    const vis = { top: Math.max(r.top, top0), bottom: Math.min(r.bottom, vh - m) };
    const tall = (vis.bottom - vis.top) > vh * 0.55 || rb - rt <= 0;
    const cx = r.left + r.width / 2, cy = (vis.top + vis.bottom) / 2;
    const clampX = x => Math.max(m, Math.min(vw - pw - m, x));
    const clampY = y => Math.max(top0, Math.min(vh - ph - m, y));
    const pref = this.steps[this.idx].place;
    const spots = {
      bottom: () => ({ ok: r.bottom + gap + ph <= vh - m, x: clampX(cx - pw / 2), y: r.bottom + gap }),
      top:    () => ({ ok: r.top - gap - ph >= top0, x: clampX(cx - pw / 2), y: r.top - gap - ph }),
      right:  () => ({ ok: r.right + gap + pw <= vw - m, x: r.right + gap, y: clampY(cy - ph / 2) }),
      left:   () => ({ ok: r.left - gap - pw >= m, x: r.left - gap - pw, y: clampY(cy - ph / 2) })
    };
    let side = null, pos = null;
    if (!tall) {
      const order = [pref, "bottom", "top", "right", "left"].filter(Boolean);
      for (const s of order) { const p = spots[s](); if (p.ok) { side = s; pos = p; break; } }
    }
    if (!pos) {
      // Large or cramped target: float the pop-up inside the visible part of it
      side = null;
      pos = { x: clampX(Math.max(r.left, m) + 16), y: clampY(vis.top + 16) };
    }
    ps.left = pos.x + "px"; ps.top = pos.y + "px";

    const arrow = pop.querySelector(".sg-arrow");
    pop.dataset.side = side || "none";
    if (side === "bottom" || side === "top") arrow.style.left = Math.max(16, Math.min(pw - 16, cx - pos.x)) + "px", arrow.style.top = "";
    else if (side === "right" || side === "left") arrow.style.top = Math.max(16, Math.min(ph - 16, cy - pos.y)) + "px", arrow.style.left = "";
  }
};
document.addEventListener("DOMContentLoaded", () => window.StageGuide.init());
