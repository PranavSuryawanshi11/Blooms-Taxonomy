/**
 * BloomCraft AI - College Templates
 *  - TemplateStyle : draws a college's copied header (logos, styled lines, meta rows) on the paper sheet
 *  - TemplateImport: upload an old question paper, review what was detected, save it as a template
 */

// ---------------------------------------------------------------------------
// Question label in the college's own numbering style
// ---------------------------------------------------------------------------
window.formatQuestionLabel = function (fmt, group, letter) {
  const prefix = (fmt && fmt.prefix !== undefined) ? fmt.prefix : "Q.";
  const sub = (fmt && fmt.sub) || "paren";
  const base = `${prefix}${group}`;
  if (letter === undefined || letter === null) return base;
  if (sub === "close") return `${base} ${letter})`;
  if (sub === "dot") return `${base} ${letter}.`;
  return `${base} (${letter})`;
};

// ---------------------------------------------------------------------------
// Header / meta rendering shared by the paper sheet and the review preview
// ---------------------------------------------------------------------------
window.TemplateStyle = {
  safeImg(url) {
    return typeof url === "string" && /^data:image\/(png|jpeg);base64,[A-Za-z0-9+/=]+$/.test(url) ? url : "";
  },

  headerHtml(ts) {
    const esc = window.escapeHtml;
    const style = ts.style || {};
    const lines = (ts.header_lines || []).map(h => {
      const css = [
        `font-size:${Number(h.size) || 11}pt`,
        `font-weight:${h.bold ? 700 : 400}`,
        `font-style:${h.italic ? "italic" : "normal"}`,
        `text-align:${["left", "center", "right"].includes(h.align) ? h.align : "center"}`,
        h.color && /^#[0-9a-fA-F]{6}$/.test(h.color) ? `color:${h.color}` : "",
        "line-height:1.25", "margin:0 0 1px"
      ].filter(Boolean).join(";");
      return `<div style="${css}">${esc(h.text)}</div>`;
    }).join("");

    const logos = (ts.logos || []).filter(l => this.safeImg(l.data_url));
    const pick = (pos) => logos.find(l => l.position === pos);
    const imgTag = (l) => l
      ? `<img src="${this.safeImg(l.data_url)}" alt="Logo" style="height:${Math.min(Math.max(Number(l.height_pt) || 56, 24), 120)}pt; width:auto; max-width:100%; object-fit:contain;">`
      : "";
    const left = pick("left"), right = pick("right"), center = pick("center");

    let html = "";
    if (center && !left && !right) {
      html += `<div style="text-align:center; margin-bottom:4px;">${imgTag(center)}</div>${lines}`;
    } else if (left || right) {
      html += `<div class="tpl-head-row">
        <div class="tpl-logo-cell" style="text-align:left;">${imgTag(left)}</div>
        <div class="tpl-head-text">${lines}</div>
        <div class="tpl-logo-cell" style="text-align:right;">${imgTag(right)}</div>
      </div>`;
    } else {
      html += lines;
    }
    return html;
  },

  metaHtml(ts, values) {
    const esc = window.escapeHtml;
    const rollBoxes = '<span class="roll-box-cells">' + '<span class="roll-cell"></span>'.repeat(10) + "</span>";
    const rows = (ts.meta_layout || []).map(row => {
      const cells = row.map((c, i) => {
        let val;
        if (c.key === "roll") val = rollBoxes;
        else if (c.key === "date") val = '<span class="tpl-blank">&nbsp;</span>';
        else if (values && values[c.key] !== undefined && values[c.key] !== "") val = esc(values[c.key]);
        else if (c.default) val = esc(c.default);
        else val = '<span class="tpl-blank">&nbsp;</span>';
        const align = i === 0 ? "left" : (i === row.length - 1 ? "right" : "center");
        return `<div class="tpl-meta-cell" style="text-align:${align};"><strong>${esc(c.label)}:</strong> ${val}</div>`;
      }).join("");
      return `<div class="tpl-meta-row">${cells}</div>`;
    }).join("");
    return rows;
  },

  metaValues(paper) {
    return {
      code: paper.course_code || "",
      course: paper.course_name || "",
      duration: paper.duration || "",
      marks: paper.total_marks != null ? String(paper.total_marks) : ""
    };
  },

  /** Apply (or clear) the college layout on the exam sheet. Call after sections are rendered. */
  applyToSheet(paper) {
    const sheet = document.getElementById("exam-sheet-container");
    if (!sheet) return;
    const header = sheet.querySelector(".exam-header");
    const metaGrid = sheet.querySelector(".exam-meta-grid");
    ["tpl-custom-header", "tpl-custom-meta"].forEach(id => { const el = document.getElementById(id); if (el) el.remove(); });
    const ts = paper && paper.template_style;

    const defaults = header ? header.querySelectorAll("#exam-render-inst, #exam-render-dept, #exam-render-title, #exam-render-session") : [];
    if (!ts || !(ts.header_lines || []).length) {
      defaults.forEach(el => el.classList.remove("tpl-hidden"));
      if (metaGrid) metaGrid.classList.remove("tpl-hidden");
      sheet.style.fontFamily = ""; sheet.style.fontSize = "";
      sheet.style.paddingLeft = ""; sheet.style.paddingRight = "";
      if (header) header.style.borderBottom = "";
      sheet.querySelectorAll(".section-banner-title").forEach(el => { el.style.textAlign = ""; el.style.textTransform = ""; });
      return;
    }

    const style = ts.style || {};
    defaults.forEach(el => el.classList.add("tpl-hidden"));
    if (header) {
      const box = document.createElement("div");
      box.id = "tpl-custom-header";
      box.innerHTML = this.headerHtml(ts);
      header.insertBefore(box, header.firstChild);
      header.style.borderBottom = style.header_border === "none" ? "none" : "2px solid #000";
    }
    if (metaGrid) {
      metaGrid.classList.add("tpl-hidden");
      if ((ts.meta_layout || []).length) {
        const meta = document.createElement("div");
        meta.id = "tpl-custom-meta";
        meta.className = "tpl-meta";
        meta.innerHTML = this.metaHtml(ts, this.metaValues(paper));
        metaGrid.parentNode.insertBefore(meta, metaGrid);
      } else {
        metaGrid.classList.remove("tpl-hidden");
      }
    }
    sheet.style.fontFamily = style.font_family === "sans" ? "Arial, Helvetica, sans-serif" : "'Times New Roman', Times, serif";
    sheet.style.fontSize = `${Math.min(Math.max(Number(style.base_font_size_pt) || 11, 8), 14)}pt`;
    const pad = Math.round(Math.min(Math.max((Number(style.margin_in) || 0.8) * 96, 28), 96));
    sheet.style.paddingLeft = `${pad}px`; sheet.style.paddingRight = `${pad}px`;
    const st = style.section_title || {};
    sheet.querySelectorAll(".section-banner-title").forEach(el => {
      if (st.align) el.style.textAlign = st.align;
      el.style.textTransform = st.uppercase ? "uppercase" : "none";
    });
  }
};

// ---------------------------------------------------------------------------
// Import dialog
// ---------------------------------------------------------------------------
window.TemplateImport = {
  draft: null,
  warnings: [],

  init() {
    const openBtn = document.getElementById("btn-add-college-template");
    if (openBtn) openBtn.addEventListener("click", () => this.open());
    const customBtn = document.getElementById("btn-create-custom-template");
    if (customBtn) customBtn.addEventListener("click", () => this.openManual());
    const manualBtn = document.getElementById("btn-tpl-manual");
    if (manualBtn) manualBtn.addEventListener("click", () => this.openManual());
    const editBtn = document.getElementById("btn-edit-template");
    if (editBtn) editBtn.addEventListener("click", () => this.editSelected());
    const quickBtn = document.getElementById("btn-tpl-quick-apply");
    if (quickBtn) quickBtn.addEventListener("click", () => this.applyQuickStructure());
    const delBtn = document.getElementById("btn-delete-template");
    if (delBtn) delBtn.addEventListener("click", () => this.deleteSelected());

    const zone = document.getElementById("tpl-dropzone");
    const input = document.getElementById("tpl-file-input");
    if (zone && input) {
      zone.addEventListener("click", () => input.click());
      zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
      zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("dragover"); });
      zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
      zone.addEventListener("drop", (e) => {
        e.preventDefault(); zone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files.length) this.upload(e.dataTransfer.files[0]);
      });
      input.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length) this.upload(e.target.files[0]);
        input.value = "";
      });
    }
    const save = document.getElementById("btn-tpl-save");
    if (save) save.addEventListener("click", () => this.save());
    const again = document.getElementById("btn-tpl-reupload");
    if (again) again.addEventListener("click", () => this.showStep("upload"));
    document.querySelectorAll("[data-close-tpl]").forEach(b => b.addEventListener("click", () => this.close()));
    const addLogo = document.getElementById("tpl-add-logo-input");
    if (addLogo) addLogo.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length) this.addLogoFile(e.target.files[0]);
      e.target.value = "";
    });
  },

  open() {
    const user = window.AuthModule && window.AuthModule.currentUser;
    if (!user) { showToast("Please sign in first.", "error"); return; }
    if (user.is_guest) {
      showToast("Create a free faculty account to add your college template.", "info");
      return;
    }
    this.draft = null;
    this.mode = "import";
    this.setModalTitle();
    this.showStep("upload");
    document.getElementById("modal-template-import").classList.add("active");
  },

  // ------------------------------------------------------------------ custom template (manual) mode
  ROLE_ORDER: ["society", "college", "tagline", "affiliation", "regional_title", "programme", "exam_title", "year_semester"],
  ROLE_STYLE: {
    society: { size: 11, bold: true, italic: false },
    college: { size: 15, bold: true, italic: false },
    tagline: { size: 10, bold: false, italic: true },
    affiliation: { size: 9, bold: false, italic: false },
    regional_title: { size: 11, bold: true, italic: false },
    programme: { size: 11, bold: true, italic: false },
    exam_title: { size: 12.5, bold: true, italic: false },
    year_semester: { size: 10.5, bold: false, italic: false }
  },
  SIMPLE_FIELDS: {
    society: "tpl-f-society", college: "tpl-f-college", tagline: "tpl-f-tagline", affiliation: "tpl-f-affiliation",
    regional_title: "tpl-f-regional", programme: "tpl-f-programme", exam_title: "tpl-f-exam-title", year_semester: "tpl-f-year-sem"
  },
  BLOOM_IDS: ["L1", "L2", "L3", "L4", "L5", "L6"],

  setModalTitle() {
    const el = document.getElementById("tpl-modal-title");
    if (el) el.textContent = this.mode === "manual" ? "Custom Template" : (this.mode === "edit" ? "Edit Template" : "Add Your College Template");
  },

  canUseTemplates() {
    const user = window.AuthModule && window.AuthModule.currentUser;
    if (!user) { showToast("Please sign in first.", "error"); return false; }
    if (user.is_guest) { showToast("Create a free faculty account to build and save your own template.", "info"); return false; }
    return true;
  },

  buildSections(n, per, marks) {
    const ladder = [["L1", "L2"], ["L2", "L3"], ["L3", "L4"], ["L4", "L5"], ["L5", "L6"]];
    const out = [];
    for (let i = 1; i <= n; i++) {
      out.push({
        id: `sec_${i}`, name: `Question ${i}`, instructions: "Answer all questions.", type: "compulsory",
        question_count: per, marks_per_question: marks,
        question_marks: Array(per).fill(marks), question_choices: Array(per).fill(false), or_marks: Array(per).fill(marks),
        total_section_marks: per * marks, allowed_levels: ladder[Math.min(i - 1, ladder.length - 1)].slice(), has_internal_choice: false
      });
    }
    return out;
  },

  blankDraft() {
    return {
      name: "My College Template", duration: "02:00 Hrs.", total_marks: 60,
      numbering_style: "sub", numbering_format: { prefix: "Q.", sub: "paren" },
      header_lines: [], logos: [],
      meta_layout: [
        [{ key: "code", label: "Course Code" }, { key: "course", label: "Course" }],
        [{ key: "duration", label: "Duration" }, { key: "marks", label: "Max. Marks" }, { key: "roll", label: "Roll No" }]
      ],
      show_roll_box: true,
      style: { font_family: "serif", font_name: "", base_font_size_pt: 11, page_size: "A4", margin_in: 0.8, header_border: "bottom",
        section_title: { align: "left", bold: true, uppercase: false }, marks_format: "[N]" },
      instructions: ["All questions are compulsory.", "Figures to the right indicate full marks."],
      sections: this.buildSections(4, 3, 5)
    };
  },

  ensureDraftShape(d) {
    d.header_lines = d.header_lines || [];
    d.logos = d.logos || [];
    d.meta_layout = d.meta_layout || [];
    d.instructions = d.instructions || [];
    d.style = d.style || {};
    d.numbering_format = d.numbering_format || { prefix: "Q.", sub: "paren" };
    d.sections = (d.sections || []).map((sec) => {
      const n = (sec.question_marks || []).length || sec.question_count || 1;
      sec.question_marks = sec.question_marks && sec.question_marks.length ? sec.question_marks : Array(n).fill(sec.marks_per_question || 5);
      sec.question_choices = sec.question_choices || Array(n).fill(false);
      sec.or_marks = sec.or_marks || sec.question_marks.slice();
      sec.allowed_levels = sec.allowed_levels && sec.allowed_levels.length ? sec.allowed_levels : ["L2", "L3"];
      sec.instructions = sec.instructions || "";
      return sec;
    });
    return d;
  },

  openManual() {
    if (!this.canUseTemplates()) return;
    this.mode = "manual";
    this.draft = this.ensureDraftShape(this.blankDraft());
    this.warnings = [];
    this.stats = {};
    this.setModalTitle();
    document.getElementById("modal-template-import").classList.add("active");
    this.showStep("review");
    this.renderReview();
  },

  editSelected() {
    if (!this.canUseTemplates()) return;
    const sel = document.getElementById("select-exam-template");
    const t = sel && (window.AppState.examTemplates || {})[sel.value];
    if (!t || !t.is_custom) return;
    this.mode = "edit";
    this.draft = this.ensureDraftShape(JSON.parse(JSON.stringify(t)));
    this.warnings = [];
    this.stats = {};
    this.setModalTitle();
    document.getElementById("modal-template-import").classList.add("active");
    this.showStep("review");
    this.renderReview();
  },

  // ---- simple "College details" form <-> header_lines
  renderSimpleHeader() {
    const d = this.draft;
    Object.keys(this.SIMPLE_FIELDS).forEach((role) => {
      const el = document.getElementById(this.SIMPLE_FIELDS[role]);
      if (!el) return;
      const line = d.header_lines.find((h) => h.role === role);
      el.value = line ? line.text : "";
    });
  },

  bindSimpleHeader() {
    Object.keys(this.SIMPLE_FIELDS).forEach((role) => {
      const el = document.getElementById(this.SIMPLE_FIELDS[role]);
      if (!el) return;
      el.oninput = () => {
        this.setRoleText(role, el.value);
        this.renderHeaderLines();
        this.updatePreview();
      };
    });
  },

  setRoleText(role, text) {
    const d = this.draft;
    const line = d.header_lines.find((h) => h.role === role);
    if (!String(text).trim()) {
      if (line) d.header_lines.splice(d.header_lines.indexOf(line), 1);
      return;
    }
    if (line) { line.text = text; return; }
    const rank = this.ROLE_ORDER.indexOf(role);
    let pos = 0;
    d.header_lines.forEach((h, i) => {
      const r = this.ROLE_ORDER.indexOf(h.role);
      if (r !== -1 && r < rank) pos = i + 1;
    });
    d.header_lines.splice(pos, 0, Object.assign({ text, role, color: null, uppercase: false, align: "center" }, this.ROLE_STYLE[role]));
  },

  applyQuickStructure() {
    const d = this.draft;
    if (!d) return;
    const n = parseInt(document.getElementById("tpl-q-sections").value);
    const per = parseInt(document.getElementById("tpl-q-per").value);
    const marks = parseInt(document.getElementById("tpl-q-marks").value);
    if (!(n >= 1 && n <= 12) || !(per >= 1 && per <= 26) || !(marks >= 1 && marks <= 100)) {
      showToast("Use 1-12 sections, 1-26 questions each and 1-100 marks per question.", "error");
      return;
    }
    if (n * per * marks > 500) { showToast("That adds up to more than 500 marks. Please reduce it.", "error"); return; }
    if (d.sections.length && !window.confirm("Replace the current sections with this new structure?")) return;
    d.sections = this.buildSections(n, per, marks);
    d.total_marks = n * per * marks;
    document.getElementById("tpl-total-marks").value = d.total_marks;
    this.renderSections();
    this.updatePreview();
    showToast(`Structure built: ${n} sections x ${per} questions x ${marks} marks = ${d.total_marks} marks.`, "success");
  },

  close() {
    document.getElementById("modal-template-import").classList.remove("active");
  },

  showStep(step) {
    document.getElementById("tpl-step-upload").style.display = step === "upload" ? "block" : "none";
    document.getElementById("tpl-step-review").style.display = step === "review" ? "block" : "none";
    document.getElementById("tpl-step-busy").style.display = step === "busy" ? "block" : "none";
    document.getElementById("btn-tpl-save").style.display = step === "review" ? "inline-flex" : "none";
    document.getElementById("btn-tpl-reupload").style.display = step === "review" ? "inline-flex" : "none";
    const status = document.getElementById("tpl-upload-status");
    if (status && step === "upload") { status.className = "qset-status"; status.textContent = "PDF, Word (.docx), or a photo/scan of an old paper (max 8 MB)"; }
  },

  async upload(file) {
    if (file.size > 8 * 1024 * 1024) { this.uploadError("File is larger than 8 MB."); return; }
    this.showStep("busy");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/api/templates/import`, { method: "POST", headers: window.authHeaders(), body: fd });
      const data = await res.json();
      if (!res.ok || !data.success) {
        this.showStep("upload");
        this.uploadError(data.error || "Could not read that file.");
        return;
      }
      this.draft = data.template;
      this.warnings = data.warnings || [];
      this.stats = data.stats || {};
      this.showStep("review");
      this.renderReview();
    } catch (err) {
      console.error(err);
      this.showStep("upload");
      this.uploadError("Network error while uploading.");
    }
  },

  uploadError(msg) {
    const status = document.getElementById("tpl-upload-status");
    if (status) { status.className = "qset-status error"; status.textContent = msg; }
    showToast(msg, "error");
  },

  // ------------------------------------------------------------------ review UI
  renderReview() {
    const d = this.draft;
    const esc = window.escapeHtml;
    const s = this.stats || {};
    const logoCount = (d.logos || []).length;
    const summaryEl = document.getElementById("tpl-found-summary");
    if (this.mode === "manual") {
      summaryEl.innerHTML = "Fill in your college details, choose the question structure, then press <strong>Save &amp; Use Template</strong>. Nothing is saved until you do.";
    } else if (this.mode === "edit") {
      summaryEl.innerHTML = "Edit anything below and press <strong>Save &amp; Use Template</strong> to update this template.";
    } else summaryEl.innerHTML =
      `Found <strong>${s.header_lines ?? d.header_lines.length}</strong> header lines, ` +
      `<strong>${logoCount}</strong> logo${logoCount === 1 ? "" : "s"}, ` +
      `<strong>${s.sections ?? d.sections.length}</strong> sections with <strong>${s.questions ?? 0}</strong> questions ` +
      `(${s.or_questions ?? 0} with OR) and <strong>${d.instructions.length}</strong> instructions. Check everything below, fix anything that is wrong, then save.`;
    const warn = document.getElementById("tpl-warnings");
    warn.innerHTML = this.warnings.map(w => `<div class="qset-note warn">${esc(w)}</div>`).join("");

    document.getElementById("tpl-name").value = d.name || "";
    document.getElementById("tpl-duration").value = d.duration || "";
    document.getElementById("tpl-total-marks").value = d.total_marks || 60;
    document.getElementById("tpl-instructions").value = (d.instructions || []).join("\n");
    const st = d.style || (d.style = {});
    document.getElementById("tpl-font-family").value = st.font_family || "serif";
    document.getElementById("tpl-font-size").value = st.base_font_size_pt || 11;
    document.getElementById("tpl-header-border").value = st.header_border || "bottom";
    document.getElementById("tpl-numbering-style").value = d.numbering_style || "sequential";
    const nf = d.numbering_format || (d.numbering_format = { prefix: "Q.", sub: "paren" });
    document.getElementById("tpl-num-prefix").value = nf.prefix;
    document.getElementById("tpl-num-sub").value = nf.sub;
    document.getElementById("tpl-marks-format").value = st.marks_format || "[N]";

    this.bindBasics();
    this.renderSimpleHeader();
    this.bindSimpleHeader();
    const reup = document.getElementById("btn-tpl-reupload");
    if (reup) reup.style.display = this.mode === "import" ? "inline-flex" : "none";
    this.renderHeaderLines();
    this.renderLogos();
    this.renderMeta();
    this.renderSections();
    this.updatePreview();
  },

  bindBasics() {
    const d = this.draft;
    const bind = (id, fn) => {
      const el = document.getElementById(id);
      el.oninput = el.onchange = () => { fn(el.value); this.updatePreview(); };
    };
    bind("tpl-name", v => { d.name = v; });
    bind("tpl-duration", v => { d.duration = v; });
    bind("tpl-total-marks", v => { d.total_marks = Math.max(1, parseInt(v) || 1); });
    bind("tpl-instructions", v => { d.instructions = v.split("\n").map(x => x.trim()).filter(Boolean); });
    bind("tpl-font-family", v => { d.style.font_family = v; });
    bind("tpl-font-size", v => { d.style.base_font_size_pt = Math.min(16, Math.max(8, parseFloat(v) || 11)); });
    bind("tpl-header-border", v => { d.style.header_border = v; });
    bind("tpl-numbering-style", v => { d.numbering_style = v; this.renderSections(); });
    bind("tpl-num-prefix", v => { d.numbering_format.prefix = v; this.renderSections(); });
    bind("tpl-num-sub", v => { d.numbering_format.sub = v; this.renderSections(); });
    bind("tpl-marks-format", v => { d.style.marks_format = v; });
  },

  renderHeaderLines() {
    const d = this.draft, esc = window.escapeHtml;
    const roles = ["society", "college", "tagline", "affiliation", "regional_title", "programme", "exam_title", "year_semester", "other"];
    const roleNames = { society: "Society / Trust", college: "College name", tagline: "Tagline", affiliation: "Affiliation", regional_title: "Regional title", programme: "Programme", exam_title: "Exam title", year_semester: "Year / Semester", other: "Other" };
    const box = document.getElementById("tpl-header-lines");
    box.innerHTML = d.header_lines.map((h, i) => `
      <div class="tpl-line-row" data-i="${i}">
        <select class="form-select tpl-sm" data-f="role" aria-label="Line type">${roles.map(r => `<option value="${r}" ${h.role === r ? "selected" : ""}>${roleNames[r]}</option>`).join("")}</select>
        <input type="text" class="form-input tpl-grow" data-f="text" value="${esc(h.text)}" aria-label="Header text">
        <input type="number" class="form-input tpl-num" data-f="size" min="6" max="40" step="0.5" value="${h.size}" title="Font size (pt)">
        <label class="lvl-chip" title="Bold"><input type="checkbox" data-f="bold" ${h.bold ? "checked" : ""}><span>B</span></label>
        <label class="lvl-chip" title="Italic"><input type="checkbox" data-f="italic" ${h.italic ? "checked" : ""}><span>I</span></label>
        <select class="form-select tpl-xs" data-f="align" aria-label="Alignment">${["left", "center", "right"].map(a => `<option ${h.align === a ? "selected" : ""}>${a}</option>`).join("")}</select>
        <button class="btn-icon" type="button" data-f="del" title="Remove line" aria-label="Remove line">&times;</button>
      </div>`).join("") || '<div class="planner-empty">No header lines. Add one below.</div>';
    box.querySelectorAll(".tpl-line-row").forEach(row => {
      const h = d.header_lines[parseInt(row.getAttribute("data-i"))];
      row.querySelectorAll("[data-f]").forEach(el => {
        const f = el.getAttribute("data-f");
        if (f === "del") { el.onclick = () => { d.header_lines.splice(d.header_lines.indexOf(h), 1); this.renderHeaderLines(); this.renderSimpleHeader(); this.updatePreview(); }; return; }
        el.oninput = el.onchange = () => {
          if (f === "bold" || f === "italic") h[f] = el.checked;
          else if (f === "size") h.size = Math.min(40, Math.max(6, parseFloat(el.value) || 11));
          else h[f] = el.value;
          if (f === "text" || f === "role") this.renderSimpleHeader();
          this.updatePreview();
        };
      });
    });
    document.getElementById("btn-tpl-add-line").onclick = () => {
      d.header_lines.push({ text: "New line", role: "other", size: 11, bold: false, italic: false, align: "center", color: null, uppercase: false });
      this.renderHeaderLines(); this.updatePreview();
    };
  },

  renderLogos() {
    const d = this.draft, esc = window.escapeHtml;
    const box = document.getElementById("tpl-logos");
    box.innerHTML = (d.logos || []).map((l, i) => `
      <div class="tpl-logo-item" data-i="${i}">
        <img src="${window.TemplateStyle.safeImg(l.data_url)}" alt="Logo ${i + 1}">
        <select class="form-select tpl-xs" data-f="position" aria-label="Logo position">${["left", "center", "right"].map(p => `<option ${l.position === p ? "selected" : ""}>${p}</option>`).join("")}</select>
        <label class="tpl-inline">Height <input type="number" class="form-input tpl-num" data-f="height" min="20" max="140" value="${Math.round(l.height_pt)}"> pt</label>
        <button class="btn btn-outline btn-sm" type="button" data-f="del">Remove</button>
      </div>`).join("") || '<div class="planner-empty" style="padding:10px;">No logo detected. Add your college logo (PNG or JPG).</div>';
    box.querySelectorAll(".tpl-logo-item").forEach(item => {
      const l = d.logos[parseInt(item.getAttribute("data-i"))];
      item.querySelector('[data-f="position"]').onchange = (e) => { l.position = e.target.value; this.updatePreview(); };
      item.querySelector('[data-f="height"]').oninput = (e) => { l.height_pt = Math.min(140, Math.max(20, parseFloat(e.target.value) || 56)); this.updatePreview(); };
      item.querySelector('[data-f="del"]').onclick = () => { d.logos.splice(d.logos.indexOf(l), 1); this.renderLogos(); this.updatePreview(); };
    });
    const addBtn = document.getElementById("btn-tpl-add-logo");
    addBtn.style.display = (d.logos || []).length >= 2 ? "none" : "inline-flex";
    addBtn.onclick = () => document.getElementById("tpl-add-logo-input").click();
  },

  addLogoFile(file) {
    if (!/^image\/(png|jpeg)$/.test(file.type)) { showToast("Logo must be a PNG or JPG image.", "error"); return; }
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const max = 360, r = Math.min(1, max / Math.max(img.width, img.height));
        const c = document.createElement("canvas");
        c.width = Math.max(1, Math.round(img.width * r)); c.height = Math.max(1, Math.round(img.height * r));
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        let url = c.toDataURL("image/png");
        if (url.length > 180000) url = c.toDataURL("image/jpeg", 0.85);
        if (url.length > 220000) { showToast("That logo is too large. Use a smaller image.", "error"); return; }
        const used = (this.draft.logos || []).map(l => l.position);
        this.draft.logos = this.draft.logos || [];
        this.draft.logos.push({ data_url: url, position: used.includes("left") ? "right" : "left", height_pt: 60 });
        this.renderLogos(); this.updatePreview();
      };
      img.onerror = () => showToast("Could not read that image.", "error");
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  },

  renderMeta() {
    const d = this.draft, esc = window.escapeHtml;
    const keys = ["code", "course", "duration", "marks", "roll", "date", "day", "class", "branch", "semester", "division", "batch", "other"];
    const box = document.getElementById("tpl-meta");
    box.innerHTML = (d.meta_layout || []).map((row, ri) => `
      <div class="tpl-meta-edit-row">
        ${row.map((c, ci) => `
          <div class="tpl-meta-edit-cell" data-r="${ri}" data-c="${ci}">
            <input type="text" class="form-input" data-f="label" value="${esc(c.label)}" aria-label="Label">
            <select class="form-select tpl-xs" data-f="key" aria-label="Field">${keys.map(k => `<option ${c.key === k ? "selected" : ""}>${k}</option>`).join("")}</select>
            <button class="btn-icon" type="button" data-f="del" title="Remove" aria-label="Remove field">&times;</button>
          </div>`).join("")}
      </div>`).join("") || '<div class="planner-empty" style="padding:10px;">No course / time / marks rows detected. The standard layout will be used.</div>';
    box.querySelectorAll(".tpl-meta-edit-cell").forEach(cell => {
      const row = d.meta_layout[parseInt(cell.getAttribute("data-r"))];
      const c = row[parseInt(cell.getAttribute("data-c"))];
      cell.querySelector('[data-f="label"]').oninput = (e) => { c.label = e.target.value; this.updatePreview(); };
      cell.querySelector('[data-f="key"]').onchange = (e) => { c.key = e.target.value; d.show_roll_box = d.meta_layout.some(r => r.some(x => x.key === "roll")); this.updatePreview(); };
      cell.querySelector('[data-f="del"]').onclick = () => {
        row.splice(row.indexOf(c), 1);
        d.meta_layout = d.meta_layout.filter(r => r.length);
        this.renderMeta(); this.updatePreview();
      };
    });
  },

  renderSections() {
    const d = this.draft, esc = window.escapeHtml;
    const sub = d.numbering_style === "sub";
    const label = (si, qi) => sub
      ? window.formatQuestionLabel(d.numbering_format, si + 1, String.fromCharCode(97 + (qi % 26)))
      : window.formatQuestionLabel(d.numbering_format, d.sections.slice(0, si).reduce((a, s) => a + s.question_count, 0) + qi + 1);
    const box = document.getElementById("tpl-sections");
    box.innerHTML = d.sections.map((sec, si) => `
      <div class="tpl-sec" data-s="${si}">
        <div class="tpl-sec-head">
          <input type="text" class="form-input tpl-grow" data-f="name" value="${esc(sec.name)}" aria-label="Section name">
          <span class="marks-badge" data-role="total">${sec.question_marks.reduce((a, b) => a + b, 0)} Marks</span>
          <button class="btn-icon" type="button" data-f="delsec" title="Remove section" aria-label="Remove section">&times;</button>
        </div>
        <input type="text" class="form-input" data-f="instr" value="${esc(sec.instructions)}" placeholder="Instruction shown under the heading" style="font-size:12px; padding:4px 8px; margin-bottom:6px;">
        <div class="tpl-lvl-row"><span>Bloom levels:</span>${this.BLOOM_IDS.map(l => `<label class="lvl-chip"><input type="checkbox" data-lvl="${l}" ${(sec.allowed_levels || []).includes(l) ? "checked" : ""}><span>${l}</span></label>`).join("")}</div>
        <table class="q-config-table"><thead><tr><th>${sub ? "Question" : "No."}</th><th>Marks</th><th>OR</th><th>OR marks</th><th></th></tr></thead><tbody>
          ${sec.question_marks.map((m, qi) => `
            <tr data-q="${qi}">
              <td class="q-label-cell">${esc(label(si, qi))}</td>
              <td><input type="number" class="form-input q-marks-input" min="1" max="100" value="${m}" data-f="marks"></td>
              <td><label class="q-or-toggle"><input type="checkbox" data-f="or" ${sec.question_choices[qi] ? "checked" : ""}><span>OR</span></label></td>
              <td><input type="number" class="form-input q-marks-input" min="1" max="100" value="${sec.or_marks[qi]}" data-f="ormarks" ${sec.question_choices[qi] ? "" : "disabled"}></td>
              <td><button class="btn-icon" type="button" data-f="delq" title="Remove question" aria-label="Remove question">&times;</button></td>
            </tr>`).join("")}
        </tbody></table>
        <button class="btn btn-outline btn-sm" type="button" data-f="addq" style="margin-top:6px;">+ Add question</button>
      </div>`).join("");

    const recalc = (sec) => { sec.question_count = sec.question_marks.length; sec.total_section_marks = sec.question_marks.reduce((a, b) => a + b, 0); sec.has_internal_choice = sec.question_choices.some(Boolean); };
    box.querySelectorAll(".tpl-sec").forEach(el => {
      const sec = d.sections[parseInt(el.getAttribute("data-s"))];
      el.querySelector('[data-f="name"]').oninput = (e) => { sec.name = e.target.value; };
      el.querySelector('[data-f="instr"]').oninput = (e) => { sec.instructions = e.target.value; };
      el.querySelectorAll("[data-lvl]").forEach(cb => {
        cb.onchange = () => {
          const picked = this.BLOOM_IDS.filter(l => {
            const box = el.querySelector(`[data-lvl="${l}"]`);
            return box && box.checked;
          });
          if (!picked.length) { cb.checked = true; showToast("Keep at least one Bloom level for the section.", "error"); return; }
          sec.allowed_levels = picked;
        };
      });
      el.querySelector('[data-f="delsec"]').onclick = () => {
        if (d.sections.length <= 1) { showToast("A template needs at least one section.", "error"); return; }
        d.sections.splice(d.sections.indexOf(sec), 1); this.renderSections();
      };
      el.querySelector('[data-f="addq"]').onclick = () => {
        const m = sec.question_marks[sec.question_marks.length - 1] || 5;
        if (sec.question_marks.length >= 26) return;
        sec.question_marks.push(m); sec.question_choices.push(false); sec.or_marks.push(m); recalc(sec); this.renderSections();
      };
      el.querySelectorAll("tbody tr").forEach(tr => {
        const qi = parseInt(tr.getAttribute("data-q"));
        const marksIn = tr.querySelector('[data-f="marks"]'), orBox = tr.querySelector('[data-f="or"]'), orIn = tr.querySelector('[data-f="ormarks"]');
        marksIn.oninput = () => {
          const old = sec.question_marks[qi], v = Math.max(1, parseInt(marksIn.value) || 1);
          if (sec.or_marks[qi] === old) { sec.or_marks[qi] = v; orIn.value = v; }
          sec.question_marks[qi] = v; recalc(sec);
          el.querySelector('[data-role="total"]').textContent = `${sec.total_section_marks} Marks`;
        };
        orBox.onchange = () => { sec.question_choices[qi] = orBox.checked; orIn.disabled = !orBox.checked; recalc(sec); };
        orIn.oninput = () => { sec.or_marks[qi] = Math.max(1, parseInt(orIn.value) || 1); };
        tr.querySelector('[data-f="delq"]').onclick = () => {
          if (sec.question_marks.length <= 1) { showToast("A section needs at least one question.", "error"); return; }
          sec.question_marks.splice(qi, 1); sec.question_choices.splice(qi, 1); sec.or_marks.splice(qi, 1); recalc(sec); this.renderSections();
        };
      });
    });
    document.getElementById("btn-tpl-add-section").onclick = () => {
      if (d.sections.length >= 12) return;
      d.sections.push({ id: `sec_${d.sections.length + 1}`, name: `Question ${d.sections.length + 1}`, instructions: "Answer all questions.", type: "compulsory",
        question_count: 2, marks_per_question: 5, question_marks: [5, 5], question_choices: [false, false], or_marks: [5, 5], total_section_marks: 10,
        allowed_levels: ["L2", "L3"], has_internal_choice: false });
      this.renderSections();
    };
    const total = d.sections.reduce((a, s) => a + s.question_marks.reduce((x, y) => x + y, 0), 0);
    const note = document.getElementById("tpl-marks-note");
    if (note) {
      note.textContent = `Questions add up to ${total} marks (OR alternatives are not counted). Paper total is ${d.total_marks}.`;
      note.className = "planner-total " + (total === Number(d.total_marks) ? "ok" : "warn");
    }
  },

  updatePreview() {
    const d = this.draft;
    if (!d) return;
    const box = document.getElementById("tpl-preview");
    const st = d.style || {};
    box.style.fontFamily = st.font_family === "sans" ? "Arial, Helvetica, sans-serif" : "'Times New Roman', Times, serif";
    box.style.fontSize = `${st.base_font_size_pt || 11}pt`;
    const values = { code: "CS601", course: "Machine Learning", duration: d.duration, marks: String(d.total_marks) };
    box.innerHTML = `
      <div class="tpl-prev-header" style="${st.header_border === "none" ? "" : "border-bottom:2px solid #000;"}">${window.TemplateStyle.headerHtml(d)}</div>
      <div class="tpl-meta">${window.TemplateStyle.metaHtml(d, values)}</div>`;
    const total = d.sections.reduce((a, s) => a + s.question_marks.reduce((x, y) => x + y, 0), 0);
    const note = document.getElementById("tpl-marks-note");
    if (note) {
      note.textContent = `Questions add up to ${total} marks (OR alternatives are not counted). Paper total is ${d.total_marks}.`;
      note.className = "planner-total " + (total === Number(d.total_marks) ? "ok" : "warn");
    }
  },

  // ------------------------------------------------------------------ save
  async save() {
    const d = this.draft;
    if (!d) return;
    if (!d.name.trim()) { showToast("Give the template a name.", "error"); return; }
    if (!d.header_lines.length) { showToast("Enter your college name in the College details section.", "error"); return; }
    const sumMarks = d.sections.reduce((a, sec) => a + sec.question_marks.reduce((x, y) => x + y, 0), 0);
    if (sumMarks !== Number(d.total_marks)) {
      if (window.confirm(`Your questions add up to ${sumMarks} marks but the paper total is ${d.total_marks}.\n\nPress OK to set the total to ${sumMarks}, or Cancel to go back and fix the marks.`)) {
        d.total_marks = sumMarks;
        document.getElementById("tpl-total-marks").value = sumMarks;
      } else return;
    }
    const btn = document.getElementById("btn-tpl-save");
    btn.disabled = true;
    try {
      const res = await fetch(`${API_BASE}/api/templates`, {
        method: "POST",
        headers: window.authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ id: d.id, template: d })
      });
      const data = await res.json();
      if (!res.ok || !data.success) { showToast(data.error || "Could not save the template.", "error"); return; }
      await this.reloadTemplates(data.template_id);
      this.close();
      showToast(`Template "${data.template.name}" saved. Your papers will now use its header, logo and layout.`, "success");
    } catch (err) {
      console.error(err);
      showToast("Network error while saving the template.", "error");
    } finally {
      btn.disabled = false;
    }
  },

  // ------------------------------------------------------------------ list management
  async reloadTemplates(selectId) {
    try {
      const res = await fetch(`${API_BASE}/api/blueprint/presets`, { headers: window.authHeaders() });
      const data = await res.json();
      if (!data.success) return;
      window.AppState.examTemplates = data.exam_templates;
      this.populateSelect(selectId);
      if (selectId && window.BlueprintModule) window.BlueprintModule.onTemplateSelect(selectId);
    } catch (e) { console.warn("Template reload failed", e); }
  },

  populateSelect(selectId) {
    const sel = document.getElementById("select-exam-template");
    if (!sel) return;
    const current = selectId || sel.value;
    const old = document.getElementById("optgroup-custom-templates");
    if (old) old.remove();
    const mine = Object.values(window.AppState.examTemplates || {}).filter(t => t.is_custom);
    if (mine.length) {
      const grp = document.createElement("optgroup");
      grp.id = "optgroup-custom-templates";
      grp.label = "My College Templates";
      mine.forEach(t => {
        const o = document.createElement("option");
        o.value = t.id;
        o.textContent = `${t.name} - ${t.total_marks} Marks (${t.duration})`;
        grp.appendChild(o);
      });
      sel.insertBefore(grp, sel.firstChild);
    }
    sel.value = (window.AppState.examTemplates || {})[current] ? current : sel.options[0].value;
    this.updateDeleteButton();
  },

  updateDeleteButton() {
    const sel = document.getElementById("select-exam-template");
    const btn = document.getElementById("btn-delete-template");
    if (!sel || !btn) return;
    const t = (window.AppState.examTemplates || {})[sel.value];
    btn.style.display = t && t.is_custom ? "inline-flex" : "none";
    const editBtn = document.getElementById("btn-edit-template");
    if (editBtn) editBtn.style.display = t && t.is_custom ? "inline-flex" : "none";
  },

  async deleteSelected() {
    const sel = document.getElementById("select-exam-template");
    const t = (window.AppState.examTemplates || {})[sel.value];
    if (!t || !t.is_custom) return;
    if (!window.confirm(`Delete the template "${t.name}"? Papers you already generated are not affected.`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/templates/${encodeURIComponent(t.id)}`, { method: "DELETE", headers: window.authHeaders() });
      const data = await res.json();
      if (!data.success) { showToast(data.error || "Could not delete.", "error"); return; }
      await this.reloadTemplates();
      const fallback = window.AppState.examTemplates["rcpit_sem_65"] ? "rcpit_sem_65" : "end_sem_100";
      document.getElementById("select-exam-template").value = fallback;
      window.BlueprintModule.onTemplateSelect(fallback);
      this.updateDeleteButton();
      showToast("Template deleted.", "info");
    } catch (e) { showToast("Network error while deleting.", "error"); }
  }
};

document.addEventListener("DOMContentLoaded", () => window.TemplateImport.init());
