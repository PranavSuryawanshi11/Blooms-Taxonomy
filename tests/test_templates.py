"""College template import: extraction, per-user storage, generation and Word export."""

import io
import os
import uuid

import pytest
from PIL import Image, ImageDraw

needs_db = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL (PostgreSQL) not configured")


def _logo_png(color):
    im = Image.new("RGB", (240, 240), "white")
    d = ImageDraw.Draw(im)
    d.ellipse((8, 8, 232, 232), outline=color, width=12)
    d.ellipse((60, 60, 180, 180), fill=color)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    buf.seek(0)
    return buf


def _college_docx(with_logo=True):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH as A
    from docx.shared import Inches, Pt
    d = Document()

    def para(host, text, size, bold=False, italic=False, al=A.CENTER, first=False):
        x = host.paragraphs[0] if first else host.add_paragraph()
        r = x.add_run(text); r.font.size = Pt(size); r.bold = bold; r.italic = italic; x.alignment = al
        return x

    if with_logo:
        t = d.add_table(rows=1, cols=3)
        t.rows[0].cells[0].paragraphs[0].add_run().add_picture(_logo_png((20, 60, 160)), width=Inches(0.9))
        t.rows[0].cells[2].paragraphs[0].add_run().add_picture(_logo_png((160, 30, 30)), width=Inches(0.9))
        mid = t.rows[0].cells[1]
        para(mid, "Shirpur Education Society's", 11, True, first=True)
        para(mid, "R. C. PATEL INSTITUTE OF TECHNOLOGY, SHIRPUR", 15, True)
        para(mid, "An Autonomous Institute", 10, False, True)
    else:
        para(d, "R. C. PATEL INSTITUTE OF TECHNOLOGY, SHIRPUR", 15, True)
    para(d, "END SEMESTER EXAMINATION EVEN SEM-IV", 12.5, True)
    para(d, "Year: II / Semester IV (Exam Year: 2024-2025)", 10)
    L = A.LEFT
    para(d, "Course Code: CS601        Course Name: Machine Learning        Roll No: ________", 10.5, al=L)
    para(d, "Time: 02:00 Hrs.        Max Marks: 50", 10.5, al=L)
    para(d, "Instructions:", 10.5, True, al=L)
    para(d, "1. Answer to each new question to be started on a fresh page.", 10, al=L)
    para(d, "2. Figures to the right indicate full marks.", 10, al=L)
    for line in ["Q.1 a) Define overfitting and underfitting in machine learning. [5]",
                 "b) Explain the bias-variance tradeoff with a neat diagram. [5]",
                 "c) Differentiate between pre-pruning and post-pruning of a decision tree. [5]",
                 "Q.2 a) Apply K-means clustering on the given points for two iterations. [10]",
                 "b) Describe single link and complete link hierarchical clustering. [5]",
                 "OR",
                 "b) Calculate precision and recall for the given confusion matrix. [5]",
                 "Q.3 Derive the optimization function for linear Support Vector Machine. [15]",
                 "OR",
                 "Design an ensemble model using bagging and boosting for fraud detection. [15]"]:
        para(d, line, 10.5, al=L)
    buf = io.BytesIO(); d.save(buf)
    return buf.getvalue()


def test_extractor_copies_header_logos_meta_structure():
    from core.template_extractor import extract_template
    r = extract_template("old.docx", _college_docx())
    t = r["template"]
    roles = {h["role"]: h for h in t["header_lines"]}
    assert roles["society"]["bold"] and roles["society"]["size"] == 11
    assert roles["college"]["size"] == 15 and roles["college"]["bold"] and "PATEL" in roles["college"]["text"]
    assert roles["tagline"]["italic"]
    assert "exam_title" in roles and "year_semester" in roles
    assert sorted(l["position"] for l in t["logos"]) == ["left", "right"]
    assert all(l["data_url"].startswith("data:image/") for l in t["logos"])
    assert [[c["key"] for c in row] for row in t["meta_layout"]] == [["code", "course", "roll"], ["duration", "marks"]]
    assert t["show_roll_box"] and t["duration"].startswith("02:00") and t["total_marks"] == 50
    assert len(t["instructions"]) == 2
    assert t["numbering_style"] == "sub" and t["numbering_format"] == {"prefix": "Q.", "sub": "close"}
    s1, s2, s3 = t["sections"]
    assert s1["question_marks"] == [5, 5, 5] and not any(s1["question_choices"])
    assert s2["question_marks"] == [10, 5] and s2["question_choices"] == [False, True]
    assert s3["question_marks"] == [15] and s3["question_choices"] == [True]


def test_extractor_heading_style_paper_and_bad_files():
    from core.template_extractor import extract_template
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH as A
    d = Document()
    for text, al in [("D. J. SANGHVI COLLEGE OF ENGINEERING", A.CENTER), ("Continuous Assessment Test - I", A.CENTER),
                     ("Course Code: CE401    Course Name: Operating Systems", A.LEFT), ("Duration: 1 Hour    Max. Marks: 30", A.LEFT),
                     ("Part A: Answer all questions (5 x 2 = 10 Marks)", A.LEFT),
                     ("1. Define process and thread. [2]", A.LEFT), ("2. List the states of a process. [2]", A.LEFT),
                     ("Part B: Answer any two (2 x 10 = 20 Marks)", A.LEFT),
                     ("3. Explain Round Robin scheduling with an example. [10]", A.LEFT),
                     ("4. Compare paging and segmentation with neat diagrams. [10]", A.LEFT)]:
        d.add_paragraph(text).alignment = al
    buf = io.BytesIO(); d.save(buf)
    t = extract_template("p.docx", buf.getvalue())["template"]
    assert t["numbering_style"] == "sequential"
    assert [s["name"] for s in t["sections"]] == ["Part A", "Part B"]
    assert t["sections"][0]["question_marks"] == [2, 2] and t["sections"][1]["question_marks"] == [10, 10]
    with pytest.raises(ValueError):
        extract_template("x.txt", b"hello")
    with pytest.raises(ValueError):
        extract_template("broken.pdf", b"%PDF-1.4 not really")


def test_schema_sanitizer_rejects_bad_logo_and_clamps_values():
    from core.template_schema import sanitize_template
    raw = {"name": "<b>X</b>", "header_lines": [{"text": "College", "size": 500, "align": "weird"}],
           "logos": [{"data_url": "data:image/svg+xml;base64,AAAA", "position": "left"}],
           "sections": [{"name": "Q1", "question_count": 3, "question_marks": [5, 5, 5], "question_choices": [True]}]}
    t = sanitize_template(raw)
    assert t["logos"] == [] and t["header_lines"][0]["size"] == 40 and t["header_lines"][0]["align"] == "center"
    assert t["sections"][0]["question_choices"] == [True, False, False] and t["college_profile"]["society"] == ""
    with pytest.raises(ValueError):
        sanitize_template({"sections": []})


@needs_db
def test_import_save_isolation_generate_and_export(client):
    from docx import Document

    def register(prefix):
        r = client.post("/api/auth/register", json={"username": f"{prefix}_{uuid.uuid4().hex[:6]}", "display_name": prefix,
                                                     "department": "CSE", "password": "Str0ngPass!42"}).get_json()
        return {"Authorization": f"Bearer {r['token']}"}

    a, b = register("tmpl_a"), register("tmpl_b")
    imp = client.post("/api/templates/import", headers=a, content_type="multipart/form-data",
                      data={"file": (io.BytesIO(_college_docx()), "old.docx")}).get_json()
    assert imp["success"] and imp["stats"]["logos"] == 2
    saved = client.post("/api/templates", headers=a, json={"template": imp["template"]}).get_json()
    tid = saved["template_id"]
    assert saved["success"] and tid.startswith("custom_")

    assert tid in client.get("/api/blueprint/presets", headers=a).get_json()["exam_templates"]
    assert tid not in client.get("/api/blueprint/presets", headers=b).get_json()["exam_templates"]
    assert client.delete(f"/api/templates/{tid}", headers=b).get_json()["deleted"] is False

    syl = client.get("/api/syllabus/samples").get_json()["samples"][0]
    gen = client.post("/api/paper/generate", headers=a, json={"syllabus": syl, "exam_config": {"template_id": tid}}).get_json()
    assert gen["success"], gen
    paper = gen["paper"]
    labels = [q["display_num"] for q in paper["all_questions"]]
    assert labels[:3] == ["Q.1 a)", "Q.1 b)", "Q.1 c)"] and "Q.2 b) (OR)" in labels
    assert len(paper["template_style"]["logos"]) == 2
    # the sample paper declares 50 marks but its questions add up to 45: the app reports it instead of hiding it
    assert paper["marks_check"] == {"expected": 50, "actual": 45, "matches": False}

    ex = client.post("/api/paper/export-doc", headers=a, json={"paper": paper})
    assert ex.status_code == 200
    doc = Document(io.BytesIO(ex.data))
    assert len(doc.inline_shapes) == 2                                   # both logos embedded as pictures
    text = "\n".join(p.text for p in doc.paragraphs) + "\n".join(c.text for t in doc.tables for r in t.rows for c in r.cells)
    assert "R. C. PATEL INSTITUTE" in text and "Course Code" in text

    guest = client.post("/api/auth/guest", json={"device_id": "dev-" + uuid.uuid4().hex}).get_json()
    g = client.post("/api/templates/import", headers={"Authorization": f"Bearer {guest['token']}"}, content_type="multipart/form-data",
                    data={"file": (io.BytesIO(_college_docx()), "old.docx")})
    assert g.status_code == 403
    assert client.delete(f"/api/templates/{tid}", headers=a).get_json()["deleted"] is True
