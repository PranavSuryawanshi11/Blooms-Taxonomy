# REST API Technical Specifications

The BloomCraft AI backend exposes clean REST endpoints on `http://127.0.0.1:5000`.

---

## 🔐 1. Faculty Authentication & Session Endpoints

### Register Faculty Profile
- **Endpoint**: `POST /api/auth/register`
- **Request Body**:
  ```json
  {
    "username": "prof.alan",
    "display_name": "Prof. Alan Turing",
    "department": "Computer Science & Engineering",
    "password": "strongPassword123"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "success": true,
    "user": {
      "user_id": "usr_9b38cf1a",
      "username": "prof.alan",
      "display_name": "Prof. Alan Turing",
      "department": "Computer Science & Engineering",
      "role": "Faculty Member"
    }
  }
  ```

### Faculty Login
- **Endpoint**: `POST /api/auth/login`
- **Request Body**:
  ```json
  {
    "username": "prof.alan",
    "password": "strongPassword123"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "success": true,
    "token": "tok_4b281f9a2e...",
    "user": { ... }
  }
  ```

### Current Session User
- **Endpoint**: `GET /api/auth/me`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `200 OK` returns authenticated faculty profile.

### Logout
- **Endpoint**: `POST /api/auth/logout`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: Revokes session token in SQLite database.

---

## 📚 2. Syllabus Ingestion & Processing

### Extract and Parse Syllabus
- **Endpoint**: `POST /api/syllabus/parse`
- **Form Data** (multipart) or **JSON**:
  - `file`: PDF file upload.
  - `raw_text`: Plaintext syllabus string.
  - `course_code`: e.g. `"CS505"`
  - `course_name`: e.g. `"Machine Learning"`
- **Response**:
  ```json
  {
    "success": true,
    "parsed": {
      "course_code": "CS505",
      "course_name": "Machine Learning",
      "total_units": 5,
      "total_topics": 28,
      "units": [
        {
          "unit_num": 1,
          "title": "Supervised Learning",
          "topics": ["Linear Regression", "Logistic Regression", "Regularization"],
          "co": "CO1"
        }
      ],
      "course_outcomes": [
        {"id": "CO1", "description": "Formulate regression and classification models"}
      ]
    }
  }
  ```

### Load Preloaded Reference Syllabi
- **Endpoint**: `GET /api/syllabus/samples`
- **Response**: List of preloaded curriculum datasets for fast demonstration.

---

## 🛠️ 3. Examination Blueprint & Paper Generation

### Build Blueprint Matrix
- **Endpoint**: `POST /api/blueprint/build`
- **Request Body**:
  ```json
  {
    "syllabus": { ... },
    "exam_config": {
      "template_id": "rcpit_sem_65",
      "total_marks": 65,
      "sections": [ ... ]
    },
    "target_distribution": {
      "L1": 20, "L2": 25, "L3": 25, "L4": 15, "L5": 10, "L6": 5
    }
  }
  ```
- **Response**: Compiled blueprint with slots, CO mappings, and target cognitive indices.

### Generate Examination Paper
- **Endpoint**: `POST /api/paper/generate`
- **Headers**: `Authorization: Bearer <token>` (Optional for private archive)
- **Request Body**:
  ```json
  {
    "syllabus": { ... },
    "blueprint_config": {
      "template_id": "rcpit_sem_65",
      "total_marks": 65
    },
    "target_distribution": { ... },
    "generation_source": "engine"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "paper": {
      "paper_id": "pap_b90b3c0fcc",
      "exam_title": "END SEMESTER EXAMINATION EVEN SEM-IV",
      "total_marks": 65,
      "sections": [ ... ],
      "all_questions": [ ... ],
      "co_fulfillment_matrix": [ ... ],
      "co_summary": { ... }
    }
  }
  ```

### Regenerate Individual Question Slot
- **Endpoint**: `POST /api/paper/regenerate-question`
- **Request Body**:
  ```json
  {
    "slot": {
      "slot_id": "q_5",
      "marks": 5,
      "bloom_level": "L3",
      "topic": "Gradient Descent",
      "co": "CO2"
    },
    "exclude_texts": ["Previous question text..."]
  }
  ```
- **Response**: Alternative question synthesized with the exact same pedagogical constraints.

---

## 📄 4. Export & History Endpoints

### Export Microsoft Word (.docx)
- **Endpoint**: `POST /api/export/word`
- **Request Body**: Complete `paper` JSON object.
- **Response**: Binary `.docx` stream with headers and download filename.

### Retrieve Past Papers History
- **Endpoint**: `GET /api/history`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: List of saved papers without heavy payloads (`O(1)` query from SQLite).

### Delete Past Paper
- **Endpoint**: `DELETE /api/history/<paper_id>`
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `{"deleted": true}`

