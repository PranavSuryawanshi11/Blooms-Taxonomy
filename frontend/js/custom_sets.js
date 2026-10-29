/**
 * BloomCraft AI - Custom Question Sets & Question Bank Manager
 * Manages user-provided question sets (e.g. Set 1, Set 2, Set 3, Set 4 with 4+ questions each)
 * Supports sampling from question sets to generate exam papers matching any selected marks, duration, and templates.
 * Zero emojis - 100% clean SVG icons.
 */

window.QuestionSetsModule = {
  activeSetId: "set_1",

  async init() {
    this.bindEvents();
    await this.loadQuestionSets();
  },

  bindEvents() {
    // Open Question Sets Modal
    const openBtn = document.getElementById("btn-open-question-sets");
    if (openBtn) {
      openBtn.addEventListener("click", () => this.openModal());
    }

    const openFromNav = document.getElementById("btn-nav-question-sets");
    if (openFromNav) {
      openFromNav.addEventListener("click", () => this.openModal());
    }

    // Add New Set Button
    const addSetBtn = document.getElementById("btn-add-new-set");
    if (addSetBtn) {
      addSetBtn.addEventListener("click", () => this.addNewSet());
    }

    // Add Question to Active Set Button
    const addQBtn = document.getElementById("btn-add-question-to-set");
    if (addQBtn) {
      addQBtn.addEventListener("click", () => this.addQuestionToActiveSet());
    }

    // Preload College Starter Sets
    const preloadBtn = document.getElementById("btn-preload-college-sets");
    if (preloadBtn) {
      preloadBtn.addEventListener("click", () => this.preloadStarterSets());
    }

    // Save Sets Button
    const saveBtn = document.getElementById("btn-save-question-sets");
    if (saveBtn) {
      saveBtn.addEventListener("click", () => this.saveQuestionSetsToServer());
    }

    // Source Mode Selector
    const sourceSelect = document.getElementById("select-generation-source");
    if (sourceSelect) {
      sourceSelect.addEventListener("change", (e) => {
        window.AppState.generationSource = e.target.value;
        const note = document.getElementById("generation-source-note");
        if (note) {
          if (e.target.value === "user_sets") {
            const count = (window.AppState.userQuestionSets || []).reduce((acc, s) => acc + (s.questions || []).length, 0);
            note.innerText = `Active: Generating directly from ${window.AppState.userQuestionSets.length} custom sets (${count} total questions in bank).`;
            note.style.color = "var(--accent-emerald)";
          } else if (e.target.value === "hybrid") {
            note.innerText = "Active: Blended mode (samples custom sets first, fills unmet quotas via AICTE engine).";
            note.style.color = "var(--accent-amber)";
          } else {
            note.innerText = "Active: Standard AICTE Examination Reform Policy algorithmic & cognitive engine.";
            note.style.color = "var(--text-secondary)";
          }
        }
      });
    }
  },

  async loadQuestionSets() {
    try {
      const headers = {};
      if (window.AuthModule && window.AuthModule.authToken) {
        headers["Authorization"] = `Bearer ${window.AuthModule.authToken}`;
      }
      const res = await fetch(`${API_BASE}/api/question-sets`, { headers });
      const data = await res.json();
      if (data.success && Array.isArray(data.sets)) {
        window.AppState.userQuestionSets = data.sets;
        if (data.sets.length > 0) {
          this.activeSetId = data.sets[0].set_id;
        }
        this.renderSetsTabs();
        this.renderActiveSetQuestions();
        this.updateBankSummaryBadge();
      }
    } catch (err) {
      console.warn("Could not load question sets:", err);
    }
  },

  async saveQuestionSetsToServer() {
    try {
      const headers = { "Content-Type": "application/json" };
      if (window.AuthModule && window.AuthModule.authToken) {
        headers["Authorization"] = `Bearer ${window.AuthModule.authToken}`;
      }
      const res = await fetch(`${API_BASE}/api/question-sets`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          sets: window.AppState.userQuestionSets
        })
      });
      const data = await res.json();
      if (data.success) {
        showToast("Custom Question Sets saved and synced with server.", "success");
        this.updateBankSummaryBadge();
      } else {
        showToast(data.error || "Failed to save question sets.", "error");
      }
    } catch (err) {
      console.error(err);
      showToast("Network error saving question sets.", "error");
    }
  },

  openModal() {
    const modal = document.getElementById("modal-question-sets");
    if (modal) {
      this.renderSetsTabs();
      this.renderActiveSetQuestions();
      modal.classList.add("active");
    }
  },

  renderSetsTabs() {
    const container = document.getElementById("sets-tab-bar");
    if (!container) return;

    container.innerHTML = "";
    const sets = window.AppState.userQuestionSets || [];

    sets.forEach((s) => {
      const btn = document.createElement("button");
      btn.className = `btn btn-sm ${s.set_id === this.activeSetId ? "btn-primary" : "btn-secondary"}`;
      btn.style.marginRight = "6px";
      btn.style.marginBottom = "6px";
      btn.innerHTML = `<span>${s.set_name}</span> <span class="badge" style="background:rgba(255,255,255,0.2); margin-left:4px;">${(s.questions || []).length}</span>`;
      btn.addEventListener("click", () => {
        this.activeSetId = s.set_id;
        this.renderSetsTabs();
        this.renderActiveSetQuestions();
      });
      container.appendChild(btn);
    });
  },

  renderActiveSetQuestions() {
    const container = document.getElementById("active-set-questions-target");
    const titleEl = document.getElementById("active-set-title");
    if (!container) return;

    const sets = window.AppState.userQuestionSets || [];
    const activeSet = sets.find(s => s.set_id === this.activeSetId);

    if (!activeSet) {
      container.innerHTML = "<p style='color:var(--text-muted); padding:20px; text-align:center;'>No question set selected.</p>";
      return;
    }

    if (titleEl) {
      titleEl.innerText = `${activeSet.set_name} (${(activeSet.questions || []).length} Questions)`;
    }

    container.innerHTML = "";
    const questions = activeSet.questions || [];

    if (questions.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:30px; color:var(--text-muted);">
          <p>This question set is currently empty.</p>
          <p style="font-size:12px;">Add questions below or preload college examination questions.</p>
        </div>
      `;
      return;
    }

    questions.forEach((q, qIdx) => {
      const card = document.createElement("div");
      card.className = "question-item";
      card.style.marginBottom = "10px";
      card.style.background = "rgba(255, 255, 255, 0.03)";
      card.style.border = "1px solid var(--border-subtle)";
      card.style.borderRadius = "var(--radius-sm)";
      card.style.padding = "10px 14px";

      const bloomLvl = q.bloom_level || "L2";
      const bloomClass = `badge-${bloomLvl.toLowerCase()}`;

      card.innerHTML = `
        <div class="question-main" style="flex:1;">
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <span style="font-weight:700; font-size:13px; color:var(--text-primary);">Question ${qIdx + 1}.</span>
            <span class="bloom-badge ${bloomClass}">${bloomLvl}</span>
            <span class="co-badge" style="background:rgba(16,185,129,0.15); color:#34D399; font-weight:700;">${q.co || "CO1"}</span>
            <span class="marks-badge">[${q.marks || 5}M]</span>
            ${q.topic ? `<span style="font-size:11px; color:var(--text-muted); font-style:italic;">${q.topic}</span>` : ""}
          </div>
          <div style="font-size:13px; color:var(--text-secondary); line-height:1.4;">${q.question_text}</div>
        </div>
        <div style="display:flex; align-items:center; gap:6px;">
          <button class="btn-icon btn-sm" title="Delete question from set" onclick="window.QuestionSetsModule.deleteQuestion(${qIdx})">
            <svg class="icon-svg icon-xs" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
        </div>
      `;
      container.appendChild(card);
    });
  },

  addNewSet() {
    const sets = window.AppState.userQuestionSets || [];
    const newIdx = sets.length + 1;
    const newSetId = `set_${Date.now()}`;
    const newSetName = `Set ${newIdx} - Custom Examination Pool`;

    sets.push({
      set_id: newSetId,
      set_name: newSetName,
      questions: []
    });

    this.activeSetId = newSetId;
    this.renderSetsTabs();
    this.renderActiveSetQuestions();
    showToast(`Created ${newSetName}.`, "success");
  },

  addQuestionToActiveSet() {
    const textInput = document.getElementById("new-q-text");
    const marksInput = document.getElementById("new-q-marks");
    const bloomInput = document.getElementById("new-q-bloom");
    const coInput = document.getElementById("new-q-co");
    const topicInput = document.getElementById("new-q-topic");

    const text = textInput ? textInput.value.trim() : "";
    if (!text) {
      showToast("Please enter question statement.", "error");
      return;
    }

    const marks = marksInput ? parseInt(marksInput.value) || 5 : 5;
    const bloom = bloomInput ? bloomInput.value : "L3";
    const co = coInput ? coInput.value.trim() || "CO1" : "CO1";
    const topic = topicInput ? topicInput.value.trim() || "Core Subject Principles" : "Core Subject Principles";

    const sets = window.AppState.userQuestionSets || [];
    const activeSet = sets.find(s => s.set_id === this.activeSetId);
    if (!activeSet) return;

    if (!activeSet.questions) activeSet.questions = [];
    activeSet.questions.push({
      question_text: text,
      marks: marks,
      bloom_level: bloom,
      co: co,
      topic: topic
    });

    // Clear input
    if (textInput) textInput.value = "";
    this.renderSetsTabs();
    this.renderActiveSetQuestions();
    this.updateBankSummaryBadge();
    showToast(`Added question to ${activeSet.set_name}.`, "success");
  },

  deleteQuestion(qIdx) {
    const sets = window.AppState.userQuestionSets || [];
    const activeSet = sets.find(s => s.set_id === this.activeSetId);
    if (!activeSet || !activeSet.questions) return;

    activeSet.questions.splice(qIdx, 1);
    this.renderSetsTabs();
    this.renderActiveSetQuestions();
    this.updateBankSummaryBadge();
  },

  async preloadStarterSets() {
    try {
      const res = await fetch(`${API_BASE}/api/question-sets`);
      const data = await res.json();
      if (data.success && data.sets) {
        window.AppState.userQuestionSets = data.sets;
        if (data.sets.length > 0) this.activeSetId = data.sets[0].set_id;
        this.renderSetsTabs();
        this.renderActiveSetQuestions();
        this.updateBankSummaryBadge();
        showToast("Preloaded 4 college examination question sets (16 questions).", "success");
      }
    } catch (err) {
      showToast("Error preloading question sets.", "error");
    }
  },

  updateBankSummaryBadge() {
    const sets = window.AppState.userQuestionSets || [];
    const totalQ = sets.reduce((acc, s) => acc + (s.questions || []).length, 0);
    const badge = document.getElementById("bank-total-badge");
    if (badge) {
      badge.innerText = `${sets.length} Sets (${totalQ} Qs)`;
    }
    const note = document.getElementById("generation-source-note");
    const sourceSelect = document.getElementById("select-generation-source");
    if (note && sourceSelect && sourceSelect.value === "user_sets") {
      note.innerText = `Active: Generating directly from ${sets.length} custom sets (${totalQ} total questions in bank).`;
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  window.QuestionSetsModule.init();
});
