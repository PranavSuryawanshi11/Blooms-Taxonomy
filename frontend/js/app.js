/**
 * BloomCraft AI - Core Application Controller
 * Global application state, routing, institutional layouts, toasts, and modals.
 * Zero emojis - 100% professional SVG icons.
 */

const resolveApiBase = () => {
  if (typeof window === "undefined") return "http://127.0.0.1:5000";
  const proto = window.location.protocol;
  const origin = window.location.origin;
  const port = window.location.port;
  if (proto === "file:" || !origin || origin === "null" || (port && port !== "5000")) {
    return "http://127.0.0.1:5000";
  }
  return origin;
};
window.API_BASE = resolveApiBase();
const API_BASE = window.API_BASE;

// Stable per-browser device id (used for the one-paper guest limit)
window.getDeviceId = function () {
  try {
    let id = localStorage.getItem("bloom_device_id");
    if (!id || id.length < 16) {
      const rnd = (window.crypto && crypto.getRandomValues)
        ? Array.from(crypto.getRandomValues(new Uint8Array(24))).map(b => b.toString(16).padStart(2, "0")).join("")
        : (Math.random().toString(16).slice(2) + Date.now().toString(16)).padEnd(32, "0");
      id = "dev-" + rnd;
      localStorage.setItem("bloom_device_id", id);
    }
    return id;
  } catch (e) {
    return "dev-session-" + (window.__fallbackDevice = window.__fallbackDevice || Math.random().toString(16).slice(2).padEnd(24, "0"));
  }
};

// Headers for authenticated API calls
window.authHeaders = function (extra) {
  const h = Object.assign({}, extra || {});
  const token = (window.AuthModule && window.AuthModule.authToken) || (window.AppState && window.AppState.authToken);
  if (token) h["Authorization"] = `Bearer ${token}`;
  h["X-Device-Id"] = window.getDeviceId();
  return h;
};

// Escape text before inserting into innerHTML
window.escapeHtml = function (v) {
  return String(v == null ? "" : v).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
};

// Make every section carry explicit per-question marks / OR flags / OR marks so the UI can edit them
window.normalizeSections = function (sections) {
  (sections || []).forEach(sec => {
    const n = Math.max(1, parseInt(sec.question_count) || 1);
    const dflt = parseInt(sec.marks_per_question) || 2;
    const marks = [];
    for (let i = 0; i < n; i++) {
      const v = Array.isArray(sec.question_marks) ? parseInt(sec.question_marks[i]) : NaN;
      marks.push(v > 0 ? v : dflt);
    }
    sec.question_count = n;
    sec.question_marks = marks;
    sec.question_choices = marks.map((m, i) => {
      if (Array.isArray(sec.question_choices) && i < sec.question_choices.length) return !!sec.question_choices[i];
      return !!sec.has_internal_choice && m >= 5;
    });
    sec.or_marks = marks.map((m, i) => {
      const v = Array.isArray(sec.or_marks) ? parseInt(sec.or_marks[i]) : NaN;
      return v > 0 ? v : m;
    });
    sec.total_section_marks = marks.reduce((a, b) => a + b, 0);
  });
  return sections;
};

// Global Application State
window.AppState = {
  currentTab: 'syllabus',
  sampleSyllabi: [],
  currentSyllabus: null,
  extractedSyllabusText: "",
  examTemplates: {},
  cognitivePresets: {},
  bloomLevels: {},
  currentBlueprintConfig: {
    institution_name: "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING",
    exam_title: "SEMESTER END EXAMINATION",
    duration: "3 Hours",
    total_marks: 100,
    instructions: [
      "Answer all questions from Part A and any four questions from Part B.",
      "Make suitable assumptions wherever necessary and state them clearly.",
      "Draw neat sketches and diagrams wherever required."
    ],
    sections: []
  },
  customLayout: {
    institution_name: "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING",
    department_name: "",
    exam_title: "SEMESTER END EXAMINATION",
    academic_session: "",
    degree_branch: "B.Tech (CSE) Semester V",
    regulation: "R20 / CBCS",
    roll_box_label: "Roll No / USN:",
    roll_format: "boxes", // "boxes" or "line"
    font_family: "serif", // "serif" or "sans"
    column_layout: "1-col", // "1-col" or "2-col"
    show_bloom_tags: true,
    show_co_tags: true,
    show_marks_tags: true,
    instructions: [
      "Answer all questions from Part A and any four questions from Part B.",
      "Make suitable assumptions wherever necessary and state them clearly."
    ]
  },
  currentDistribution: {
    L1: 20,
    L2: 25,
    L3: 25,
    L4: 15,
    L5: 10,
    L6: 5
  },
  currentPaper: null,
  currentUser: null,
  numberingStyle: "sub",
  uploadedSet: null,          // parsed result of an uploaded question set (units / CO / PO / questions)
  useUploadedSet: false,
  unitPlan: { enabled: true, units: [] },
  guestQuota: null,
  diagramMode: localStorage.getItem("bloom_diagram_mode") || "auto",
  apiConfig: {
    groq_key: localStorage.getItem("bloom_groq_key") || "",
    openrouter_key: localStorage.getItem("bloom_openrouter_key") || "",
    cerebras_key: localStorage.getItem("bloom_cerebras_key") || "",
    mistral_key: localStorage.getItem("bloom_mistral_key") || ""
  }
};

document.addEventListener("DOMContentLoaded", async () => {
  initTabs();
  initModals();
  initCustomLayoutModal();
  initAcademicYearAndCourseFields();
  if (window.AuthModule && window.AuthModule.init) {
    await window.AuthModule.init();
  }
  await loadPresets();
  await loadSampleSyllabi();
  // Resume exactly where the faculty member left off (refresh / reload within the same browser session)
  if (window.SessionModule) {
    window.SessionModule.restore();
    window.SessionModule._booted = true;
  }
});

// Tab Routing System
function initTabs() {
  const tabButtons = document.querySelectorAll(".step-tab");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  window.AppState.currentTab = tabId;
  if (window.StageGuide) window.StageGuide.onTab(tabId);

  // Update tab navigation UI
  document.querySelectorAll(".step-tab").forEach(tab => {
    if (tab.getAttribute("data-tab") === tabId) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });

  // Toggle tab contents
  const tabs = ["syllabus", "blueprint", "studio", "analytics"];
  tabs.forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    if (el) {
      el.style.display = (t === tabId) ? "block" : "none";
    }
  });

  // Trigger tab-specific refresh
  if (tabId === 'blueprint') {
    if (window.BlueprintModule && window.BlueprintModule.refresh) {
      window.BlueprintModule.refresh();
    }
  } else if (tabId === 'analytics') {
    if (window.GeneratorModule && window.GeneratorModule.renderAnalytics) {
      window.GeneratorModule.renderAnalytics();
    }
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Preset Loader
async function loadPresets() {
  try {
    const res = await fetch(`${API_BASE}/api/blueprint/presets`, { headers: window.authHeaders() });
    const data = await res.json();
    if (data.success) {
      window.AppState.bloomLevels = data.bloom_levels;
      window.AppState.cognitivePresets = data.cognitive_presets;
      window.AppState.examTemplates = data.exam_templates;
      
      // Default template: RCPIT 65 or Semester End 100
      const defaultTmplKey = data.exam_templates["rcpit_sem_65"] ? "rcpit_sem_65" : "end_sem_100";
      if (data.exam_templates && data.exam_templates[defaultTmplKey]) {
        const defaultTmpl = data.exam_templates[defaultTmplKey];
        window.AppState.currentBlueprintConfig.template_id = defaultTmplKey;
        window.AppState.currentBlueprintConfig.college_profile = defaultTmpl.college_profile || null;
        window.AppState.currentBlueprintConfig.total_marks = defaultTmpl.total_marks;
        window.AppState.currentBlueprintConfig.duration = defaultTmpl.duration;
        window.AppState.currentBlueprintConfig.exam_title = defaultTmpl.name;
        window.AppState.currentBlueprintConfig.instructions = defaultTmpl.instructions || [];
        window.AppState.currentBlueprintConfig.sections = window.normalizeSections(JSON.parse(
          JSON.stringify(defaultTmpl.sections)
        ));
        window.AppState.numberingStyle = defaultTmpl.numbering_style || "sequential";
        window.AppState.numberingFormat = defaultTmpl.numbering_format || null;
        if (defaultTmpl.college_profile) {
          window.AppState.customLayout.college_profile = defaultTmpl.college_profile;
          if (defaultTmpl.college_profile.institution_name) {
            window.AppState.customLayout.institution_name = defaultTmpl.college_profile.institution_name;
          }
        }
      }
    }
  } catch (err) {
    console.error("Failed to load presets:", err);
    showToast("Unable to connect to backend server.", "error");
  }
}

// Sample Syllabi Loader
async function loadSampleSyllabi() {
  try {
    const res = await fetch(`${API_BASE}/api/syllabus/samples`);
    const data = await res.json();
    if (data.success) {
      window.AppState.sampleSyllabi = data.samples;
      if (window.SyllabusModule && window.SyllabusModule.renderSamples) {
        window.SyllabusModule.renderSamples(data.samples);
      }
    }
  } catch (err) {
    console.error("Failed to load sample curricula:", err);
  }
}

// Toast Notifications (Clean SVG Icons, Zero Emojis)
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  
  let iconSvg = '';
  if (type === "success") {
    iconSvg = '<svg class="icon-svg icon-sm" style="color:var(--accent-emerald)" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>';
  } else if (type === "error") {
    iconSvg = '<svg class="icon-svg icon-sm" style="color:var(--accent-rose)" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
  } else {
    iconSvg = '<svg class="icon-svg icon-sm" style="color:var(--primary-color)" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
  }

  toast.innerHTML = `${iconSvg} <span></span>`;
  toast.querySelector("span").textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

// Modal Helpers
function initModals() {
  // Close buttons
  document.querySelectorAll("[data-close-modal]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
    });
  });

  // Close on clicking backdrop
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("active");
      }
    });
  });


}

// Custom Layout Modal Controller
function initCustomLayoutModal() {
  const openLayoutBtn = document.getElementById("btn-open-layout-customizer");
  const modal = document.getElementById("modal-custom-layout");
  const saveBtn = document.getElementById("btn-save-custom-layout");
  const quickColBtn = document.getElementById("btn-toggle-columns");

  if (openLayoutBtn && modal) {
    openLayoutBtn.addEventListener("click", () => {
      const layout = window.AppState.customLayout;
      document.getElementById("layout-inst-name").value = layout.institution_name || "";
      document.getElementById("layout-dept-name").value = layout.department_name || "";
      document.getElementById("layout-exam-title").value = layout.exam_title || "";
      document.getElementById("layout-degree-branch").value = layout.degree_branch || "";
      document.getElementById("layout-regulation").value = layout.regulation || "";
      document.getElementById("layout-roll-label").value = layout.roll_box_label || "Roll No / USN:";
      document.getElementById("layout-custom-instructions").value = (layout.instructions || []).join("\n");

      // Column buttons
      setToggleActive("btn-layout-1col", "btn-layout-2col", layout.column_layout === "2-col");
      // Font buttons
      setToggleActive("btn-font-serif", "btn-font-sans", layout.font_family === "sans");
      // Roll buttons
      setToggleActive("btn-roll-boxes", "btn-roll-line", layout.roll_format === "line");

      // Visibility switches
      document.getElementById("toggle-show-bloom").checked = layout.show_bloom_tags;
      document.getElementById("toggle-show-co").checked = layout.show_co_tags;
      document.getElementById("toggle-show-marks").checked = layout.show_marks_tags;

      modal.classList.add("active");
    });
  }

  // Column buttons in modal
  const btn1Col = document.getElementById("btn-layout-1col");
  const btn2Col = document.getElementById("btn-layout-2col");
  if (btn1Col && btn2Col) {
    btn1Col.addEventListener("click", () => setToggleActive("btn-layout-1col", "btn-layout-2col", false));
    btn2Col.addEventListener("click", () => setToggleActive("btn-layout-1col", "btn-layout-2col", true));
  }

  // Font buttons in modal
  const btnSerif = document.getElementById("btn-font-serif");
  const btnSans = document.getElementById("btn-font-sans");
  if (btnSerif && btnSans) {
    btnSerif.addEventListener("click", () => setToggleActive("btn-font-serif", "btn-font-sans", false));
    btnSans.addEventListener("click", () => setToggleActive("btn-font-serif", "btn-font-sans", true));
  }

  // Roll buttons in modal
  const btnBoxes = document.getElementById("btn-roll-boxes");
  const btnLine = document.getElementById("btn-roll-line");
  if (btnBoxes && btnLine) {
    btnBoxes.addEventListener("click", () => setToggleActive("btn-roll-boxes", "btn-roll-line", false));
    btnLine.addEventListener("click", () => setToggleActive("btn-roll-boxes", "btn-roll-line", true));
  }

  // Quick 1-col / 2-col toggle button in paper toolbar
  if (quickColBtn) {
    quickColBtn.addEventListener("click", () => {
      const is2Col = window.AppState.customLayout.column_layout === "2-col";
      window.AppState.customLayout.column_layout = is2Col ? "1-col" : "2-col";
      updateQuickColButton();
      applyLayoutToExamSheet();
      showToast(`Switched to ${window.AppState.customLayout.column_layout === '2-col' ? 'Two Columns' : 'Single Column'} layout.`, "info");
    });
  }

  // Save Custom Layout
  if (saveBtn) {
    saveBtn.addEventListener("click", () => {
      const layout = window.AppState.customLayout;
      layout.institution_name = document.getElementById("layout-inst-name").value.trim() || "EXAMINATION BOARD";
      layout.department_name = document.getElementById("layout-dept-name").value.trim();
      layout.exam_title = document.getElementById("layout-exam-title").value.trim() || "SEMESTER EXAMINATION";
      window.syncAcademicYear();
      layout.degree_branch = document.getElementById("layout-degree-branch").value.trim();
      layout.regulation = document.getElementById("layout-regulation").value.trim();
      layout.roll_box_label = document.getElementById("layout-roll-label").value.trim() || "Roll No / USN:";

      layout.column_layout = document.getElementById("btn-layout-2col").classList.contains("active") ? "2-col" : "1-col";
      layout.font_family = document.getElementById("btn-font-sans").classList.contains("active") ? "sans" : "serif";
      layout.roll_format = document.getElementById("btn-roll-line").classList.contains("active") ? "line" : "boxes";

      layout.show_bloom_tags = document.getElementById("toggle-show-bloom").checked;
      layout.show_co_tags = document.getElementById("toggle-show-co").checked;
      layout.show_marks_tags = document.getElementById("toggle-show-marks").checked;

      const rawInstr = document.getElementById("layout-custom-instructions").value.trim();
      layout.instructions = rawInstr ? rawInstr.split("\n").map(s => s.trim()).filter(Boolean) : [];

      updateQuickColButton();
      applyLayoutToExamSheet();

      modal.classList.remove("active");
      showToast("Question paper layout updated successfully.", "success");
    });
  }
}

function setToggleActive(id1, id2, isSecondActive) {
  const el1 = document.getElementById(id1);
  const el2 = document.getElementById(id2);
  if (el1 && el2) {
    if (isSecondActive) {
      el1.classList.remove("active");
      el2.classList.add("active");
    } else {
      el1.classList.add("active");
      el2.classList.remove("active");
    }
  }
}

function updateQuickColButton() {
  const label = document.getElementById("col-toggle-label");
  if (label) {
    const is2Col = window.AppState.customLayout.column_layout === "2-col";
    label.innerText = is2Col ? "1-Column Layout" : "2-Column Layout";
  }
}

function applyLayoutToExamSheet() {
  const layout = window.AppState.customLayout;
  const sheet = document.getElementById("exam-sheet-container");
  if (!sheet) return;

  // Institution & Department
  document.getElementById("exam-render-inst").innerText = layout.institution_name;
  const deptEl = document.getElementById("exam-render-dept");
  if (deptEl) {
    if (layout.department_name) {
      deptEl.innerText = layout.department_name;
      deptEl.style.display = "block";
    } else {
      deptEl.style.display = "none";
    }
  }

  // Exam Title & Session
  document.getElementById("exam-render-title").innerText = layout.exam_title;
  const sessionEl = document.getElementById("exam-render-session");
  if (sessionEl) {
    const degReg = [layout.degree_branch, layout.academic_session, layout.regulation ? `Reg: ${layout.regulation}` : ''].filter(Boolean).join(" | ");
    if (degReg) {
      sessionEl.innerText = degReg;
      sessionEl.style.display = "block";
    } else {
      sessionEl.style.display = "none";
    }
  }

  // Roll Box Label & Style
  const rollLabel = document.getElementById("exam-render-roll-label");
  if (rollLabel) rollLabel.innerText = layout.roll_box_label;

  const rollBoxContainer = document.getElementById("exam-render-roll-box");
  if (rollBoxContainer) {
    if (layout.roll_format === "line") {
      rollBoxContainer.className = "roll-line";
      rollBoxContainer.innerHTML = "";
    } else {
      rollBoxContainer.className = "roll-box-cells";
      rollBoxContainer.innerHTML = '<span class="roll-cell"></span>'.repeat(10);
    }
  }

  // Instructions
  const instrEl = document.getElementById("exam-render-instructions");
  if (instrEl && layout.instructions && layout.instructions.length > 0) {
    instrEl.innerHTML = "<strong>Instructions:</strong> " + layout.instructions.join(" | ");
  }

  // 1-Col vs 2-Col layout
  if (layout.column_layout === "2-col") {
    sheet.classList.add("layout-2col");
  } else {
    sheet.classList.remove("layout-2col");
  }

  // Font family
  if (layout.font_family === "sans") {
    sheet.classList.add("font-sans");
  } else {
    sheet.classList.remove("font-sans");
  }

  // Tag visibility classes
  sheet.classList.toggle("hide-bloom", !layout.show_bloom_tags);
  sheet.classList.toggle("hide-co", !layout.show_co_tags);
  sheet.classList.toggle("hide-marks", !layout.show_marks_tags);
}

window.showToast = showToast;
window.switchTab = switchTab;
window.applyLayoutToExamSheet = applyLayoutToExamSheet;


// ---------------------------------------------------------------------------
// Academic Year (A.Y.) - one field drives every place the year is printed
// ---------------------------------------------------------------------------
window.AY_RE = /\b20\d\d\s*[-\u2013\u2014\/]\s*(?:20)?\d\d\b/;

// Indian academic years start around June: Nov 2026 -> "2026-2027", Mar 2027 -> "2026-2027"
window.defaultAcademicYear = function () {
  const d = new Date();
  const start = d.getMonth() >= 5 ? d.getFullYear() : d.getFullYear() - 1;
  return `${start}-${start + 1}`;
};

window.getAcademicYear = function () {
  const el = document.getElementById("academic-year");
  return ((el && el.value) || "").replace(/\s+/g, " ").trim();
};

// Replace a year range in `text`; with append=true add "(A.Y.: ..)" when the text has none
window.withAcademicYear = function (text, ay, append) {
  if (!ay) return text || "";
  text = text || "";
  if (window.AY_RE.test(text)) return text.replace(new RegExp(window.AY_RE.source, "g"), () => ay);
  return append ? `${text} (A.Y.: ${ay})`.trim() : text;
};

// Keep the layout's session line in step with the A.Y. field
window.getYearSemester = function () {
  const el = document.getElementById("year-semester");
  return ((el && el.value) || "").replace(/\s+/g, " ").trim();
};

window.syncAcademicYear = function () {
  const ay = window.getAcademicYear();
  const ys = window.getYearSemester();
  window.AppState.academicYear = ay;
  window.AppState.customLayout.academic_session = [ys, ay ? `Academic Year ${ay}` : ""].filter(Boolean).join(" | ");
};

// Stamp the A.Y. on an already generated paper (live edits, print and Word export read this copy)
window.applyAcademicYearToPaper = function (paper) {
  const ay = window.getAcademicYear();
  const ys = window.getYearSemester();
  if (!paper || (!ay && !ys)) return;
  paper.academic_year = ay;
  paper.year_semester = ys;
  if (paper.college_profile) {
    paper.college_profile = Object.assign({}, paper.college_profile);
    if (ys) {
      paper.college_profile.year_semester = ay ? `${ys} (A.Y.: ${ay})` : ys;
    } else if (ay) {
      paper.college_profile.year_semester = window.withAcademicYear(paper.college_profile.year_semester, ay, true);
    }
    if (ay && paper.college_profile.exam_title) {
      paper.college_profile.exam_title = window.withAcademicYear(paper.college_profile.exam_title, ay, false);
    }
  }
  if (ay && paper.exam_title) paper.exam_title = window.withAcademicYear(paper.exam_title, ay, false);
  // Custom / imported college templates draw their header from plain text lines: stamp those too
  if (paper.template_style && Array.isArray(paper.template_style.header_lines) && paper.template_style.header_lines.length) {
    const ts = Object.assign({}, paper.template_style);
    ts.header_lines = ts.header_lines.map((h) => Object.assign({}, h));
    const ysText = ys ? (ay ? `${ys} (A.Y.: ${ay})` : ys) : "";
    let foundYs = false;
    ts.header_lines.forEach((h) => {
      if (h.role === "year_semester") {
        foundYs = true;
        if (ysText) h.text = ysText;
        else if (ay) h.text = window.withAcademicYear(h.text, ay, true);
      } else if (h.role === "exam_title" && ay) {
        h.text = window.withAcademicYear(h.text, ay, false);
      }
    });
    if (!foundYs && (ysText || ay)) {
      ts.header_lines.push({ text: ysText || `A.Y.: ${ay}`, role: "year_semester", size: 10.5, bold: false, italic: false,
        uppercase: false, align: "center", color: null });
    }
    paper.template_style = ts;
  }
  paper.custom_layout = Object.assign({}, paper.custom_layout || {}, {
    academic_session: [ys, ay ? `Academic Year ${ay}` : ""].filter(Boolean).join(" | ")
  });
};

function initAcademicYearAndCourseFields() {
  const ayEl = document.getElementById("academic-year");
  const ysEl = document.getElementById("year-semester");
  if (ayEl) {
    if (!ayEl.value.trim()) ayEl.value = window.defaultAcademicYear();
    window.syncAcademicYear();
    const onHeaderChange = () => {
      window.syncAcademicYear();
      const paper = window.AppState.currentPaper;
      if (paper) {
        window.applyAcademicYearToPaper(paper);
        if (window.GeneratorModule && window.GeneratorModule.renderPaper) window.GeneratorModule.renderPaper(paper);
      } else if (typeof applyLayoutToExamSheet === "function") {
        applyLayoutToExamSheet();
      }
    };
    ayEl.addEventListener("input", onHeaderChange);
    if (ysEl) ysEl.addEventListener("input", onHeaderChange);
  }

  // Course code / title typed after a paper exists must reach the paper, its preview, print and export
  const refreshCourse = () => {
    const paper = window.AppState.currentPaper;
    if (!paper) return;
    const code = (document.getElementById("course-code")?.value || "").trim();
    const name = (document.getElementById("course-name")?.value || "").trim();
    if (code) paper.course_code = code;
    if (name) paper.course_name = name;
    const courseEl = document.getElementById("exam-render-course");
    if (courseEl) courseEl.innerText = `${paper.course_code}: ${paper.course_name}`;
  };
  ["course-code", "course-name"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", refreshCourse);
  });
}
