/**
 * BloomCraft AI - Paper Export & Document Service
 * Handles print formatting, Word document generation, JSON archiving, and project ZIP packaging.
 * Zero emojis - 100% professional SVG icons.
 */

window.ExportModule = {
  init() {
    this.bindEvents();
  },

  bindEvents() {
    // Print / Save to PDF Button
    const printBtn = document.getElementById("btn-print-paper");
    if (printBtn) {
      printBtn.addEventListener("click", () => this.printPaper());
    }

    // Export Word (.doc) Button
    const wordBtn = document.getElementById("btn-export-word");
    if (wordBtn) {
      wordBtn.addEventListener("click", () => this.exportWordDoc());
    }

    // Export JSON Button
    const jsonBtn = document.getElementById("btn-export-json");
    if (jsonBtn) {
      jsonBtn.addEventListener("click", () => this.exportJson());
    }
  },

  // Turn an SVG string into a PNG data URL (Word cannot display inline SVG)
  svgToPng(svgStr) {
    return new Promise((resolve) => {
      try {
        const vb = svgStr.match(/viewBox="[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)"/);
        const w = vb ? parseFloat(vb[1]) : 600;
        const h = vb ? parseFloat(vb[2]) : 400;
        // drop the responsive style and give the root fixed pixel size so the image renders at its true size
        const clean = svgStr.replace(/<svg\b[^>]*>/, (tag) => {
          let t = tag.replace(/\sstyle="[^"]*"/, "").replace(/\s(width|height)="[^"]*"/g, "");
          if (!/xmlns=/.test(t)) t = t.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"');
          return t.replace("<svg", `<svg width="${w}" height="${h}"`);
        });
        const img = new Image();
        img.onload = () => {
          const scale = 2;
          const canvas = document.createElement("canvas");
          canvas.width = Math.round(w * scale);
          canvas.height = Math.round(h * scale);
          const ctx = canvas.getContext("2d");
          ctx.fillStyle = "#ffffff";
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          resolve({ png: canvas.toDataURL("image/png"), w, h });
        };
        img.onerror = () => resolve(null);
        img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(clean);
      } catch (e) {
        resolve(null);
      }
    });
  },

  // Print ONLY the question paper: no tool name, Bloom level, CO, AICTE verb, matrices or buttons
  printPaper() {
    const paper = window.AppState.currentPaper;
    const sheet = document.getElementById("exam-sheet-container");
    if (!paper || !sheet) {
      showToast("Please synthesize a question paper first.", "error");
      return;
    }

    const layout = window.AppState.customLayout || {};
    const showMarks = layout.show_marks_tags !== false;
    const clone = sheet.cloneNode(true);

    // remove everything that is not part of the paper itself
    clone.querySelectorAll(
      "#exam-co-covered-box, #exam-co-matrix-target, .figure-header, .figure-actions, .question-hover-actions, .no-print, button"
    ).forEach((el) => el.remove());

    // keep only the marks from each question's meta group, drop Bloom / AICTE / CO badges
    clone.querySelectorAll(".question-item").forEach((item) => {
      const marksEl = item.querySelector(".marks-badge");
      const marksText = marksEl ? marksEl.textContent.trim() : "";
      const meta = item.querySelector(".question-meta-group");
      if (meta) meta.remove();
      if (showMarks && marksText) {
        const m = document.createElement("div");
        m.className = "print-marks";
        m.textContent = marksText.replace(/M\]$/, "]");
        const main = item.querySelector(".question-main");
        if (main) main.appendChild(m);
      }
    });
    clone.querySelectorAll(".section-banner-marks").forEach((el) => {
      el.textContent = el.textContent.replace(/\s+/g, " ").trim();
    });
    clone.querySelectorAll("[id]").forEach((el) => el.removeAttribute("id"));

    const title = [paper.course_code, paper.exam_title || "Question Paper"].filter(Boolean).join(" - ");
    const twoCol = clone.classList.contains("layout-2col");
    const sans = clone.classList.contains("font-sans");

    const css = `
      @page { size: A4 portrait; margin: 14mm 14mm; }
      * { box-sizing: border-box; }
      html, body { margin: 0; padding: 0; background: #fff; color: #000; }
      body { font-family: ${sans ? "Arial, Helvetica, sans-serif" : "'Times New Roman', Times, serif"}; font-size: 11pt; line-height: 1.4; }
      .exam-header { text-align: center; border-bottom: 1.5pt solid #000; padding-bottom: 6pt; margin-bottom: 8pt; }
      .exam-inst-name { font-size: 14pt; font-weight: bold; text-transform: uppercase; }
      .exam-dept-name, .exam-title-name { font-size: 11.5pt; font-weight: bold; margin-top: 2pt; }
      .exam-title-name { text-transform: uppercase; }
      .exam-session-name { font-size: 10pt; margin-top: 2pt; }
      .exam-meta-grid { display: grid; grid-template-columns: 1fr auto; gap: 4pt 12pt; font-size: 10.5pt; border-bottom: 1pt solid #000; padding-bottom: 6pt; margin-bottom: 8pt; }
      .roll-box-cells { display: inline-flex; vertical-align: middle; }
      .roll-cell { display: inline-block; width: 15pt; height: 15pt; border: 1pt solid #000; margin-left: -1pt; }
      .roll-line { display: inline-block; width: 120pt; border-bottom: 1pt solid #000; }
      .exam-instructions-box { font-size: 10pt; font-style: italic; border: 0.75pt dashed #444; padding: 4pt 7pt; margin-bottom: 8pt; }
      .section-banner { border-left: 3pt solid #000; background: #f1f1f1; padding: 3pt 7pt; margin: 10pt 0 5pt; font-weight: bold; break-after: avoid; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .section-banner-title { font-size: 11pt; text-transform: uppercase; }
      .section-banner-marks { font-size: 9.5pt; font-weight: normal; font-style: italic; }
      .question-item { padding: 4pt 0; break-inside: avoid; }
      .question-main { display: flex; gap: 8pt; align-items: flex-start; }
      .question-num { font-weight: bold; min-width: 26pt; }
      .question-text-content { flex: 1; text-align: justify; }
      .print-marks { font-weight: bold; white-space: nowrap; padding-left: 8pt; }
      .question-figure-box { margin: 5pt auto 2pt; text-align: center; break-inside: avoid; }
      .figure-svg-wrapper svg { display: block; margin: 0 auto !important; width: auto !important; max-width: 82mm !important; max-height: 80mm !important; height: auto !important; border: 0 !important; border-radius: 0 !important; }
      .figure-caption { font-size: 9pt; font-style: italic; margin-top: 2pt; }
      .or-divider-banner { text-align: center; font-weight: bold; font-size: 10pt; margin: 3pt 0; }
      ${twoCol ? "#paper-render-target, .paper-render-target { column-count: 2; column-gap: 18pt; column-rule: 0.5pt solid #999; }" : ""}
    `;
    // the tool-name footer and "END" line stay generic; drop nothing else
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title.replace(/</g, "&lt;")}</title><style>${css}</style></head><body>${clone.innerHTML.replace(/<!--[\s\S]*?-->/g, "")}</body></html>`;

    const frame = document.createElement("iframe");
    frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden;";
    document.body.appendChild(frame);
    const doc = frame.contentWindow.document;
    doc.open(); doc.write(html); doc.close();

    const oldTitle = document.title;
    document.title = title;                       // browsers print the page title in the header
    const cleanup = () => { document.title = oldTitle; setTimeout(() => frame.remove(), 500); };
    frame.contentWindow.addEventListener("afterprint", cleanup);
    setTimeout(() => {
      frame.contentWindow.focus();
      frame.contentWindow.print();
      setTimeout(cleanup, 60000);
    }, 350);
  },

  async exportWordDoc() {
    const paper = window.AppState.currentPaper;
    if (!paper) {
      showToast("Please synthesize a question paper first.", "error");
      return;
    }

    // Work on a copy so the on-screen paper is not modified
    const payloadPaper = JSON.parse(JSON.stringify(paper));
    payloadPaper.custom_layout = window.AppState.customLayout;

    const btn = document.getElementById("btn-export-word");
    const origHtml = btn ? btn.innerHTML : "";
    if (btn) btn.innerHTML = "<span>Generating Word Document...</span>";

    try {
      // Rasterize every diagram so it appears inside the Word file next to its question
      const allQs = [];
      (payloadPaper.sections || []).forEach((sec) => (sec.questions || []).forEach((q) => {
        allQs.push(q);
        if (q.or_question) allQs.push(q.or_question);
      }));
      for (const q of allQs) {
        if (q.figure && q.figure.svg) {
          const r = await this.svgToPng(q.figure.svg);
          if (r) { q.figure_png = r.png; q.figure_png_w = r.w; q.figure_png_h = r.h; }
        }
      }

      const headers = { "Content-Type": "application/json" };
      if (window.AuthModule && window.AuthModule.authToken) {
        headers["Authorization"] = `Bearer ${window.AuthModule.authToken}`;
      }
      const res = await fetch(`${API_BASE}/api/paper/export-doc`, {
        method: "POST",
        headers,
        body: JSON.stringify({ paper: payloadPaper })
      });

      if (!res.ok) throw new Error("Server failed to generate Word document");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      const cleanCode = (paper.course_code || "EXAM").replace(/[^a-zA-Z0-9_-]/g, "_");
      a.download = `${cleanCode}_Question_Paper.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();

      showToast("Word document generated and downloaded successfully.", "success");
    } catch (err) {
      console.error(err);
      showToast("Error downloading Word document.", "error");
    } finally {
      if (btn) btn.innerHTML = origHtml;
    }
  },

  exportJson() {
    const paper = window.AppState.currentPaper;
    if (!paper) {
      showToast("Please synthesize a question paper first.", "error");
      return;
    }

    paper.custom_layout = window.AppState.customLayout;

    const jsonString = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(paper, null, 2));
    const a = document.createElement("a");
    a.setAttribute("href", jsonString);
    const cleanCode = (paper.course_code || "EXAM").replace(/[^a-zA-Z0-9_-]/g, "_");
    a.setAttribute("download", `${cleanCode}_Question_Paper_Archive.json`);
    document.body.appendChild(a);
    a.click();
    a.remove();

    showToast("Paper JSON archive downloaded successfully.", "success");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  window.ExportModule.init();
});
