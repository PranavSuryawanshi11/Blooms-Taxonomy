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
      window.AppState.currentBlueprintConfig.sections = JSON.parse(JSON.stringify(tmpl.sections));

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
        window.AppState.currentBlueprintConfig.sections = scheme.sections;
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

  renderSectionsList() {
    const container = document.getElementById("blueprint-sections-container");
    if (!container) return;

    const sections = window.AppState.currentBlueprintConfig.sections || [];
    container.innerHTML = "";

    sections.forEach((sec, idx) => {
      const card = document.createElement("div");
      card.className = "scheme-section-item";

      let totalM = sec.question_count * sec.marks_per_question;
      if (Array.isArray(sec.question_marks) && sec.question_marks.length === sec.question_count) {
        totalM = sec.question_marks.reduce((a, b) => a + Number(b), 0);
      } else if (sec.total_section_marks) {
        totalM = sec.total_section_marks;
      }
      sec.total_section_marks = totalM;

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <input type="text" class="form-input" value="${sec.name}" id="sec-name-${idx}" style="font-weight:700; max-width:68%; padding:4px 8px; font-size:13px;" placeholder="Section Title">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="marks-badge" id="sec-total-m-${idx}">${totalM} Marks</span>
            <button class="btn-icon" title="Remove this section" id="sec-del-${idx}">
              <svg class="icon-svg icon-sm" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>

        <div class="form-group" style="margin-bottom: 8px;">
          <input type="text" class="form-input" value="${sec.instructions}" id="sec-instr-${idx}" style="font-size:12px; padding:4px 8px;" placeholder="Section Instructions">
        </div>

        <div class="grid-4" style="align-items: center; margin-bottom: 8px;">
          <div>
            <label class="form-label" style="font-size:11px; margin-bottom:2px;">Questions</label>
            <input type="number" class="form-input" min="1" max="25" value="${sec.question_count}" id="sec-qcount-${idx}" style="padding:4px 8px; font-size:12px;">
          </div>
          <div>
            <label class="form-label" style="font-size:11px; margin-bottom:2px;">Marks / Q</label>
            <input type="number" class="form-input" min="1" max="50" value="${sec.marks_per_question}" id="sec-mq-${idx}" style="padding:4px 8px; font-size:12px;">
          </div>
          <div style="grid-column: span 2; display: flex; align-items: center; gap: 8px; padding-top: 14px;">
            <label class="switch" style="width:32px; height:18px;">
              <input type="checkbox" id="sec-choice-${idx}" ${sec.has_internal_choice ? 'checked' : ''}>
              <span class="switch-slider"></span>
            </label>
            <span style="font-size:12px; color:var(--text-secondary);">Internal Choice (OR)</span>
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
          <span style="font-size:11px; font-weight:600; color:var(--text-muted);">Allowed Bloom Levels:</span>
          ${["L1", "L2", "L3", "L4", "L5", "L6"].map(lvl => {
            const isChecked = (sec.allowed_levels || []).includes(lvl);
            return `
              <label style="cursor:pointer; display:inline-flex; align-items:center; gap:3px; font-size:11px; font-family:var(--font-mono); background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); padding:1px 6px; border-radius:var(--radius-xs);">
                <input type="checkbox" data-sec-lvl="${idx}" value="${lvl}" ${isChecked ? 'checked' : ''} style="margin:0;">
                <span>${lvl}</span>
              </label>
            `;
          }).join("")}
        </div>
      `;

      container.appendChild(card);

      // Bind listeners for inline adjustments
      card.querySelector(`#sec-name-${idx}`).addEventListener("input", (e) => {
        sec.name = e.target.value;
      });

      card.querySelector(`#sec-instr-${idx}`).addEventListener("input", (e) => {
        sec.instructions = e.target.value;
      });

      const qCountInput = card.querySelector(`#sec-qcount-${idx}`);
      const mqInput = card.querySelector(`#sec-mq-${idx}`);
      const totalBadge = card.querySelector(`#sec-total-m-${idx}`);

      const recalcSection = () => {
        const qc = parseInt(qCountInput.value) || 1;
        const mq = parseInt(mqInput.value) || 1;
        sec.question_marks = null;
        sec.question_count = qc;
        sec.marks_per_question = mq;
        sec.total_section_marks = qc * mq;
        totalBadge.innerText = `${qc * mq} Marks`;
        this.updateTotalMarksIndicator();
      };

      qCountInput.addEventListener("input", recalcSection);
      mqInput.addEventListener("input", recalcSection);

      card.querySelector(`#sec-choice-${idx}`).addEventListener("change", (e) => {
        sec.has_internal_choice = e.target.checked;
      });

      card.querySelectorAll(`[data-sec-lvl="${idx}"]`).forEach(cb => {
        cb.addEventListener("change", () => {
          const selected = [];
          card.querySelectorAll(`[data-sec-lvl="${idx}"]:checked`).forEach(c => selected.push(c.value));
          sec.allowed_levels = selected.length > 0 ? selected : ["L2"];
        });
      });

      card.querySelector(`#sec-del-${idx}`).addEventListener("click", () => {
        this.removeSection(idx);
      });
    });
  },

  updateTotalMarksIndicator() {
    const sections = window.AppState.currentBlueprintConfig.sections || [];
    const computedTotal = sections.reduce((acc, s) => {
      if (Array.isArray(s.question_marks) && s.question_marks.length === s.question_count) {
        return acc + s.question_marks.reduce((a, b) => a + Number(b), 0);
      }
      if (s.total_section_marks) {
        return acc + Number(s.total_section_marks);
      }
      return acc + (s.question_count * s.marks_per_question);
    }, 0);
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
