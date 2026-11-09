/**
 * BloomCraft AI - Work Session Persistence
 * Keeps the faculty member's progress (stage, syllabus, blueprint, generated paper, form fields)
 * in sessionStorage so a refresh or a tab switch resumes exactly where they left off.
 * sessionStorage is wiped when the browser/tab is closed, so a closed browser means a fresh
 * sign-in and a clean workspace (past papers stay in the server-side archive).
 */
window.SessionModule = {
  KEY: "bloom_work_state_v1",
  STATE_KEYS: [
    "currentTab", "currentSyllabus", "extractedSyllabusText", "currentBlueprintConfig",
    "customLayout", "currentDistribution", "currentPaper", "numberingStyle", "numberingFormat",
    "uploadedSet", "useUploadedSet", "unitPlan", "unitPlanAuto", "academicYear", "diagramMode"
  ],
  FIELD_IDS: [
    "course-code", "course-dept", "course-name", "academic-year", "year-semester",
    "syllabus-text-input", "select-exam-template", "blueprint-total-marks", "blueprint-duration",
    "blueprint-exam-title", "select-numbering-style", "select-generation-source"
  ],
  _ready: false,
  _timer: null,
  _last: "",

  userKey() {
    const u = (window.AuthModule && window.AuthModule.currentUser) || window.AppState.currentUser;
    return u ? String(u.user_id || u.username || "") : "";
  },

  init() {
    const schedule = () => this.scheduleSave();
    ["input", "change", "click"].forEach(ev => document.addEventListener(ev, schedule, true));
    window.addEventListener("pagehide", () => this.save());
    document.addEventListener("visibilitychange", () => { if (document.hidden) this.save(); });
    setInterval(() => this.save(), 5000);
  },

  scheduleSave() {
    if (!this._ready) return;
    clearTimeout(this._timer);
    this._timer = setTimeout(() => this.save(), 400);
  },

  snapshot() {
    const st = window.AppState, snap = { uid: this.userKey(), state: {}, fields: {} };
    this.STATE_KEYS.forEach(k => { if (st[k] !== undefined) snap.state[k] = st[k]; });
    this.FIELD_IDS.forEach(id => {
      const el = document.getElementById(id);
      if (el) snap.fields[id] = el.value;
    });
    const unitEn = document.getElementById("unit-plan-enable");
    if (unitEn) snap.fields["unit-plan-enable"] = unitEn.checked ? "1" : "0";
    return snap;
  },

  save() {
    if (!this._ready || !this.userKey()) return;
    const snap = this.snapshot();
    let json = JSON.stringify(snap);
    if (json === this._last) return;
    try {
      sessionStorage.setItem(this.KEY, json);
      this._last = json;
    } catch (e) {
      // Quota exceeded (very large paper with many diagrams): drop the bulkiest piece and retry
      try {
        delete snap.state.extractedSyllabusText;
        sessionStorage.setItem(this.KEY, JSON.stringify(snap));
      } catch (e2) { console.warn("Could not persist work session:", e2); }
    }
  },

  clear() {
    this._ready = false;
    this._last = "";
    try { sessionStorage.removeItem(this.KEY); } catch (e) {}
  },

  // Called once the app, presets and templates are loaded. Returns true if work was restored.
  restore() {
    let restored = false;
    try {
      const raw = sessionStorage.getItem(this.KEY);
      const uid = this.userKey();
      if (raw && uid) {
        const snap = JSON.parse(raw);
        if (snap && snap.uid === uid) { this._apply(snap); restored = true; }
        else sessionStorage.removeItem(this.KEY);
      }
    } catch (e) {
      console.warn("Work session restore failed:", e);
      try { sessionStorage.removeItem(this.KEY); } catch (_) {}
    }
    this._ready = !!this.userKey();
    return restored;
  },

  // Enable saving after a fresh sign-in (no restore needed, the workspace is new)
  start() { this._ready = !!this.userKey(); },

  _apply(snap) {
    const st = window.AppState;
    Object.keys(snap.state || {}).forEach(k => { st[k] = snap.state[k]; });

    Object.keys(snap.fields || {}).forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      if (id === "unit-plan-enable") { el.checked = snap.fields[id] === "1"; return; }
      if (el.tagName === "SELECT") {
        if (Array.from(el.options).some(o => o.value === snap.fields[id])) el.value = snap.fields[id];
      } else el.value = snap.fields[id];
    });
    if (window.syncAcademicYear) window.syncAcademicYear();

    if (st.currentSyllabus) {
      const S = window.SyllabusModule;
      if (S) {
        S.renderParsedSyllabus(st.currentSyllabus);
        S.renderExtractedDocument(st.extractedSyllabusText || st.currentSyllabus.extracted_text || "");
        document.querySelectorAll("#sample-chips-container .chip").forEach(c => {
          c.classList.toggle("active", st.currentSyllabus.code && c.textContent.includes(st.currentSyllabus.code));
        });
      }
    }

    const B = window.BlueprintModule;
    if (B) {
      B.renderSliders();
      B.refresh();
    }
    if (window.UploadModule && window.UploadModule.renderResult && st.uploadedSet) window.UploadModule.renderResult();
    if (window.TemplateImport && window.TemplateImport.updateDeleteButton) window.TemplateImport.updateDeleteButton();

    if (st.currentPaper && window.GeneratorModule) {
      window.applyLayoutToExamSheet();
      window.GeneratorModule.renderPaper(st.currentPaper);
    }

    let tab = st.currentTab || "syllabus";
    if ((tab === "studio" || tab === "analytics") && !st.currentPaper) tab = "blueprint";
    if (tab === "blueprint" && !st.currentSyllabus) tab = "syllabus";
    window.switchTab(tab);
    window.scrollTo({ top: 0, behavior: "instant" });
    if (window.showToast) window.showToast("Welcome back - your work in this session has been restored.", "success");
  }
};
window.SessionModule.init();
