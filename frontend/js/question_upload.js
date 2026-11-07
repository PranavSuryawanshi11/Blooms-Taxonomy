/**
 * BloomCraft AI - Upload Question Set
 * Uploads a question paper / question bank, shows the Unit names, CO and PO derived from it,
 * and offers a "Generate Question Paper" button that builds the paper from those questions.
 */

window.UploadModule = {
  init() {
    const zone = document.getElementById("qset-dropzone");
    const input = document.getElementById("qset-file-input");
    if (zone && input) {
      zone.addEventListener("click", () => input.click());
      zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
      zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("dragover"); });
      zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
      zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files.length) this.upload(e.dataTransfer.files[0]);
      });
      input.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length) this.upload(e.target.files[0]);
        input.value = "";
      });
    }
    const gen = document.getElementById("btn-qset-generate");
    if (gen) gen.addEventListener("click", () => this.generate());
    const rm = document.getElementById("btn-qset-remove");
    if (rm) rm.addEventListener("click", () => this.clear());
  },

  async upload(file) {
    if (!window.AuthModule || !window.AuthModule.authToken) {
      showToast("Please sign in first.", "error");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      showToast("File is larger than 5 MB.", "error");
      return;
    }
    const status = document.getElementById("qset-upload-status");
    if (status) { status.className = "qset-status busy"; status.textContent = `Reading ${file.name} ...`; }

    const fd = new FormData();
    fd.append("file", file);
    fd.append("course_code", document.getElementById("course-code")?.value || "CS501");
    fd.append("course_name", document.getElementById("course-name")?.value || "");

    try {
      const res = await fetch(`${API_BASE}/api/question-sets/upload`, {
        method: "POST",
        headers: window.authHeaders(),
        body: fd
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        if (status) { status.className = "qset-status error"; status.textContent = data.error || "Could not read that file."; }
        showToast(data.error || "Could not read that file.", "error");
        return;
      }
      window.AppState.uploadedSet = data;
      window.AppState.useUploadedSet = true;
      window.AppState.unitPlanAuto = true;
      window.AppState.unitPlan.units = [];
      if (status) { status.className = "qset-status ok"; status.textContent = `${data.question_count} questions found in ${data.file_name}.`; }
      this.renderResult();
      if (window.BlueprintModule) window.BlueprintModule.renderUnitPlanner();
      showToast(`Question set loaded: ${data.question_count} questions, ${data.units.length} units.`, "success");
    } catch (err) {
      console.error(err);
      if (status) { status.className = "qset-status error"; status.textContent = "Network error while uploading."; }
      showToast("Network error while uploading the question set.", "error");
    }
  },

  syncSet() {
    const d = window.AppState.uploadedSet;
    if (!d) return;
    d.set.questions = d.questions.map(q => {
      const c = Object.assign({}, q);
      delete c.marks_assumed;
      return c;
    });
    d.syllabus.units = d.units.map(u => ({
      unit_num: u.unit_num, title: u.title, co: u.co, topics: (u.topics && u.topics.length) ? u.topics : [u.title]
    }));
    d.syllabus.course_outcomes = d.course_outcomes;
  },

  marksFit(d) {
    const needed = {};
    (window.AppState.currentBlueprintConfig.sections || []).forEach(sec => {
      (sec.question_marks || []).forEach((m, i) => {
        needed[m] = (needed[m] || 0) + 1;
        if (sec.question_choices && sec.question_choices[i]) {
          const om = (sec.or_marks && sec.or_marks[i]) || m;
          needed[om] = (needed[om] || 0) + 1;
        }
      });
    });
    const have = d.marks_profile || {};
    const short = Object.keys(needed).filter(m => (have[m] || 0) < needed[m]);
    return { needed, have, short };
  },

  renderResult() {
    const wrap = document.getElementById("qset-result");
    const d = window.AppState.uploadedSet;
    if (!wrap) return;
    if (!d) { wrap.style.display = "none"; wrap.innerHTML = ""; this.refreshActiveBadge(); return; }
    const esc = window.escapeHtml;
    const fit = this.marksFit(d);
    const fmt = (o) => Object.keys(o).sort((a, b) => a - b).map(k => `${o[k]} x ${k}M`).join(", ") || "none";

    wrap.style.display = "block";
    wrap.innerHTML = `
      <div class="qset-stats">
        <div class="qset-stat"><strong>${d.question_count}</strong><span>Questions</span></div>
        <div class="qset-stat"><strong>${d.units.length}</strong><span>Units</span></div>
        <div class="qset-stat"><strong>${d.course_outcomes.length}</strong><span>Course Outcomes</span></div>
        <div class="qset-stat"><strong>${d.program_outcomes.length}</strong><span>Program Outcomes</span></div>
      </div>
      <div class="qset-note">${d.unit_source === "labels" ? "Units were read from the unit headings in your file." : "Unit names were derived from the topics of your questions. You can rename them or move a question to another unit below."}${d.assumed_marks_count ? ` ${d.assumed_marks_count} question(s) had no marks and were set to the most common value.` : ""}</div>
      ${fit.short.length ? `<div class="qset-note warn">Your set has ${esc(fmt(fit.have))}; the selected scheme needs ${esc(fmt(fit.needed))}. Questions are matched by marks first, so the paper total may differ from the scheme.</div>` : ""}

      <div class="qset-grid">
        <div>
          <h4 class="qset-h">Units and Course Outcomes</h4>
          <div class="q-table-wrap">
            <table class="q-config-table">
              <thead><tr><th>CO</th><th>Unit name (editable)</th><th>Qs</th><th>Marks</th></tr></thead>
              <tbody>
                ${d.units.map((u, i) => `
                  <tr data-ui="${i}">
                    <td><span class="co-badge">${esc(u.co)}</span></td>
                    <td><input type="text" class="form-input unit-title-input" value="${esc(u.title)}" aria-label="Unit ${u.unit_num} name"></td>
                    <td>${u.question_count}</td><td>${u.marks}</td>
                  </tr>`).join("")}
              </tbody>
            </table>
          </div>
          <div class="co-list">
            ${d.course_outcomes.map(c => `<div><span class="co-badge">${esc(c.id)}</span> ${esc(c.description)}</div>`).join("")}
          </div>
          <h4 class="qset-h">Program Outcomes used</h4>
          <div class="co-list">
            ${d.program_outcomes.map(p => `<div><span class="co-badge po">${esc(p.id)}</span> ${esc(p.title)}</div>`).join("")}
          </div>
        </div>
        <div>
          <h4 class="qset-h">Questions</h4>
          <div class="q-table-wrap qset-questions">
            <table class="q-config-table">
              <thead><tr><th>#</th><th>Question</th><th>M</th><th>BL</th><th>Unit</th><th>CO</th><th>PO</th></tr></thead>
              <tbody>
                ${d.questions.map((q, i) => `
                  <tr data-qi="${i}">
                    <td>${i + 1}</td>
                    <td class="qset-qtext" title="${esc(q.question_text)}">${esc(q.question_text.length > 90 ? q.question_text.slice(0, 90) + "..." : q.question_text)}</td>
                    <td>${q.marks}</td>
                    <td><span class="bloom-badge badge-${q.bloom_level.toLowerCase()}">${q.bloom_level}</span></td>
                    <td><select class="form-select q-unit-select" aria-label="Unit for question ${i + 1}">
                      ${d.units.map(u => `<option value="${u.unit_num}" ${u.unit_num === q.unit_num ? "selected" : ""}>U${u.unit_num}</option>`).join("")}
                    </select></td>
                    <td class="q-co-cell">${esc(q.co)}</td>
                    <td>${esc(q.po)}</td>
                  </tr>`).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>`;

    wrap.querySelectorAll(".unit-title-input").forEach(inp => {
      inp.addEventListener("change", (e) => {
        const i = parseInt(e.target.closest("tr").getAttribute("data-ui"));
        const title = e.target.value.trim() || d.units[i].title;
        d.units[i].title = title;
        d.questions.forEach(q => { if (q.unit_num === d.units[i].unit_num) q.unit_title = title; });
        this.syncSet();
        if (window.BlueprintModule) window.BlueprintModule.renderUnitPlanner();
      });
    });
    wrap.querySelectorAll(".q-unit-select").forEach(sel => {
      sel.addEventListener("change", (e) => {
        const i = parseInt(e.target.closest("tr").getAttribute("data-qi"));
        const u = d.units.find(x => x.unit_num === parseInt(e.target.value));
        if (!u) return;
        const q = d.questions[i];
        q.unit_num = u.unit_num; q.unit_title = u.title; q.co = u.co;
        q.co_description = (d.course_outcomes.find(c => c.id === u.co) || {}).description || "";
        e.target.closest("tr").querySelector(".q-co-cell").textContent = u.co;
        d.units.forEach(x => {
          const qs = d.questions.filter(z => z.unit_num === x.unit_num);
          x.question_count = qs.length; x.marks = qs.reduce((a, z) => a + z.marks, 0);
        });
        this.syncSet();
        this.renderResult();
      });
    });
    this.refreshActiveBadge();
  },

  refreshActiveBadge() {
    const badge = document.getElementById("qset-active-badge");
    const gen = document.getElementById("qset-generate-bar");
    const active = !!(window.AppState.uploadedSet && window.AppState.useUploadedSet);
    if (badge) badge.style.display = active ? "inline-flex" : "none";
    if (gen) gen.style.display = window.AppState.uploadedSet ? "flex" : "none";
    const note = document.getElementById("generation-source-note");
    if (note && active) {
      note.textContent = `Active: building the paper from your uploaded question set (${window.AppState.uploadedSet.question_count} questions).`;
      note.style.color = "var(--accent-emerald)";
    }
  },

  async generate() {
    if (!window.AppState.uploadedSet) { showToast("Upload a question set first.", "error"); return; }
    this.syncSet();
    window.AppState.useUploadedSet = true;
    this.refreshActiveBadge();
    if (window.GeneratorModule) await window.GeneratorModule.generatePaper();
  },

  clear() {
    window.AppState.uploadedSet = null;
    window.AppState.useUploadedSet = false;
    window.AppState.unitPlanAuto = true;
    window.AppState.unitPlan.units = [];
    const status = document.getElementById("qset-upload-status");
    if (status) { status.className = "qset-status"; status.textContent = "PDF, DOCX, TXT, MD, CSV or JSON (max 5 MB)"; }
    this.renderResult();
    if (window.BlueprintModule) window.BlueprintModule.renderUnitPlanner();
    const note = document.getElementById("generation-source-note");
    if (note) { note.textContent = "Active: Standard AICTE Examination Reform Policy algorithmic & cognitive engine."; note.style.color = "var(--text-secondary)"; }
    showToast("Uploaded question set removed.", "info");
  }
};

document.addEventListener("DOMContentLoaded", () => window.UploadModule.init());
