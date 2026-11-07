/**
 * BloomCraft AI - Blueprint Designer & Marking Scheme Controller
 * Handles template presets, marking scheme uploads, manual section adjustments, and Bloom sliders.
 * Zero emojis - 100% professional SVG icons.
 */

window.BlueprintModule = {
  init() {
    this.bindEvents();
    this.renderSliders();
  },

  bindEvents() {
    // Template Selector
    const templateSelect = document.getElementById("select-exam-template");
    if (templateSelect) {
      templateSelect.addEventListener("change", (e) => this.onTemplateSelect(e.target.value));
    }

    // Cognitive Preset Buttons
    document.querySelectorAll("[data-cognitive-preset]").forEach(btn => {
      btn.addEventListener("click", () => {
        const presetKey = btn.getAttribute("data-cognitive-preset");
        this.applyCognitivePreset(presetKey);
      });
    });

    // Auto-Balance Button
    const autoBalanceBtn = document.getElementById("btn-auto-balance");
    if (autoBalanceBtn) {
      autoBalanceBtn.addEventListener("click", () => this.autoBalanceDistribution());
    }

    // Generate Paper Button
    const generateBtn = document.getElementById("btn-generate-paper");
    if (generateBtn) {
      generateBtn.addEventListener("click", () => {
        if (window.GeneratorModule && window.GeneratorModule.generatePaper) {
          window.GeneratorModule.generatePaper();
        }
      });
    }

    // Total Marks input listener
    const totalMarksInput = document.getElementById("blueprint-total-marks");
    if (totalMarksInput) {
      totalMarksInput.addEventListener("input", (e) => {
        window.AppState.currentBlueprintConfig.total_marks = parseInt(e.target.value) || 100;
        this.updateTotalMarksIndicator();
        this.renderUnitPlanner();
      });
    }

    // Duration input listener
    const durationInput = document.getElementById("blueprint-duration");
    if (durationInput) {
      durationInput.addEventListener("input", (e) => {
        window.AppState.currentBlueprintConfig.duration = e.target.value;
      });
    }

    // Exam Title listener
    const examTitleInput = document.getElementById("blueprint-exam-title");
    if (examTitleInput) {
      examTitleInput.addEventListener("input", (e) => {
        window.AppState.currentBlueprintConfig.exam_title = e.target.value;
      });
    }

    // Numbering style (Q1, Q2 ... vs Q.1 (a), (b), (c))
    const numSel = document.getElementById("select-numbering-style");
    if (numSel) {
      numSel.value = window.AppState.numberingStyle || "sequential";
      numSel.addEventListener("change", (e) => {
        window.AppState.numberingStyle = e.target.value;
        this.renderSectionsList();
      });
    }

    // Unit planner controls
    const upEnable = document.getElementById("unit-plan-enable");
    if (upEnable) {
      upEnable.addEventListener("change", () => {
        window.AppState.unitPlan.enabled = upEnable.checked;
        this.renderUnitPlanner();
      });
    }
    const upEven = document.getElementById("btn-unit-plan-even");
    if (upEven) {
      upEven.addEventListener("click", () => {
        window.AppState.unitPlanAuto = true;
        this.renderUnitPlanner(true);
      });
    }
    const upClear = document.getElementById("btn-unit-plan-clear-levels");
    if (upClear) {
      upClear.addEventListener("click", () => {
        (window.AppState.unitPlan.units || []).forEach(u => { u.levels = []; });
        this.renderUnitPlanner();
      });
    }

    // Add Section button
    const addSectionBtn = document.getElementById("btn-add-section");
    if (addSectionBtn) {
      addSectionBtn.addEventListener("click", () => this.addNewSection());
    }

    // Download Marking Scheme Template button
    const downloadTmplBtn = document.getElementById("btn-download-scheme-template");
    if (downloadTmplBtn) {
      downloadTmplBtn.addEventListener("click", () => this.downloadSchemeTemplate());
    }

    // Upload Marking Scheme File
    const schemeFileInput = document.getElementById("marking-scheme-file-input");
    if (schemeFileInput) {
      schemeFileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
          this.uploadMarkingSchemeFile(e.target.files[0]);
        }
      });
    }
  },

  refresh() {
    this.renderSectionsList();
    this.updateTotalMarksIndicator();
    this.updateDistributionVisualizer();
    this.renderUnitPlanner();
    if (window.UploadModule && window.UploadModule.renderResult) window.UploadModule.refreshActiveBadge();
  },

  onTemplateSelect(templateId) {
    const templates = window.AppState.examTemplates;
    if (templates && templates[templateId]) {
      const tmpl = templates[templateId];
      const marksEl = document.getElementById("blueprint-total-marks");
      const durEl = document.getElementById("blueprint-duration");
      const titleEl = document.getElementById("blueprint-exam-title");

      if (marksEl) marksEl.value = tmpl.total_marks;
      if (durEl) durEl.value = tmpl.duration;
      if (titleEl) titleEl.value = tmpl.name;

      window.AppState.currentBlueprintConfig.template_id = templateId;
      window.AppState.currentBlueprintConfig.college_profile = tmpl.college_profile || null;
      window.AppState.currentBlueprintConfig.total_marks = tmpl.total_marks;
      window.AppState.currentBlueprintConfig.duration = tmpl.duration;
      window.AppState.currentBlueprintConfig.exam_title = tmpl.name;
      window.AppState.currentBlueprintConfig.instructions = tmpl.instructions || [];
      window.AppState.currentBlueprintConfig.sections = window.normalizeSections(JSON.parse(JSON.stringify(tmpl.sections)));
      window.AppState.numberingStyle = tmpl.numbering_style || "sequential";
      window.AppState.numberingFormat = tmpl.numbering_format || null;
      if (window.TemplateImport) window.TemplateImport.updateDeleteButton();
      const numSel = document.getElementById("select-numbering-style");
      if (numSel) numSel.value = window.AppState.numberingStyle;
      window.AppState.unitPlanAuto = true;

      // Also sync custom layout defaults
      window.AppState.customLayout.exam_title = tmpl.name;
      window.AppState.customLayout.instructions = tmpl.instructions || [];
      if (tmpl.college_profile) {
        window.AppState.customLayout.college_profile = tmpl.college_profile;
        if (tmpl.college_profile.institution_name) {
          window.AppState.customLayout.institution_name = tmpl.college_profile.institution_name;
        }
      }

      this.renderSectionsList();
      this.updateTotalMarksIndicator();
      showToast(`Applied ${tmpl.name} marking scheme preset.`, "info");
    }
  },

  async downloadSchemeTemplate() {
    try {
      const res = await fetch(`${API_BASE}/api/blueprint/marking-scheme-template`);
      const data = await res.json();
      if (data.success) {
        const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data.template, null, 2));
        const a = document.createElement("a");
        a.setAttribute("href", jsonStr);
        a.setAttribute("download", "university_marking_scheme_format.json");
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("Marking scheme template downloaded.", "success");
      }
    } catch (err) {
      console.error(err);
      showToast("Failed to download template.", "error");
    }
  },

  async uploadMarkingSchemeFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/blueprint/upload-marking-scheme`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.success && data.marking_scheme) {
        const scheme = data.marking_scheme;
        window.AppState.currentBlueprintConfig.sections = window.normalizeSections(scheme.sections);
        window.AppState.unitPlanAuto = true;
        window.AppState.currentBlueprintConfig.total_marks = scheme.total_marks;
        window.AppState.currentBlueprintConfig.duration = scheme.duration;
        window.AppState.currentBlueprintConfig.exam_title = scheme.exam_title;
        if (scheme.instructions && scheme.instructions.length > 0) {
          window.AppState.currentBlueprintConfig.instructions = scheme.instructions;
          window.AppState.customLayout.instructions = scheme.instructions;
        }

        document.getElementById("blueprint-total-marks").value = scheme.total_marks;
        document.getElementById("blueprint-duration").value = scheme.duration;
        document.getElementById("blueprint-exam-title").value = scheme.exam_title;

        this.renderSectionsList();
        this.updateTotalMarksIndicator();
        showToast(`Loaded marking scheme: ${scheme.exam_title} (${scheme.total_marks} Marks)`, "success");
      } else {
        showToast(data.error || "Failed to load marking scheme format.", "error");
      }
    } catch (err) {
      console.error(err);
      showToast("Error processing marking scheme file.", "error");
    }
  },

  addNewSection() {
    const sections = window.AppState.currentBlueprintConfig.sections;
    const nextIdx = sections.length + 1;
    const nextChar = String.fromCharCode(64 + nextIdx);

    const newSec = {
      id: `sec_${Date.now()}`,
      name: `Part ${nextChar} - Analytical & Applied Problems`,
      instructions: `Answer any four questions in Part ${nextChar}. (10 Marks each)`,
      type: "choice",
      question_count: 4,
      marks_per_question: 10,
      total_section_marks: 40,
      allowed_levels: ["L3", "L4"],
      has_internal_choice: true
    };
    window.normalizeSections([newSec]);

    sections.push(newSec);
    this.renderSectionsList();
    this.updateTotalMarksIndicator();
    showToast(`Added Section ${nextChar}.`, "success");
  },

  removeSection(idx) {
    const sections = window.AppState.currentBlueprintConfig.sections;
    if (sections.length <= 1) {
      showToast("At least one section is required.", "error");
      return;
    }

    sections.splice(idx, 1);
    this.renderSectionsList();
    this.updateTotalMarksIndicator();
    showToast("Section removed.", "info");
  },

  sectionTotal(sec) {
    return (sec.question_marks || []).reduce((a, b) => a + Number(b || 0), 0);
  },

  questionLabel(secIdx, qIdx) {
    const fmt = window.AppState.numberingFormat;
    if (window.AppState.numberingStyle === "sub") {
      return window.formatQuestionLabel(fmt, secIdx + 1, String.fromCharCode(97 + (qIdx % 26)));
    }
    let n = 0;
    const secs = window.AppState.currentBlueprintConfig.sections || [];
    for (let i = 0; i < secIdx; i++) n += secs[i].question_count || 0;
    return fmt ? window.formatQuestionLabel(fmt, n + qIdx + 1) : `Q${n + qIdx + 1}`;
  },

  renderSectionsList() {
    const container = document.getElementById("blueprint-sections-container");
    if (!container) return;

    const sections = window.normalizeSections(window.AppState.currentBlueprintConfig.sections || []);
    const esc = window.escapeHtml;
    container.innerHTML = "";

    sections.forEach((sec, idx) => {
      const card = document.createElement("div");
      card.className = "scheme-section-item";
      const totalM = this.sectionTotal(sec);
      const subMode = window.AppState.numberingStyle === "sub";

      const rowsHtml = sec.question_marks.map((m, qi) => `
        <tr data-q="${qi}">
          <td class="q-label-cell">${this.questionLabel(idx, qi)}</td>
          <td><input type="number" class="form-input q-marks-input" min="1" max="50" value="${m}" data-field="marks" aria-label="Marks"></td>
          <td class="q-or-cell"><label class="q-or-toggle"><input type="checkbox" data-field="or" ${sec.question_choices[qi] ? "checked" : ""}><span>Add OR</span></label></td>
          <td><input type="number" class="form-input q-marks-input" min="1" max="50" value="${sec.or_marks[qi]}" data-field="ormarks" ${sec.question_choices[qi] ? "" : "disabled"} aria-label="OR question marks"></td>
        </tr>`).join("");

      card.innerHTML = `
        <div class="sec-head-row">
          <input type="text" class="form-input sec-name-input" value="${esc(sec.name)}" data-role="name" placeholder="Section / Question title">
          <div class="sec-head-actions">
            <span class="marks-badge" data-role="total">${totalM} Marks</span>
            <button class="btn-icon" type="button" title="Remove this section" data-role="delete">
              <svg class="icon-svg icon-sm" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>

        <div class="form-group" style="margin-bottom: 8px;">
          <input type="text" class="form-input" value="${esc(sec.instructions)}" data-role="instr" style="font-size:12px; padding:4px 8px;" placeholder="Section instructions">
        </div>

        <div class="sec-controls-row">
          <div>
            <label class="form-label sm-label">${subMode ? "Sub-questions" : "Questions"}</label>
            <input type="number" class="form-input sm-input" min="1" max="26" value="${sec.question_count}" data-role="qcount">
          </div>
          <div>
            <label class="form-label sm-label">Marks each</label>
            <input type="number" class="form-input sm-input" min="1" max="50" value="${sec.marks_per_question}" data-role="mq">
          </div>
          <label class="q-or-toggle sec-or-master" title="Tick or untick OR for every question at once">
            <input type="checkbox" data-role="or-all" ${sec.question_choices.every(Boolean) ? "checked" : ""}>
            <span>OR on all</span>
          </label>
        </div>

        <div class="q-table-wrap">
          <table class="q-config-table">
            <thead><tr><th>${subMode ? "Question" : "No."}</th><th>Marks</th><th>OR option</th><th>OR marks</th></tr></thead>
            <tbody>${rowsHtml}</tbody>
          </table>
        </div>
        <div class="sec-hint">OR questions are alternatives, so they are not added to the ${totalM}-mark section total.</div>

        <div class="sec-levels-row">
          <span class="sec-levels-label">Allowed Bloom Levels:</span>
          ${["L1", "L2", "L3", "L4", "L5", "L6"].map(lvl => `
            <label class="lvl-chip">
              <input type="checkbox" data-sec-lvl="${idx}" value="${lvl}" ${(sec.allowed_levels || []).includes(lvl) ? "checked" : ""}>
              <span>${lvl}</span>
            </label>`).join("")}
        </div>
      `;
      container.appendChild(card);

      const q = (sel) => card.querySelector(sel);
      const refreshTotals = () => {
        sec.total_section_marks = this.sectionTotal(sec);
        q('[data-role="total"]').innerText = `${sec.total_section_marks} Marks`;
        q(".sec-hint").innerText = `OR questions are alternatives, so they are not added to the ${sec.total_section_marks}-mark section total.`;
        sec.has_internal_choice = sec.question_choices.some(Boolean);
        q('[data-role="or-all"]').checked = sec.question_choices.every(Boolean);
        this.updateTotalMarksIndicator();
        this.renderUnitPlanner();
      };

      q('[data-role="name"]').addEventListener("input", e => { sec.name = e.target.value; });
      q('[data-role="instr"]').addEventListener("input", e => { sec.instructions = e.target.value; });

      // Per-question edits
      card.querySelectorAll("tbody tr").forEach(tr => {
        const qi = parseInt(tr.getAttribute("data-q"));
        const marksIn = tr.querySelector('[data-field="marks"]');
        const orBox = tr.querySelector('[data-field="or"]');
        const orMarks = tr.querySelector('[data-field="ormarks"]');
        marksIn.addEventListener("input", () => {
          const old = sec.question_marks[qi];
          const v = Math.max(1, parseInt(marksIn.value) || 1);
          if (sec.or_marks[qi] === old) { sec.or_marks[qi] = v; orMarks.value = v; }
          sec.question_marks[qi] = v;
          refreshTotals();
        });
        orBox.addEventListener("change", () => {
          sec.question_choices[qi] = orBox.checked;
          orMarks.disabled = !orBox.checked;
          refreshTotals();
        });
        orMarks.addEventListener("input", () => {
          sec.or_marks[qi] = Math.max(1, parseInt(orMarks.value) || 1);
        });
      });

      q('[data-role="or-all"]').addEventListener("change", e => {
        sec.question_choices = sec.question_choices.map(() => e.target.checked);
        this.renderSectionsList();
        this.updateTotalMarksIndicator();
      });

      // Number of questions / default marks
      q('[data-role="qcount"]').addEventListener("change", e => {
        const n = Math.min(26, Math.max(1, parseInt(e.target.value) || 1));
        const dm = parseInt(sec.marks_per_question) || 2;
        while (sec.question_marks.length < n) {
          sec.question_marks.push(dm); sec.question_choices.push(false); sec.or_marks.push(dm);
        }
        sec.question_marks.length = n; sec.question_choices.length = n; sec.or_marks.length = n;
        sec.question_count = n;
        sec.total_section_marks = this.sectionTotal(sec);
        this.renderSectionsList();
        this.updateTotalMarksIndicator();
        this.renderUnitPlanner();
      });
      q('[data-role="mq"]').addEventListener("change", e => {
        const mq = Math.max(1, parseInt(e.target.value) || 1);
        sec.marks_per_question = mq;
        sec.question_marks = sec.question_marks.map(() => mq);
        sec.or_marks = sec.or_marks.map(() => mq);
        this.renderSectionsList();
        this.updateTotalMarksIndicator();
        this.renderUnitPlanner();
      });

      card.querySelectorAll(`[data-sec-lvl="${idx}"]`).forEach(cb => {
        cb.addEventListener("change", () => {
          const selected = [];
          card.querySelectorAll(`[data-sec-lvl="${idx}"]:checked`).forEach(c => selected.push(c.value));
          sec.allowed_levels = selected.length > 0 ? selected : ["L2"];
        });
      });

      q('[data-role="delete"]').addEventListener("click", () => this.removeSection(idx));
    });
  },

  updateTotalMarksIndicator() {
    const sections = window.AppState.currentBlueprintConfig.sections || [];
    window.normalizeSections(sections);
    const computedTotal = sections.reduce((acc, s) => acc + this.sectionTotal(s), 0);
    const indicator = document.getElementById("computed-blueprint-marks");
    if (indicator) {
      indicator.innerText = `${computedTotal} Marks`;
    }

    const totalMarksInput = document.getElementById("blueprint-total-marks");
    if (totalMarksInput && parseInt(totalMarksInput.value) !== computedTotal) {
      totalMarksInput.value = computedTotal;
      window.AppState.currentBlueprintConfig.total_marks = computedTotal;
    }
  },

  // ------------------------------------------------------------------
  // Unit-wise marks weightage and Bloom levels
  // ------------------------------------------------------------------
  planTotalMarks() {
    return parseInt(document.getElementById("blueprint-total-marks")?.value) || window.AppState.currentBlueprintConfig.total_marks || 0;
  },

  renderUnitPlanner() {
    const body = document.getElementById("unit-planner-body");
    if (!body) return;
    const syl = window.getActiveSyllabus ? window.getActiveSyllabus() : window.AppState.currentSyllabus;
    const plan = window.AppState.unitPlan;
    const enableBox = document.getElementById("unit-plan-enable");
    if (enableBox) enableBox.checked = !!plan.enabled;

    if (!syl || !syl.units || !syl.units.length) {
      body.innerHTML = '<div class="planner-empty">Load a syllabus (Stage 1) or upload a question set to plan unit-wise marks.</div>';
      return;
    }

    const total = this.planTotalMarks();
    const prev = {};
    (plan.units || []).forEach(u => { prev[u.unit_num] = u; });
    const n = syl.units.length;
    const base = Math.floor(total / n);
    let extra = total - base * n;
    plan.units = syl.units.map((u, i) => {
      const old = prev[u.unit_num];
      const even = base + (i < extra ? 1 : 0);
      return {
        unit_num: u.unit_num,
        title: u.title,
        co: u.co,
        marks: (old && window.AppState.unitPlanAuto === false) ? old.marks : even,
        levels: old ? old.levels : []          // default: no Bloom level selected
      };
    });

    const esc = window.escapeHtml;
    const levelNames = { L1: "Remember", L2: "Understand", L3: "Apply", L4: "Analyze", L5: "Evaluate", L6: "Create" };
    body.innerHTML = `
      <div class="q-table-wrap">
        <table class="q-config-table unit-plan-table">
          <thead><tr><th>Unit</th><th>Marks</th><th>Share</th><th>Bloom levels for this unit <span class="th-note">(none ticked = any level)</span></th></tr></thead>
          <tbody>
            ${plan.units.map((u, i) => `
              <tr data-i="${i}">
                <td class="unit-name-cell"><strong>Unit ${esc(u.unit_num)}</strong><span>${esc(u.title)}</span></td>
                <td><input type="number" class="form-input q-marks-input" min="0" max="500" step="1" value="${u.marks}" data-field="marks" ${plan.enabled ? "" : "disabled"} aria-label="Marks for unit ${esc(u.unit_num)}"></td>
                <td class="unit-share" data-role="share">0%</td>
                <td>
                  <div class="lvl-chip-row">
                    ${["L1","L2","L3","L4","L5","L6"].map(l => `
                      <label class="lvl-chip" title="${levelNames[l]}">
                        <input type="checkbox" data-lvl="${l}" ${u.levels.includes(l) ? "checked" : ""}><span>${l}</span>
                      </label>`).join("")}
                  </div>
                </td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
      <div class="planner-total" id="unit-plan-total"></div>`;

    const refreshTotals = () => {
      const sum = plan.units.reduce((a, u) => a + (Number(u.marks) || 0), 0);
      const el = document.getElementById("unit-plan-total");
      const paperTotal = this.planTotalMarks();
      if (el) {
        if (!plan.enabled) {
          el.className = "planner-total";
          el.textContent = "Unit-wise marks weightage is off. Questions are spread across units automatically.";
        } else if (sum === paperTotal) {
          el.className = "planner-total ok";
          el.textContent = `Allocated ${sum} of ${paperTotal} marks.`;
        } else {
          el.className = "planner-total warn";
          el.textContent = `Allocated ${sum} of ${paperTotal} marks. The weightage will be scaled proportionally to ${paperTotal} when the paper is generated.`;
        }
      }
      body.querySelectorAll("tbody tr").forEach(tr => {
        const u = plan.units[parseInt(tr.getAttribute("data-i"))];
        const pct = sum ? Math.round((Number(u.marks) || 0) / sum * 100) : 0;
        tr.querySelector('[data-role="share"]').textContent = `${pct}%`;
      });
    };

    body.querySelectorAll("tbody tr").forEach(tr => {
      const u = plan.units[parseInt(tr.getAttribute("data-i"))];
      tr.querySelector('[data-field="marks"]').addEventListener("input", e => {
        u.marks = Math.max(0, parseInt(e.target.value) || 0);
        u._touched = true;
        window.AppState.unitPlanAuto = false;
        refreshTotals();
      });
      tr.querySelectorAll("[data-lvl]").forEach(cb => {
        cb.addEventListener("change", () => {
          u.levels = Array.from(tr.querySelectorAll("[data-lvl]:checked")).map(c => c.getAttribute("data-lvl"));
        });
      });
    });
    refreshTotals();
  },

  getUnitPlanPayload() {
    const plan = window.AppState.unitPlan;
    if (!plan || !plan.units || !plan.units.length) return null;
    return {
      enabled: true,
      use_weightage: !!plan.enabled,
      units: plan.units.map(u => ({ unit_num: u.unit_num, marks: Number(u.marks) || 0, levels: u.levels || [] }))
    };
  },

  renderSliders() {
    const container = document.getElementById("bloom-sliders-container");
    if (!container) return;

    const levels = ["L1", "L2", "L3", "L4", "L5", "L6"];
    const levelNames = {
      L1: { name: "Remembering", color: "var(--bloom-l1)" },
      L2: { name: "Understanding", color: "var(--bloom-l2)" },
      L3: { name: "Applying", color: "var(--bloom-l3)" },
      L4: { name: "Analyzing", color: "var(--bloom-l4)" },
      L5: { name: "Evaluating", color: "var(--bloom-l5)" },
      L6: { name: "Creating", color: "var(--bloom-l6)" }
    };

    container.innerHTML = "";

    levels.forEach(lvl => {
      const val = window.AppState.currentDistribution[lvl] || 0;
      const meta = levelNames[lvl];

      const card = document.createElement("div");
      card.className = "bloom-slider-card";
      card.innerHTML = `
        <div class="slider-header">
          <div class="slider-title">
            <span class="bloom-badge badge-${lvl.toLowerCase()}">${lvl}</span>
            <span>${meta.name}</span>
          </div>
          <span class="slider-pct" id="label-pct-${lvl}">${val}%</span>
        </div>
        <input type="range" class="range-slider" id="slider-${lvl}" min="0" max="60" step="5" value="${val}" style="accent-color: ${meta.color};">
      `;

      container.appendChild(card);

      const slider = card.querySelector(`#slider-${lvl}`);
      slider.addEventListener("input", (e) => {
        const newVal = parseInt(e.target.value);
        window.AppState.currentDistribution[lvl] = newVal;
        document.getElementById(`label-pct-${lvl}`).innerText = `${newVal}%`;
        this.updateDistributionVisualizer();
      });
    });

    this.updateDistributionVisualizer();
  },

  applyCognitivePreset(presetKey) {
    const presets = window.AppState.cognitivePresets;
    if (presets && presets[presetKey]) {
      const dist = presets[presetKey].distribution;
      window.AppState.currentDistribution = { ...dist };

      Object.keys(dist).forEach(lvl => {
        const slider = document.getElementById(`slider-${lvl}`);
        const label = document.getElementById(`label-pct-${lvl}`);
        if (slider) slider.value = dist[lvl];
        if (label) label.innerText = `${dist[lvl]}%`;
      });

      this.updateDistributionVisualizer();
      showToast(`Applied ${presets[presetKey].name} distribution.`, "info");
    }
  },

  autoBalanceDistribution() {
    const dist = window.AppState.currentDistribution;
    const total = Object.values(dist).reduce((a, b) => a + b, 0);

    if (total === 0) return;

    let running = 0;
    const keys = Object.keys(dist);
    keys.forEach((k, idx) => {
      if (idx === keys.length - 1) {
        dist[k] = 100 - running;
      } else {
        dist[k] = Math.round((dist[k] / total) * 100);
        running += dist[k];
      }
      const slider = document.getElementById(`slider-${k}`);
      const label = document.getElementById(`label-pct-${k}`);
      if (slider) slider.value = dist[k];
      if (label) label.innerText = `${dist[k]}%`;
    });

    this.updateDistributionVisualizer();
    showToast("Normalized Bloom distribution to exactly 100%.", "success");
  },

  updateDistributionVisualizer() {
    const dist = window.AppState.currentDistribution;
    const total = Object.values(dist).reduce((a, b) => a + b, 0);

    const totalEl = document.getElementById("bloom-total-pct");
    if (totalEl) {
      totalEl.innerText = `${total}%`;
      if (total === 100) {
        totalEl.style.color = "var(--accent-emerald)";
      } else {
        totalEl.style.color = "var(--accent-rose)";
      }
    }

    // Mini stacked visualizer bar
    const barContainer = document.getElementById("bloom-stacked-bar");
    if (barContainer) {
      barContainer.innerHTML = "";
      const levels = ["L1", "L2", "L3", "L4", "L5", "L6"];
      const colors = {
        L1: "var(--bloom-l1)",
        L2: "var(--bloom-l2)",
        L3: "var(--bloom-l3)",
        L4: "var(--bloom-l4)",
        L5: "var(--bloom-l5)",
        L6: "var(--bloom-l6)"
      };

      levels.forEach(lvl => {
        const pct = dist[lvl] || 0;
        if (pct > 0) {
          const seg = document.createElement("div");
          seg.style.width = `${pct}%`;
          seg.style.height = "100%";
          seg.style.background = colors[lvl];
          seg.title = `${lvl}: ${pct}%`;
          barContainer.appendChild(seg);
        }
      });
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  window.BlueprintModule.init();
});


// The syllabus used for generation: units derived from an uploaded question set, or the loaded syllabus
window.getActiveSyllabus = function () {
  const st = window.AppState;
  const base = (st.useUploadedSet && st.uploadedSet && st.uploadedSet.syllabus)
    ? st.uploadedSet.syllabus
    : st.currentSyllabus;
  if (!base) return base;
  // The Course Code / Course Title fields are the source of truth: the parsed syllabus only
  // remembers the values typed at parse time, so re-apply the current ones every time.
  const syl = JSON.parse(JSON.stringify(base));
  const code = document.getElementById("course-code")?.value.trim();
  const name = document.getElementById("course-name")?.value.trim();
  const dept = document.getElementById("course-dept")?.value.trim();
  if (code) syl.code = code;
  if (name) syl.name = name;
  if (dept) syl.department = dept;
  return syl;
};
