/**
 * BloomCraft AI - Question Paper Studio & Analytics Controller
 * Handles paper generation, college layout rendering (RCPIT / DJSCE), AICTE verb badges,
 * Course Outcomes (CO) fulfillment matrix, and accreditation analytics.
 * Zero emojis - 100% professional SVG icons.
 */

window.GeneratorModule = {
  currentEditingSlot: null,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    // Regenerate All Button
    const regenAllBtn = document.getElementById("btn-regenerate-all");
    if (regenAllBtn) {
      regenAllBtn.addEventListener("click", () => this.generatePaper());
    }

    // Save Edit Modal Button
    const saveEditBtn = document.getElementById("btn-save-edit-question");
    if (saveEditBtn) {
      saveEditBtn.addEventListener("click", () => this.saveQuestionEdit());
    }

    // Diagram Checkbox Toggle in Edit Modal
    const figCheckbox = document.getElementById("edit-question-has-figure");
    if (figCheckbox) {
      figCheckbox.addEventListener("change", (e) => {
        const panel = document.getElementById("edit-figure-controls-panel");
        if (panel) panel.style.display = e.target.checked ? "block" : "none";
        if (e.target.checked && (!this.currentEditingSlotTempFigure || !this.currentEditingSlotTempFigure.svg)) {
          this.synthesizeDiagramInModal();
        }
      });
    }

    // Modal Synthesize Diagram Button
    const synthDiagramBtn = document.getElementById("btn-synthesize-diagram-modal");
    if (synthDiagramBtn) {
      synthDiagramBtn.addEventListener("click", () => this.synthesizeDiagramInModal());
    }

    // Modal Remove Diagram Button
    const removeDiagramBtn = document.getElementById("btn-remove-diagram-modal");
    if (removeDiagramBtn) {
      removeDiagramBtn.addEventListener("click", () => {
        const chk = document.getElementById("edit-question-has-figure");
        if (chk) chk.checked = false;
        const panel = document.getElementById("edit-figure-controls-panel");
        if (panel) panel.style.display = "none";
        this.currentEditingSlotTempFigure = null;
        const prev = document.getElementById("edit-figure-preview-container");
        if (prev) prev.innerHTML = '<span style="font-size:12px; color:#64748B;">Diagram removed. Check the box above to generate one.</span>';
      });
    }

    // Modal SVG Code Realtime Preview
    const svgCodeArea = document.getElementById("edit-figure-svg-code");
    if (svgCodeArea) {
      svgCodeArea.addEventListener("input", (e) => {
        const prev = document.getElementById("edit-figure-preview-container");
        if (prev && e.target.value.includes("<svg")) {
          prev.innerHTML = e.target.value;
          if (this.currentEditingSlotTempFigure) {
            this.currentEditingSlotTempFigure.svg = e.target.value;
          }
        }
      });
    }
  },

  async generatePaper() {
    const syllabus = window.AppState.currentSyllabus;
    if (!syllabus || !syllabus.units || syllabus.units.length === 0) {
      showToast("Please parse or select a curriculum document first.", "error");
      window.switchTab("syllabus");
      return;
    }

    const blueprintConfig = window.AppState.currentBlueprintConfig;
    const distribution = window.AppState.currentDistribution;
    const apiConfig = window.AppState.apiConfig;
    const customLayout = window.AppState.customLayout;
    const genSource = window.AppState.generationSource || "aicte_engine";

    // Synchronize custom layout institution/exam title with blueprint
    customLayout.institution_name = blueprintConfig.institution_name;
    customLayout.exam_title = blueprintConfig.exam_title;

    const generateBtn = document.getElementById("btn-generate-paper");
    const origHtml = generateBtn ? generateBtn.innerHTML : "";
    if (generateBtn) {
      generateBtn.innerHTML = "<span>Synthesizing AICTE-Compliant Examination Paper...</span>";
      generateBtn.disabled = true;
    }

    try {
      const userId = window.AppState.currentUser?.user_id;
      const headers = { "Content-Type": "application/json" };
      if (window.AuthModule && window.AuthModule.authToken) {
        headers["Authorization"] = `Bearer ${window.AuthModule.authToken}`;
      }

      // Check if user chose to generate from their custom question sets
      let questionSetsPayload = undefined;
      if (genSource === "user_sets" || genSource === "hybrid") {
        questionSetsPayload = window.AppState.userQuestionSets;
      }

      const res = await fetch(`${API_BASE}/api/paper/generate`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          syllabus: syllabus,
          exam_config: blueprintConfig,
          distribution: distribution,
          api_config: apiConfig,
          diagram_mode: window.AppState.diagramMode || "auto",
          custom_layout: customLayout,
          question_sets: questionSetsPayload,
          user_id: userId || undefined,
          user_seed: userId || undefined
        })
      });

      const data = await res.json();
      if (data.success) {
        window.AppState.currentPaper = data.paper;
        this.renderPaper(data.paper);
        window.switchTab("studio");
        showToast("Examination paper synthesized successfully with AICTE verb standards.", "success");
        if (window.AuthModule && window.AuthModule.refreshHistory) {
          window.AuthModule.refreshHistory();
        }
      } else {
        showToast(data.error || "Failed to synthesize examination paper.", "error");
      }
    } catch (err) {
      console.error(err);
      showToast("Network error communicating with paper synthesis engine.", "error");
    } finally {
      if (generateBtn) {
        generateBtn.innerHTML = origHtml;
        generateBtn.disabled = false;
      }
    }
  },

  renderPaper(paper) {
    const container = document.getElementById("paper-render-target");
    if (!container) return;

    // Apply custom layout values to sheet header
    window.applyLayoutToExamSheet();

    // Render College Profile Header (RCPIT Shirpur / SVKM DJSCE)
    const collegeProfile = paper.college_profile;
    const instEl = document.getElementById("exam-render-inst");
    const deptEl = document.getElementById("exam-render-dept");
    const titleEl = document.getElementById("exam-render-title");
    const sessionEl = document.getElementById("exam-render-session");

    if (collegeProfile) {
      if (instEl) {
        let collegeHtml = "";
        if (collegeProfile.society) {
          collegeHtml += `<div style="font-size: 11pt; font-weight: 700; color: #334155; text-transform: none; margin-bottom: 2px;">${collegeProfile.society}</div>`;
        }
        collegeHtml += `<div style="font-size: 15pt; font-weight: 800; letter-spacing: 0.5px;">${collegeProfile.college}</div>`;
        if (collegeProfile.tagline) {
          collegeHtml += `<div style="font-size: 10pt; font-weight: 600; font-style: italic; color: #475569; margin-top: 1px;">${collegeProfile.tagline}</div>`;
        }
        if (collegeProfile.affiliation) {
          collegeHtml += `<div style="font-size: 9pt; color: #64748B; margin-top: 1px;">${collegeProfile.affiliation}</div>`;
        }
        if (collegeProfile.regional_title) {
          collegeHtml += `<div style="font-size: 11pt; font-weight: bold; color: #1E293B; margin-top: 2px;">${collegeProfile.regional_title}</div>`;
        }
        instEl.innerHTML = collegeHtml;
      }
      if (deptEl) {
        deptEl.style.display = "block";
        deptEl.innerText = collegeProfile.programme ? `Programme: ${collegeProfile.programme}` : "";
      }
      if (titleEl) {
        titleEl.innerText = collegeProfile.exam_title || paper.exam_title || "SEMESTER EXAMINATION";
      }
      if (sessionEl) {
        sessionEl.style.display = "block";
        sessionEl.innerText = collegeProfile.year_semester || "";
      }
    } else {
      if (instEl) instEl.innerText = paper.institution_name || "EXAMINATION BOARD";
      if (titleEl) titleEl.innerText = paper.exam_title || "SEMESTER EXAMINATION";
    }

    // Populate Course & Exam Metadata
    const courseEl = document.getElementById("exam-render-course");
    if (courseEl) courseEl.innerText = `${paper.course_code}: ${paper.course_name}`;

    const marksEl = document.getElementById("exam-render-marks");
    if (marksEl) marksEl.innerText = `${paper.total_marks} Marks`;

    const durEl = document.getElementById("exam-render-duration");
    if (durEl) durEl.innerText = paper.duration || "02:00 Hrs.";

    // Instructions
    const instrBox = document.getElementById("exam-render-instructions");
    if (instrBox) {
      const instrList = window.AppState.customLayout.instructions && window.AppState.customLayout.instructions.length > 0
        ? window.AppState.customLayout.instructions
        : (paper.instructions || []);
      instrBox.innerHTML = "<strong>Instructions:</strong> " + instrList.join(" | ");
    }

    // Render AICTE Model Format: Course Outcomes Covered Table
    let coCoveredBox = document.getElementById("exam-co-covered-box");
    if (!coCoveredBox) {
      coCoveredBox = document.createElement("div");
      coCoveredBox.id = "exam-co-covered-box";
      coCoveredBox.className = "exam-co-covered-box";
      instrBox.parentNode.insertBefore(coCoveredBox, container);
    }

    const cos = paper.course_outcomes || [];
    if (cos.length > 0) {
      coCoveredBox.style.display = "block";
      const coRows = cos.map(c => 
        `<tr><td style="font-weight:bold; width:12%; text-align:center; padding:5px 8px; border:1px solid #CBD5E1;">${c.id}</td><td style="padding:5px 8px; border:1px solid #CBD5E1;">${c.description}</td></tr>`
      ).join("");
      coCoveredBox.innerHTML = `
        <div style="font-weight:700; font-size:11.5px; margin-bottom:4px; color:#1E293B;">
          In this question paper following course outcomes are covered:
        </div>
        <table style="width:100%; border-collapse:collapse; font-size:11px; margin-bottom:14px; background:#F8FAFC;">
          <thead>
            <tr style="background:#E2E8F0; text-align:left;">
              <th style="padding:5px 8px; border:1px solid #CBD5E1; text-align:center;">CO No.</th>
              <th style="padding:5px 8px; border:1px solid #CBD5E1;">Course Outcomes</th>
            </tr>
          </thead>
          <tbody>${coRows}</tbody>
        </table>
      `;
    } else {
      coCoveredBox.style.display = "none";
    }

    // Render Sections & Question Rows
    container.innerHTML = "";

    (paper.sections || []).forEach((sec) => {
      const secWrapper = document.createElement("div");
      secWrapper.className = "exam-section-block";

      const banner = document.createElement("div");
      banner.className = "section-banner";
      banner.innerHTML = `
        <div class="section-banner-title">${sec.section_name}</div>
        <div class="section-banner-marks">
          ${sec.instructions} (${sec.total_marks} Marks)
        </div>
      `;
      secWrapper.appendChild(banner);

      (sec.questions || []).forEach((q) => {
        const qRow = this.createQuestionRow(q);
        secWrapper.appendChild(qRow);

        if (q.or_question) {
          const divider = document.createElement("div");
          divider.className = "or-divider-banner";
          divider.innerText = "------------- OR -------------";
          secWrapper.appendChild(divider);

          const orRow = this.createQuestionRow(q.or_question);
          secWrapper.appendChild(orRow);
        }
      });

      container.appendChild(secWrapper);
    });

    // Render Dedicated Section: Question-to-CO Fulfillment & Mapping Matrix
    let coMatrixTarget = document.getElementById("exam-co-matrix-target");
    if (!coMatrixTarget) {
      coMatrixTarget = document.createElement("div");
      coMatrixTarget.id = "exam-co-matrix-target";
      container.parentNode.appendChild(coMatrixTarget);
    }

    const coMatrix = paper.co_fulfillment_matrix || [];
    if (coMatrix.length > 0) {
      coMatrixTarget.style.display = "block";
      const matrixRows = coMatrix.map(m => `
        <tr>
          <td style="text-align:center; font-weight:bold; padding:6px; border:1px solid #CBD5E1;">${m.display_num}</td>
          <td style="padding:6px; border:1px solid #CBD5E1; font-size:11px;">${m.question_text.slice(0, 110)}...</td>
          <td style="text-align:center; font-weight:bold; padding:6px; border:1px solid #CBD5E1;">${m.marks}M</td>
          <td style="text-align:center; padding:6px; border:1px solid #CBD5E1;"><span class="bloom-badge badge-${(m.bloom_level || 'l2').toLowerCase()}">${m.bloom_level}</span></td>
          <td style="text-align:center; font-weight:700; color:#1D4ED8; padding:6px; border:1px solid #CBD5E1;">${m.aicte_verb || 'Explain'}</td>
          <td style="text-align:center; font-weight:800; color:#047857; padding:6px; border:1px solid #CBD5E1;">${m.co}</td>
          <td style="padding:6px; border:1px solid #CBD5E1; font-size:10.5px; color:#475569;">${m.co_description || ''}</td>
        </tr>
      `).join("");

      coMatrixTarget.innerHTML = `
        <div style="margin-top:28px; border-top:2px solid #0F172A; padding-top:14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="font-size:13px; font-weight:800; text-transform:uppercase; color:#0F172A; display:flex; align-items:center; gap:6px;">
              <svg class="icon-svg icon-sm" viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
              Criterion 3 (NBA / AICTE): Question-to-CO Fulfillment & Mapping Matrix
            </div>
            <span class="badge" style="background:#ECFDF5; color:#047857; border:1px solid #A7F3D0; font-size:10.5px; font-weight:700;">
              AICTE Verbs Standard Compliant
            </span>
          </div>
          <p style="font-size:11px; color:#64748B; margin:0 0 10px 0;">
            Exhaustive mapping verifying which Course Outcome (CO) each generated question fulfills along with its cognitive level and action verb.
          </p>
          <table style="width:100%; border-collapse:collapse; font-size:11px; text-align:left; background:#FFFFFF;">
            <thead>
              <tr style="background:#F1F5F9;">
                <th style="padding:6px; border:1px solid #CBD5E1; text-align:center; width:6%;">Q. No.</th>
                <th style="padding:6px; border:1px solid #CBD5E1; width:40%;">Question Statement Excerpt</th>
                <th style="padding:6px; border:1px solid #CBD5E1; text-align:center; width:6%;">Marks</th>
                <th style="padding:6px; border:1px solid #CBD5E1; text-align:center; width:9%;">Bloom Level</th>
                <th style="padding:6px; border:1px solid #CBD5E1; text-align:center; width:11%;">AICTE Verb</th>
                <th style="padding:6px; border:1px solid #CBD5E1; text-align:center; width:8%;">Fulfilled CO</th>
                <th style="padding:6px; border:1px solid #CBD5E1; width:20%;">Course Outcome Description</th>
              </tr>
            </thead>
            <tbody>${matrixRows}</tbody>
          </table>
        </div>
      `;
    } else {
      coMatrixTarget.style.display = "none";
    }

    // Update floating stats
    const totalQCount = (paper.all_questions || []).length;
    const statQ = document.getElementById("studio-stat-questions");
    if (statQ) statQ.innerText = `${totalQCount} Questions`;

    const statM = document.getElementById("studio-stat-marks");
    if (statM) statM.innerText = `${paper.total_marks} Total Marks`;
  },

  createQuestionRow(q) {
    const item = document.createElement("div");
    item.className = "question-item";
    item.id = `q-row-${q.slot_id}`;

    const bloomLvl = q.bloom_level || "L2";
    const bloomClass = `badge-${bloomLvl.toLowerCase()}`;
    const aicteVerb = q.aicte_verb || q.bloom_verb || "Explain";

    // Dynamic Technical Figure SVG rendering with header bar & controls
    let figureHtml = "";
    if (q.figure && q.figure.svg) {
      const figTitle = q.figure.title || "Technical Schematic";
      const figCap = q.figure.caption || `Figure ${q.display_num}: Schematic illustrating ${q.topic || 'the concept'}.`;
      figureHtml = `
        <div class="question-figure-box" id="q-fig-box-${q.slot_id}">
          <div class="figure-header">
            <span class="figure-title-badge">Figure ${q.display_num}: ${figTitle}</span>
            <div class="figure-actions no-print" style="display:flex; gap:6px;">
              <button class="btn-icon-xs" title="Regenerate alternative diagram" onclick="window.GeneratorModule.regenerateDiagramForQuestion('${q.slot_id}')">
                <svg class="icon-svg icon-sm" viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
              </button>
              <button class="btn-icon-xs" title="Edit diagram specifications" onclick="window.GeneratorModule.openEditModal('${q.slot_id}')">
                <svg class="icon-svg icon-sm" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button class="btn-icon-xs" title="Remove diagram" style="color:#DC2626;" onclick="window.GeneratorModule.removeDiagramFromQuestion('${q.slot_id}')">
                <svg class="icon-svg icon-sm" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
          <div class="figure-svg-wrapper">
            ${q.figure.svg}
          </div>
          <div class="figure-caption">
            ${figCap}
          </div>
        </div>
      `;
    }

    // Clean SVG icons for hover actions (Zero emojis)
    const refreshSvg = '<svg class="icon-svg icon-sm" viewBox="0 0 24 24"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>';
    const editSvg = '<svg class="icon-svg icon-sm" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
    const addDiagramSvg = '<svg class="icon-svg icon-sm" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>';

    const diagramActionBtn = !q.figure ? `
      <button class="btn-icon" title="Synthesize technical diagram / figure" onclick="window.GeneratorModule.generateDiagramForQuestion('${q.slot_id}')">
        ${addDiagramSvg}
      </button>
    ` : '';

    item.innerHTML = `
      <div class="question-main">
        <div class="question-num">${q.display_num}.</div>
        <div class="question-text-content" id="q-text-${q.slot_id}">
          <div>${q.question_text}</div>
          ${figureHtml}
        </div>
      </div>
      <div class="question-meta-group">
        <span class="bloom-badge ${bloomClass}" id="q-badge-${q.slot_id}">${bloomLvl} - ${q.bloom_name || ""}</span>
        <span class="badge badge-aicte" title="Official AICTE Action Verb" style="background:rgba(59,130,246,0.12); color:#60A5FA; border:1px solid rgba(59,130,246,0.3); font-weight:700;">
          AICTE: ${aicteVerb}
        </span>
        <span class="co-badge" title="Course Outcome fulfilled: ${q.co_description || q.co}">${q.co || "CO1"}</span>
        <span class="marks-badge">[${q.marks}M]</span>
        <div class="question-hover-actions no-print">
          ${diagramActionBtn}
          <button class="btn-icon" title="Regenerate alternative question" onclick="window.GeneratorModule.regenerateSingleQuestion('${q.slot_id}')">
            ${refreshSvg}
          </button>
          <button class="btn-icon" title="Edit question wording or marks" onclick="window.GeneratorModule.openEditModal('${q.slot_id}')">
            ${editSvg}
          </button>
        </div>
      </div>
    `;

    return item;
  },

  async regenerateSingleQuestion(slotId) {
    const paper = window.AppState.currentPaper;
    if (!paper) return;

    let targetQ = (paper.all_questions || []).find(q => q.slot_id === slotId);
    if (!targetQ) return;

    const row = document.getElementById(`q-row-${slotId}`);
    if (row) row.style.opacity = "0.4";

    try {
      const res = await fetch(`${API_BASE}/api/paper/regenerate-question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slot: {
            slot_id: targetQ.slot_id,
            display_num: targetQ.display_num,
            bloom_level: targetQ.bloom_level,
            topic: targetQ.topic,
            marks: targetQ.marks,
            unit_num: targetQ.unit_num,
            unit_title: targetQ.unit_title,
            co: targetQ.co,
            co_description: targetQ.co_description
          },
          api_config: window.AppState.apiConfig,
          diagram_mode: window.AppState.diagramMode || "auto",
          exclude_texts: [targetQ.question_text]
        })
      });

      const data = await res.json();
      if (data.success && data.question) {
        targetQ.question_text = data.question.question_text;
        targetQ.marking_scheme = data.question.marking_scheme;
        targetQ.aicte_verb = data.question.aicte_verb;
        targetQ.figure = data.question.figure;

        // Re-render paper to update matrix & question text
        this.renderPaper(paper);
        showToast(`Regenerated ${targetQ.display_num} with AICTE verb '${data.question.aicte_verb}'.`, "success");
      }
    } catch (err) {
      console.error(err);
      showToast("Error regenerating alternative question.", "error");
    } finally {
      if (row) row.style.opacity = "1";
    }
  },

  async generateDiagramForQuestion(slotId, variation = 0) {
    const paper = window.AppState.currentPaper;
    if (!paper) return;

    const targetQ = (paper.all_questions || []).find(q => q.slot_id === slotId);
    if (!targetQ) return;

    const row = document.getElementById(`q-row-${slotId}`);
    if (row) row.style.opacity = "0.5";

    try {
      showToast(`Synthesizing dynamic diagram for Question ${targetQ.display_num}...`, "info");
      const res = await fetch(`${API_BASE}/api/diagram/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: targetQ.topic,
          question_text: targetQ.question_text,
          bloom_level: targetQ.bloom_level,
          marks: targetQ.marks,
          display_num: targetQ.display_num,
          variation: variation,
          api_config: window.AppState.apiConfig
        })
      });

      const data = await res.json();
      if (data.success && data.figure) {
        targetQ.figure = data.figure;
        if (!targetQ.question_text.includes("Figure")) {
          targetQ.question_text += ` (Refer to ${data.figure.title || 'schematic'} in Figure ${targetQ.display_num} below).`;
        }
        this.renderPaper(paper);
        showToast(`Technical diagram synthesized for Question ${targetQ.display_num}.`, "success");
      } else {
        showToast(data.error || "Failed to synthesize diagram.", "error");
      }
    } catch (err) {
      console.error(err);
      showToast("Network error communicating with diagram engine.", "error");
    } finally {
      if (row) row.style.opacity = "1";
    }
  },

  async regenerateDiagramForQuestion(slotId) {
    // each regeneration asks the model for a different valid visualisation
    this._diagramRegenCount = (this._diagramRegenCount || 0) + 1;
    return this.generateDiagramForQuestion(slotId, this._diagramRegenCount);
  },

  removeDiagramFromQuestion(slotId) {
    const paper = window.AppState.currentPaper;
    if (!paper) return;

    const targetQ = (paper.all_questions || []).find(q => q.slot_id === slotId);
    if (!targetQ) return;

    targetQ.figure = null;
    this.renderPaper(paper);
    showToast(`Diagram removed from Question ${targetQ.display_num}.`, "info");
  },

  openEditModal(slotId) {
    const paper = window.AppState.currentPaper;
    if (!paper) return;

    const targetQ = (paper.all_questions || []).find(q => q.slot_id === slotId);
    if (!targetQ) return;

    this.currentEditingSlot = targetQ;
    this.currentEditingSlotTempFigure = targetQ.figure ? JSON.parse(JSON.stringify(targetQ.figure)) : null;

    document.getElementById("edit-modal-slot-title").innerHTML = `
      <svg class="icon-svg icon-sm" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
      Edit Question ${targetQ.display_num} & Technical Diagram
    `;
    document.getElementById("edit-question-text").value = targetQ.question_text;
    document.getElementById("edit-question-marks").value = targetQ.marks;
    document.getElementById("edit-question-bloom").value = targetQ.bloom_level;
    document.getElementById("edit-question-co").value = targetQ.co || "CO1";

    // Figure Controls inside Modal
    const figCheckbox = document.getElementById("edit-question-has-figure");
    const figPanel = document.getElementById("edit-figure-controls-panel");
    const previewContainer = document.getElementById("edit-figure-preview-container");

    if (targetQ.figure && targetQ.figure.svg) {
      if (figCheckbox) figCheckbox.checked = true;
      if (figPanel) figPanel.style.display = "block";
      document.getElementById("edit-figure-title").value = targetQ.figure.title || "";
      document.getElementById("edit-figure-caption").value = targetQ.figure.caption || "";
      document.getElementById("edit-figure-svg-code").value = targetQ.figure.svg || "";
      if (document.getElementById("edit-figure-type")) {
        document.getElementById("edit-figure-type").value = targetQ.figure.diagram_type || "auto";
      }
      if (previewContainer) previewContainer.innerHTML = targetQ.figure.svg;
    } else {
      if (figCheckbox) figCheckbox.checked = false;
      if (figPanel) figPanel.style.display = "none";
      document.getElementById("edit-figure-title").value = "";
      document.getElementById("edit-figure-caption").value = "";
      document.getElementById("edit-figure-svg-code").value = "";
      if (previewContainer) previewContainer.innerHTML = '<span style="font-size:12px; color:#64748B;">No diagram attached. Check the box above to generate one.</span>';
    }

    const statusSpan = document.getElementById("diagram-synth-status");
    if (statusSpan) statusSpan.innerText = "";

    document.getElementById("modal-edit-question").classList.add("active");
  },

  async synthesizeDiagramInModal() {
    if (!this.currentEditingSlot) return;

    const btn = document.getElementById("btn-synthesize-diagram-modal");
    const statusSpan = document.getElementById("diagram-synth-status");
    const origHtml = btn ? btn.innerHTML : "";
    if (btn) {
      btn.innerHTML = "<span>Synthesizing...</span>";
      btn.disabled = true;
    }
    if (statusSpan) statusSpan.innerText = "Synthesizing vector schematic...";

    const qText = document.getElementById("edit-question-text").value.trim() || this.currentEditingSlot.question_text;
    const diagType = document.getElementById("edit-figure-type").value;
    const customPrompt = document.getElementById("edit-figure-custom-prompt").value.trim();

    try {
      const res = await fetch(`${API_BASE}/api/diagram/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: this.currentEditingSlot.topic,
          question_text: qText,
          bloom_level: document.getElementById("edit-question-bloom").value,
          marks: parseInt(document.getElementById("edit-question-marks").value) || 5,
          display_num: this.currentEditingSlot.display_num,
          diagram_type: diagType,
          custom_prompt: customPrompt,
          api_config: window.AppState.apiConfig
        })
      });

      const data = await res.json();
      if (data.success && data.figure) {
        this.currentEditingSlotTempFigure = data.figure;
        document.getElementById("edit-figure-title").value = data.figure.title || "";
        document.getElementById("edit-figure-caption").value = data.figure.caption || "";
        document.getElementById("edit-figure-svg-code").value = data.figure.svg || "";
        const previewContainer = document.getElementById("edit-figure-preview-container");
        if (previewContainer) previewContainer.innerHTML = data.figure.svg;
        if (statusSpan) statusSpan.innerText = "Diagram synthesized successfully.";
        showToast("Vector diagram synthesized.", "success");
      } else {
        if (statusSpan) statusSpan.innerText = "Synthesis failed.";
        showToast(data.error || "Failed to generate diagram.", "error");
      }
    } catch (err) {
      console.error(err);
      if (statusSpan) statusSpan.innerText = "Error generating diagram.";
      showToast("Network error generating diagram.", "error");
    } finally {
      if (btn) {
        btn.innerHTML = origHtml;
        btn.disabled = false;
      }
    }
  },

  saveQuestionEdit() {
    if (!this.currentEditingSlot) return;

    const newText = document.getElementById("edit-question-text").value.trim();
    const newMarks = parseInt(document.getElementById("edit-question-marks").value) || 2;
    const newBloom = document.getElementById("edit-question-bloom").value;
    const newCO = document.getElementById("edit-question-co").value.trim();

    if (!newText) {
      showToast("Question wording cannot be empty.", "error");
      return;
    }

    this.currentEditingSlot.question_text = newText;
    this.currentEditingSlot.marks = newMarks;
    this.currentEditingSlot.bloom_level = newBloom;
    this.currentEditingSlot.co = newCO;

    // Save Figure if attached
    const hasFig = document.getElementById("edit-question-has-figure").checked;
    if (hasFig) {
      const svgCode = document.getElementById("edit-figure-svg-code").value.trim();
      const figTitle = document.getElementById("edit-figure-title").value.trim() || "Technical Schematic";
      const figCaption = document.getElementById("edit-figure-caption").value.trim() || `Figure ${this.currentEditingSlot.display_num}: Schematic for ${figTitle}`;

      if (svgCode && svgCode.includes("<svg")) {
        this.currentEditingSlot.figure = {
          figure_id: `fig_${this.currentEditingSlot.display_num}`,
          title: figTitle,
          caption: figCaption,
          svg: svgCode,
          diagram_type: document.getElementById("edit-figure-type").value
        };
      } else if (this.currentEditingSlotTempFigure) {
        this.currentEditingSlot.figure = this.currentEditingSlotTempFigure;
      }
    } else {
      this.currentEditingSlot.figure = null;
    }

    // Update match in CO matrix
    const paper = window.AppState.currentPaper;
    if (paper && paper.co_fulfillment_matrix) {
      const match = paper.co_fulfillment_matrix.find(m => m.slot_id === this.currentEditingSlot.slot_id);
      if (match) {
        match.question_text = newText;
        match.marks = newMarks;
        match.bloom_level = newBloom;
        match.co = newCO;
      }
    }

    document.getElementById("modal-edit-question").classList.remove("active");
    this.renderPaper(paper);
    showToast("Question specifications and technical diagram updated.", "success");
  },

  renderAnalytics() {
    const paper = window.AppState.currentPaper;
    if (!paper) {
      document.getElementById("analytics-empty-state").style.display = "block";
      document.getElementById("analytics-content").style.display = "none";
      return;
    }

    document.getElementById("analytics-empty-state").style.display = "none";
    document.getElementById("analytics-content").style.display = "block";

    const analytics = paper.analytics || {};
    const targetDist = analytics.target_distribution || window.AppState.currentDistribution;
    const actualDist = analytics.actual_distribution || {};
    const cogIndex = analytics.cognitive_index || 3.0;

    // Metrics Cards
    document.getElementById("metric-cog-index").innerText = `${cogIndex} / 6.0`;
    document.getElementById("metric-paper-marks").innerText = `${paper.total_marks} Marks`;
    document.getElementById("metric-questions-count").innerText = `${(paper.all_questions || []).length} Questions`;

    // Render Target vs Actual Distribution Table
    const tableBody = document.getElementById("analytics-table-body");
    tableBody.innerHTML = "";

    const levels = ["L1", "L2", "L3", "L4", "L5", "L6"];
    const levelNames = {
      L1: "Remembering",
      L2: "Understanding",
      L3: "Applying",
      L4: "Analyzing",
      L5: "Evaluating",
      L6: "Creating"
    };

    levels.forEach(lvl => {
      const targetPct = targetDist[lvl] || 0;
      const actualData = actualDist[lvl] || { count: 0, marks: 0, marks_pct: 0 };
      const diff = Math.round(actualData.marks_pct - targetPct);
      const diffSign = diff > 0 ? `+${diff}%` : `${diff}%`;
      const diffColor = Math.abs(diff) <= 5 ? "var(--accent-emerald)" : "var(--accent-amber)";

      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border-subtle)";
      tr.innerHTML = `
        <td style="padding: 10px 8px;"><span class="bloom-badge badge-${lvl.toLowerCase()}">${lvl}</span> <strong>${levelNames[lvl]}</strong></td>
        <td style="padding: 10px 8px;"><strong>${targetPct}%</strong></td>
        <td style="padding: 10px 8px;"><strong>${actualData.marks_pct}%</strong></td>
        <td style="padding: 10px 8px;">${actualData.count} Questions</td>
        <td style="padding: 10px 8px;">${actualData.marks} Marks</td>
        <td style="padding: 10px 8px; color: ${diffColor}; font-weight: bold;">${diffSign}</td>
      `;
      tableBody.appendChild(tr);
    });

    // Render Course Outcomes Attainment & Fulfillment Section
    const coContainer = document.getElementById("analytics-co-breakdown-container");
    if (coContainer) {
      coContainer.innerHTML = "";
      const coSummary = analytics.co_summary || paper.co_summary || {};
      const totalMarks = paper.total_marks || 1;

      Object.keys(coSummary).forEach(coId => {
        const item = coSummary[coId];
        const pct = Math.round((item.total_marks / totalMarks) * 100);
        const card = document.createElement("div");
        card.className = "metric-card";
        card.style.display = "block";
        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div style="font-size:14px; font-weight:700; color:#34D399; display:flex; align-items:center; gap:6px;">
              <span class="co-badge">${item.id}</span>
              <span>${item.total_marks} Marks (${pct}%)</span>
            </div>
            <span class="badge" style="background:rgba(255,255,255,0.06); font-size:11px;">${item.question_count} Questions</span>
          </div>
          <div style="font-size:12px; color:var(--text-secondary); margin-bottom:10px;">${item.description}</div>
          <div style="font-size:11.5px; color:var(--text-muted);">
            <strong>Fulfilling Questions:</strong> ${item.questions.join(", ") || "None"}
          </div>
        `;
        coContainer.appendChild(card);
      });
    }

    // Render Answer Key / Rubrics
    const rubricContainer = document.getElementById("rubrics-container");
    if (rubricContainer) {
      rubricContainer.innerHTML = "";
      (paper.all_questions || []).forEach(q => {
        const card = document.createElement("div");
        card.className = "unit-card";

        const criteriaHtml = (q.marking_scheme || []).map(c => 
          `<tr><td style="padding:5px 8px; border-bottom:1px solid rgba(255,255,255,0.04);">${c.criterion}</td><td style="padding:5px 8px; text-align:right; font-weight:bold; border-bottom:1px solid rgba(255,255,255,0.04); font-family:var(--font-mono);">${c.marks} M</td></tr>`
        ).join("");

        card.innerHTML = `
          <div class="unit-card-header" style="cursor:default;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="unit-pill">${q.display_num}</span>
              <span class="bloom-badge badge-${q.bloom_level.toLowerCase()}">${q.bloom_level}</span>
              <span class="co-badge">${q.co || "CO1"}</span>
              <span style="font-weight:600; margin-left:4px; font-size:13px;">${q.question_text.slice(0, 85)}...</span>
            </div>
            <span class="marks-badge">${q.marks} Marks</span>
          </div>
          <div class="unit-topics-body">
            <table style="width:100%; font-size:12px; border-collapse:collapse;">
              ${criteriaHtml}
            </table>
          </div>
        `;
        rubricContainer.appendChild(card);
      });
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  window.GeneratorModule.init();
});
