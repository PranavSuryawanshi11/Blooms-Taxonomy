/**
 * BloomCraft AI - Syllabus Ingestion & Document Viewer Controller
 * Handles PDF extraction, curriculum parsing, document view tabs, and stats.
 * Zero emojis - 100% professional SVG icons.
 */

window.SyllabusModule = {
  init() {
    this.bindEvents();
    this.bindViewTabs();
  },

  bindEvents() {
    // Parse Text button
    const parseBtn = document.getElementById("btn-parse-text");
    if (parseBtn) {
      parseBtn.addEventListener("click", () => this.parseRawText());
    }

    // File input & Drag drop
    const fileInput = document.getElementById("syllabus-file-input");
    const dropzone = document.getElementById("syllabus-dropzone");

    if (dropzone && fileInput) {
      dropzone.addEventListener("click", () => fileInput.click());

      dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });

      dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
      });

      dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          this.uploadFile(e.dataTransfer.files[0]);
        }
      });

      fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
          this.uploadFile(e.target.files[0]);
        }
      });
    }

    // Proceed to Blueprint button
    const proceedBtn = document.getElementById("btn-proceed-blueprint");
    if (proceedBtn) {
      proceedBtn.addEventListener("click", () => {
        if (!window.AppState.currentSyllabus) {
          showToast("Please parse or load a curriculum document first.", "error");
          return;
        }
        window.switchTab("blueprint");
      });
    }

    // Copy Extracted Text button
    const copyBtn = document.getElementById("btn-copy-extracted-text");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => this.copyExtractedText());
    }
  },

  bindViewTabs() {
    const btnModules = document.getElementById("btn-view-modules");
    const btnDoc = document.getElementById("btn-view-extracted-doc");
    const secModules = document.getElementById("view-section-modules");
    const secDoc = document.getElementById("view-section-extracted-doc");

    if (btnModules && btnDoc && secModules && secDoc) {
      btnModules.addEventListener("click", () => {
        btnModules.classList.add("active");
        btnDoc.classList.remove("active");
        secModules.style.display = "block";
        secDoc.style.display = "none";
      });

      btnDoc.addEventListener("click", () => {
        btnDoc.classList.add("active");
        btnModules.classList.remove("active");
        secModules.style.display = "none";
        secDoc.style.display = "block";
      });
    }
  },

  renderSamples(samples) {
    const container = document.getElementById("sample-chips-container");
    if (!container) return;

    container.innerHTML = "";
    samples.forEach(s => {
      const chip = document.createElement("button");
      chip.className = "chip";
      chip.innerHTML = `<strong>${s.code}</strong> ${s.name}`;
      chip.addEventListener("click", () => {
        document.querySelectorAll("#sample-chips-container .chip").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        this.loadSampleSyllabus(s, true);
      });
      container.appendChild(chip);
    });

    // Auto-load first sample (DBMS) by default for immediate preview without toast notification
    if (samples.length > 0 && !window.AppState.currentSyllabus) {
      container.children[0].classList.add("active");
      this.loadSampleSyllabus(samples[0], false);
    }
  },

  loadSampleSyllabus(sample, showNotification = false) {
    window.AppState.currentSyllabus = JSON.parse(JSON.stringify(sample));
    
    // Fill course info fields
    document.getElementById("course-code").value = sample.code;
    document.getElementById("course-name").value = sample.name;
    document.getElementById("course-dept").value = sample.department || "Computer Science & Engineering";

    // Format syllabus document text if not present
    let docText = sample.extracted_text;
    if (!docText) {
      docText = this.buildCurriculumDocumentString(sample);
    }
    window.AppState.extractedSyllabusText = docText;
    sample.extracted_text = docText;

    this.renderParsedSyllabus(sample);
    this.renderExtractedDocument(docText);

    // Only show toast when explicitly requested by user action and faculty is logged in
    if (showNotification && (window.AppState?.currentUser || window.AuthModule?.currentUser)) {
      showToast(`Loaded ${sample.code}: ${sample.name} curriculum.`, "success");
    }
  },

  async parseRawText() {
    const text = document.getElementById("syllabus-text-input").value.trim();
    if (!text || text.length < 20) {
      showToast("Please enter detailed syllabus text with unit and topic descriptions.", "error");
      return;
    }

    const code = document.getElementById("course-code").value.trim() || "CS501";
    const name = document.getElementById("course-name").value.trim() || "Course Curriculum";

    const btn = document.getElementById("btn-parse-text");
    const origHtml = btn.innerHTML;
    btn.innerHTML = "<span>Parsing Curriculum Structure...</span>";
    btn.disabled = true;

    try {
      const res = await fetch(`${API_BASE}/api/syllabus/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: text, course_code: code, course_name: name })
      });
      const data = await res.json();
      if (data.success) {
        window.AppState.currentSyllabus = data.syllabus;
        window.AppState.extractedSyllabusText = data.syllabus.extracted_text || text;
        this.renderParsedSyllabus(data.syllabus);
        this.renderExtractedDocument(window.AppState.extractedSyllabusText);
        showToast(`Parsed ${data.syllabus.total_units} modules and ${data.syllabus.total_topics} topics successfully.`, "success");
      } else {
        showToast(data.error || "Failed to parse syllabus structure.", "error");
      }
    } catch (err) {
      console.error(err);
      showToast("Network error communicating with syllabus parser.", "error");
    } finally {
      btn.innerHTML = origHtml;
      btn.disabled = false;
    }
  },

  async uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("course_code", document.getElementById("course-code").value.trim() || "CS501");
    formData.append("course_name", document.getElementById("course-name").value.trim() || file.name.replace(/\.[^/.]+$/, ""));

    const dropText = document.querySelector(".dropzone-text");
    const origText = dropText ? dropText.innerText : "";
    if (dropText) dropText.innerText = `Extracting curriculum from ${file.name}...`;

    try {
      const res = await fetch(`${API_BASE}/api/syllabus/parse`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        window.AppState.currentSyllabus = data.syllabus;
        window.AppState.extractedSyllabusText = data.syllabus.extracted_text || "";
        
        document.getElementById("course-code").value = data.syllabus.code;
        document.getElementById("course-name").value = data.syllabus.name;
        
        this.renderParsedSyllabus(data.syllabus);
        this.renderExtractedDocument(window.AppState.extractedSyllabusText);

        // Switch to extracted document view to immediately show extracted PDF content
        const btnDoc = document.getElementById("btn-view-extracted-doc");
        if (btnDoc) btnDoc.click();

        showToast(`Extracted ${data.syllabus.total_units} units directly from ${file.name}!`, "success");
      } else {
        showToast(data.error || "Failed to extract syllabus from file.", "error");
      }
    } catch (err) {
      console.error(err);
      showToast("Error processing uploaded document.", "error");
    } finally {
      if (dropText) dropText.innerText = origText;
    }
  },

  renderParsedSyllabus(syllabus) {
    const previewContainer = document.getElementById("parsed-syllabus-container");
    const emptyState = document.getElementById("syllabus-empty-state");
    const proceedBtn = document.getElementById("btn-proceed-blueprint");

    if (!previewContainer) return;

    if (emptyState) emptyState.style.display = "none";
    previewContainer.style.display = "block";
    if (proceedBtn) proceedBtn.style.display = "inline-flex";

    // Summary metrics
    document.getElementById("stat-total-units").innerText = syllabus.total_units || syllabus.units.length;
    document.getElementById("stat-total-topics").innerText = syllabus.total_topics || 
      syllabus.units.reduce((acc, u) => acc + (u.topics ? u.topics.length : 0), 0);
    document.getElementById("stat-total-cos").innerText = (syllabus.course_outcomes || []).length || syllabus.units.length;

    // Render Unit cards
    const unitsList = document.getElementById("units-list");
    unitsList.innerHTML = "";

    syllabus.units.forEach(u => {
      const card = document.createElement("div");
      card.className = "unit-card";

      const topicsHtml = (u.topics || []).map(t => `<span class="topic-tag">${t}</span>`).join("");

      card.innerHTML = `
        <div class="unit-card-header">
          <div class="unit-info">
            <span class="unit-pill">Unit ${u.unit_num}</span>
            <span class="co-badge">${u.co || `CO${u.unit_num}`}</span>
            <span class="unit-title-text">${u.title}</span>
          </div>
          <span style="font-size:12px; color:var(--text-muted); font-family:var(--font-mono);">${(u.topics || []).length} topics</span>
        </div>
        <div class="unit-topics-body">
          ${topicsHtml}
        </div>
      `;
      unitsList.appendChild(card);
    });
  },

  renderExtractedDocument(rawText) {
    const docDisplay = document.getElementById("extracted-syllabus-text-display");
    const linesStat = document.getElementById("doc-stat-lines");
    const charsStat = document.getElementById("doc-stat-chars");

    if (!docDisplay) return;

    const clean = (rawText || "").trim();
    docDisplay.textContent = clean || "No raw text extracted.";

    const lines = clean ? clean.split("\n").length : 0;
    const chars = clean.length;

    if (linesStat) linesStat.innerText = `${lines} lines`;
    if (charsStat) charsStat.innerText = `${chars.toLocaleString()} characters`;
  },

  copyExtractedText() {
    const text = window.AppState.extractedSyllabusText;
    if (!text) {
      showToast("No extracted text to copy.", "error");
      return;
    }

    navigator.clipboard.writeText(text).then(() => {
      showToast("Extracted syllabus text copied to clipboard.", "success");
    }).catch(() => {
      showToast("Unable to copy to clipboard.", "error");
    });
  },

  buildCurriculumDocumentString(syllabus) {
    const parts = [
      `COURSE CODE: ${syllabus.code}`,
      `COURSE TITLE: ${syllabus.name}`,
      `DEPARTMENT: ${syllabus.department || "Computer Science & Engineering"}`,
      `CREDITS: ${syllabus.credits || 4}`,
      `\nCOURSE OUTCOMES:`
    ];

    (syllabus.course_outcomes || []).forEach(co => {
      parts.push(`  [${co.id}] ${co.description}`);
    });

    parts.push(`\nCURRICULUM MODULES & TOPICS:\n`);

    (syllabus.units || []).forEach(u => {
      parts.push(`UNIT ${u.unit_num}: ${u.title} [${u.co || 'CO' + u.unit_num}]`);
      (u.topics || []).forEach(t => {
        parts.push(`  • ${t}`);
      });
      parts.push("");
    });

    return parts.join("\n");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  window.SyllabusModule.init();
});
