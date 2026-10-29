"""
Bloom's Taxonomy Question Paper Generator
Flask Application & RESTful API Server
"""

import os
import io
import json
import logging
import zipfile
from flask import Flask, request, jsonify, send_from_directory, Response, send_file

from config import BLOOM_LEVELS, BLOOM_ORDER, BLOOM_PRESETS, EXAM_TEMPLATES
from core.bloom_engine import (
    validate_bloom_distribution, 
    calculate_actual_distribution, 
    calculate_cognitive_index, 
    normalize_distribution
)
from core.syllabus_parser import parse_syllabus, extract_text_from_pdf
from core.blueprint_builder import build_blueprint
from core.question_generator import generate_paper_from_blueprint, generate_single_question
from core.figure_generator import generate_technical_diagram
from core.export_service import generate_word_document, generate_word_docx

from core.auth_history_service import (
    authenticate_user,
    register_user,
    reset_user_password,
    list_users,
    create_session,
    get_user_by_token,
    destroy_session,
    save_paper_to_history,
    get_user_history,
    get_history_paper,
    delete_history_paper
)

# Set up paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CUSTOM_TEMPLATES_FILE = os.path.join(DATA_DIR, "custom_templates.json")

def load_all_templates():
    templates = dict(EXAM_TEMPLATES)
    if os.path.exists(CUSTOM_TEMPLATES_FILE):
        try:
            with open(CUSTOM_TEMPLATES_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
                templates.update(custom)
        except Exception as e:
            logger.warning(f"Could not load custom templates: {e}")
    return templates

def save_custom_template(template_id: str, template_data: dict):
    custom = {}
    if os.path.exists(CUSTOM_TEMPLATES_FILE):
        try:
            with open(CUSTOM_TEMPLATES_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
        except Exception:
            custom = {}
    custom[template_id] = template_data
    os.makedirs(os.path.dirname(CUSTOM_TEMPLATES_FILE), exist_ok=True)
    with open(CUSTOM_TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(custom, f, indent=2)

def delete_custom_template(template_id: str):
    if os.path.exists(CUSTOM_TEMPLATES_FILE):
        try:
            with open(CUSTOM_TEMPLATES_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
            if template_id in custom:
                del custom[template_id]
                with open(CUSTOM_TEMPLATES_FILE, "w", encoding="utf-8") as f:
                    json.dump(custom, f, indent=2)
                return True
        except Exception:
            pass
    return False

QUESTION_SETS_FILE = os.path.join(DATA_DIR, "user_question_sets.json")

def get_default_starter_sets():
    """Default starter sets modeled directly on the attached college question papers."""
    return [
        {
            "set_id": "set_1",
            "set_name": "Set 1 - Statistical Foundations & Tests",
            "questions": [
                {
                    "question_text": "Perform two-way ANOVA on the given agricultural table across treatments A, B, C, D and determine whether land blocks differ significantly.",
                    "marks": 8,
                    "bloom_level": "L3",
                    "aicte_verb": "Perform",
                    "co": "CO1",
                    "topic": "Two-Way ANOVA & Hypothesis Testing"
                },
                {
                    "question_text": "Perform Linear Discriminant Analysis (LDA) on Class 1 = {(2,3), (3,2), (3,4), (2,2)} and Class 2 = {(7,8), (8,7), (8,9), (7,7)} and classify query point (4,5).",
                    "marks": 8,
                    "bloom_level": "L3",
                    "aicte_verb": "Perform",
                    "co": "CO1",
                    "topic": "Linear Discriminant Analysis"
                },
                {
                    "question_text": "Calculate the third quartile and compute the probability that sample mean is between 110 to 120 hours for video projector bulbs with mean 100 hours and SD 75.",
                    "marks": 6,
                    "bloom_level": "L3",
                    "aicte_verb": "Calculate",
                    "co": "CO2",
                    "topic": "Normal Distribution & Quartiles"
                },
                {
                    "question_text": "Compute the 95% and 99% confidence limits of the cytokine response of mice given observation vector [0.2, 1.3, 1.4, 2.3, 4.2, 4.7, 4.7, 5.1].",
                    "marks": 4,
                    "bloom_level": "L3",
                    "aicte_verb": "Compute",
                    "co": "CO2",
                    "topic": "Confidence Intervals & Estimation"
                }
            ]
        },
        {
            "set_id": "set_2",
            "set_name": "Set 2 - Correlation, Regression & Variance",
            "questions": [
                {
                    "question_text": "Construct a 95% confidence interval for the population variance given sample variance 36 hours squared from 25 tested LED bulbs.",
                    "marks": 5,
                    "bloom_level": "L3",
                    "aicte_verb": "Construct",
                    "co": "CO2",
                    "topic": "Chi-Square Variance Estimation"
                },
                {
                    "question_text": "Calculate Spearman's Rank Correlation Coefficient with tie corrections for Math and Physics scores across the 6 students dataset.",
                    "marks": 6,
                    "bloom_level": "L3",
                    "aicte_verb": "Calculate",
                    "co": "CO3",
                    "topic": "Spearman Rank Correlation"
                },
                {
                    "question_text": "Determine the mean values, correlation coefficient, and standard deviation of Y given regression equations 7x - 5y + 14 = 0 and 28x - 25y - 35 = 0.",
                    "marks": 6,
                    "bloom_level": "L4",
                    "aicte_verb": "Determine",
                    "co": "CO3",
                    "topic": "Bivariate Linear Regression"
                },
                {
                    "question_text": "Explain the significance of ROC curve. Determine which model exhibits superior performance based on comparative AUC curves.",
                    "marks": 5,
                    "bloom_level": "L4",
                    "aicte_verb": "Explain",
                    "co": "CO4",
                    "topic": "ROC Analysis & Model Comparison"
                }
            ]
        },
        {
            "set_id": "set_3",
            "set_name": "Set 3 - Supervised Learning & Optimization",
            "questions": [
                {
                    "question_text": "Explain the concept of Inductive learning and describe any two types of Bias with real-world examples.",
                    "marks": 5,
                    "bloom_level": "L2",
                    "aicte_verb": "Explain",
                    "co": "CO1",
                    "topic": "Inductive Learning & Bias"
                },
                {
                    "question_text": "Construct the confusion matrix, calculate False Positive and False Negative metrics for the 200 email classification dataset.",
                    "marks": 5,
                    "bloom_level": "L3",
                    "aicte_verb": "Construct",
                    "co": "CO2",
                    "topic": "Classification Confusion Matrix"
                },
                {
                    "question_text": "Differentiate between Post Pruning and Pre-pruning methods of Decision Tree. Formulate how overfitting is detected.",
                    "marks": 10,
                    "bloom_level": "L4",
                    "aicte_verb": "Differentiate",
                    "co": "CO3",
                    "topic": "Decision Trees & Pruning"
                },
                {
                    "question_text": "Derive the optimization function for linear Support Vector Machine (SVM) and formulate the discriminant function.",
                    "marks": 10,
                    "bloom_level": "L5",
                    "aicte_verb": "Derive",
                    "co": "CO4",
                    "topic": "Support Vector Machines"
                }
            ]
        },
        {
            "set_id": "set_4",
            "set_name": "Set 4 - Clustering & Ensemble Methods",
            "questions": [
                {
                    "question_text": "Apply K-means algorithm on given 2D coordinates A(2,2), B(3,2), C(1,1), D(3,1), E(1.5,0.5) to partition into two clusters for two iterations.",
                    "marks": 10,
                    "bloom_level": "L3",
                    "aicte_verb": "Apply",
                    "co": "CO4",
                    "topic": "K-Means Coordinate Clustering"
                },
                {
                    "question_text": "Describe the architecture and voting mechanism of bagging in ensemble methods. Analyze the reduction in model variance.",
                    "marks": 10,
                    "bloom_level": "L4",
                    "aicte_verb": "Describe",
                    "co": "CO4",
                    "topic": "Ensemble Bagging & Random Forests"
                },
                {
                    "question_text": "Differentiate between Single Link, Complete Link, and Average Link agglomerative hierarchical clustering.",
                    "marks": 5,
                    "bloom_level": "L4",
                    "aicte_verb": "Differentiate",
                    "co": "CO4",
                    "topic": "Hierarchical Clustering"
                },
                {
                    "question_text": "Evaluate the clinical dataset with attributes [Cholesterol, Diabetic, Family History, Blood Pressure] and predict the risk label for test query point.",
                    "marks": 15,
                    "bloom_level": "L5",
                    "aicte_verb": "Evaluate",
                    "co": "CO5",
                    "topic": "Supervised Model Inference"
                }
            ]
        }
    ]

def load_user_question_sets(user_id: str = "default"):
    if os.path.exists(QUESTION_SETS_FILE):
        try:
            with open(QUESTION_SETS_FILE, "r", encoding="utf-8") as f:
                all_sets = json.load(f)
                if user_id in all_sets and all_sets[user_id]:
                    return all_sets[user_id]
                if "default" in all_sets and all_sets["default"]:
                    return all_sets["default"]
        except Exception as e:
            logger.warning(f"Error reading question sets file: {e}")
    # Return starter sets
    default_sets = get_default_starter_sets()
    save_user_question_sets(user_id, default_sets)
    return default_sets

def save_user_question_sets(user_id: str, sets_data: list):
    all_sets = {}
    if os.path.exists(QUESTION_SETS_FILE):
        try:
            with open(QUESTION_SETS_FILE, "r", encoding="utf-8") as f:
                all_sets = json.load(f)
        except Exception:
            all_sets = {}
    key = user_id or "default"
    all_sets[key] = sets_data
    os.makedirs(os.path.dirname(QUESTION_SETS_FILE), exist_ok=True)
    with open(QUESTION_SETS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_sets, f, indent=2)

app = Flask(__name__, static_folder=FRONTEND_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BloomApp")


# Enable Comprehensive CORS
@app.before_request
def handle_options_preflight():
    if request.method == "OPTIONS":
        res = Response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-User-Id, X-Auth-Token"
        return res

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-User-Id, X-Auth-Token"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# =========================================================================
# STATIC FRONTEND ROUTES
# =========================================================================
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


# =========================================================================
# REST API ENDPOINTS
# =========================================================================
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Bloom's Taxonomy Question Paper Generator",
        "version": "1.0.0",
        "supported_levels": list(BLOOM_LEVELS.keys())
    })


@app.route("/api/syllabus/samples", methods=["GET"])
def get_sample_syllabi():
    """Return preloaded university engineering course syllabi."""
    sample_file = os.path.join(DATA_DIR, "sample_syllabi.json")
    try:
        with open(sample_file, "r", encoding="utf-8") as f:
            samples = json.load(f)
        return jsonify({"success": True, "samples": samples})
    except Exception as e:
        logger.error(f"Error loading sample syllabi: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/syllabus/parse", methods=["POST"])
def parse_syllabus_endpoint():
    """
    Parses syllabus text or uploaded PDF file into structured units, topics, and COs.
    """
    try:
        raw_text = ""
        course_code = "CS501"
        course_name = "Subject Curriculum"

        # Check for multipart file upload
        if "file" in request.files:
            uploaded_file = request.files["file"]
            filename = uploaded_file.filename.lower()
            if filename.endswith(".pdf"):
                raw_text = extract_text_from_pdf(uploaded_file.read())
            else:
                raw_text = uploaded_file.read().decode("utf-8", errors="replace")
            
            course_code = request.form.get("course_code", course_code)
            course_name = request.form.get("course_name", course_name)
        elif request.is_json:
            data = request.get_json()
            raw_text = data.get("raw_text", "")
            course_code = data.get("course_code", course_code)
            course_name = data.get("course_name", course_name)
        else:
            return jsonify({"success": False, "error": "Invalid request format. Send JSON or multipart file."}), 400

        if not raw_text or len(raw_text.strip()) < 10:
            return jsonify({"success": False, "error": "Syllabus content is empty or too short."}), 400

        parsed = parse_syllabus(raw_text, course_code=course_code, course_name=course_name)
        return jsonify({"success": True, "syllabus": parsed})

    except Exception as e:
        logger.error(f"Error parsing syllabus: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/blueprint/presets", methods=["GET"])
def get_presets():
    """Return standard and custom examination templates and cognitive presets."""
    return jsonify({
        "success": True,
        "bloom_levels": BLOOM_LEVELS,
        "bloom_order": BLOOM_ORDER,
        "cognitive_presets": BLOOM_PRESETS,
        "exam_templates": load_all_templates()
    })


@app.route("/api/paper/generate", methods=["POST"])
def generate_paper():
    """
    Generates a full examination paper from syllabus, blueprint specs, Bloom distribution,
    or user-provided custom question sets (e.g. Set 1, Set 2, Set 3, Set 4).
    Differentiates per user seed, applies college templates, and persists to user history.
    """
    try:
        data = request.get_json() or {}
        syllabus = data.get("syllabus")
        if not syllabus or not syllabus.get("units"):
            return jsonify({"success": False, "error": "Valid syllabus with at least one unit is required."}), 400

        exam_config = data.get("exam_config", {})
        target_distribution = data.get("distribution", BLOOM_PRESETS["balanced"]["distribution"])
        user_sets = data.get("question_sets") or data.get("user_sets")

        # Resolve template metadata and college profile if template_id is specified
        template_id = exam_config.get("template_id") or data.get("template_id")
        all_templates = load_all_templates()
        if template_id and template_id in all_templates:
            tmpl = all_templates[template_id]
            if "sections" in tmpl and not exam_config.get("sections"):
                exam_config["sections"] = tmpl["sections"]
            if "total_marks" in tmpl and not exam_config.get("total_marks"):
                exam_config["total_marks"] = tmpl["total_marks"]
            if "college_profile" in tmpl and not exam_config.get("college_profile"):
                exam_config["college_profile"] = tmpl["college_profile"]
            if "instructions" in tmpl and not exam_config.get("instructions"):
                exam_config["instructions"] = tmpl["instructions"]
            if "duration" in tmpl and not exam_config.get("duration"):
                exam_config["duration"] = tmpl["duration"]
            if "name" in tmpl and not exam_config.get("exam_title"):
                exam_config["exam_title"] = tmpl.get("college_profile", {}).get("exam_title", tmpl["name"])
        
        # Resolve authenticated user from Bearer token for strict security & isolation
        auth_header = request.headers.get("Authorization") or request.headers.get("X-Auth-Token")
        auth_user = get_user_by_token(auth_header)
        if not auth_user:
            return jsonify({"success": False, "error": "Please sign in to generate question papers."}), 401
        user_id = auth_user["user_id"]
        user_seed = auth_user["user_id"]
        
        # Normalize distribution if needed
        normalized_dist = normalize_distribution(target_distribution)

        # Build execution blueprint with user divergence
        blueprint = build_blueprint(syllabus, exam_config, normalized_dist, user_seed=user_seed)

        # Generate questions from AICTE engine or user question sets
        api_config = data.get("api_config", {})
        paper = generate_paper_from_blueprint(
            blueprint, 
            api_config=api_config, 
            user_seed=user_seed, 
            user_sets=user_sets,
            diagram_mode=data.get("diagram_mode", "auto")
        )

        # Calculate actual cognitive distribution and depth metrics
        actual_stats = calculate_actual_distribution(paper["all_questions"])
        cognitive_index = calculate_cognitive_index(actual_stats)

        paper["analytics"] = {
            "target_distribution": normalized_dist,
            "actual_distribution": actual_stats,
            "cognitive_index": cognitive_index,
            "co_summary": paper.get("co_summary", {}),
            "source_mode": paper.get("source_mode", "AICTE-Pedagogical-Engine")
        }

        custom_layout = data.get("custom_layout", {})
        paper["custom_layout"] = custom_layout

        # Persist to user history if user_id is provided
        if user_id:
            paper_id = save_paper_to_history(user_id, paper)
            paper["paper_id"] = paper_id

        return jsonify({"success": True, "paper": paper})

    except Exception as e:
        logger.error(f"Error generating paper: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================================
# CUSTOM USER QUESTION SETS ENDPOINTS (QUESTION POOLS & SETS)
# =========================================================================
@app.route("/api/question-sets", methods=["GET"])
def get_question_sets():
    """Retrieve custom question sets for authenticated faculty member."""
    try:
        auth_header = request.headers.get("Authorization") or request.headers.get("X-Auth-Token")
        auth_user = get_user_by_token(auth_header)
        user_id = auth_user["user_id"] if auth_user else (request.args.get("user_id") or "default")

        sets = load_user_question_sets(user_id)
        return jsonify({"success": True, "sets": sets})
    except Exception as e:
        logger.error(f"Error retrieving question sets: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/question-sets", methods=["POST"])
def save_question_sets_endpoint():
    """Save or update custom question sets (e.g. Set 1, Set 2, Set 3, Set 4)."""
    try:
        data = request.get_json() or {}
        sets_data = data.get("sets", [])
        if not isinstance(sets_data, list):
            return jsonify({"success": False, "error": "Question sets must be a list of sets."}), 400

        auth_header = request.headers.get("Authorization") or request.headers.get("X-Auth-Token")
        auth_user = get_user_by_token(auth_header)
        user_id = auth_user["user_id"] if auth_user else (data.get("user_id") or "default")

        save_user_question_sets(user_id, sets_data)
        return jsonify({"success": True, "sets": sets_data, "message": "Question sets updated successfully."})
    except Exception as e:
        logger.error(f"Error saving question sets: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================================
# USER AUTHENTICATION ENDPOINTS (WITH STRICT SESSION SECURITY)
# =========================================================================
@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticate user with username and password, returning an isolated session token."""
    try:
        data = request.get_json() or {}
        username = data.get("username", "")
        password = data.get("password", "")
        if not username:
            return jsonify({"success": False, "error": "Username is required."}), 400

        user = authenticate_user(username, password)
        if not user:
            return jsonify({"success": False, "error": "Incorrect username or password."}), 401

        token = create_session(user["user_id"])
        return jsonify({"success": True, "user": user, "token": token})
    except Exception as e:
        logger.error(f"Error during login: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Register a new faculty user profile and issue an isolated session token."""
    try:
        data = request.get_json() or {}
        username = data.get("username", "")
        display_name = data.get("display_name", "")
        department = data.get("department", "")
        password = data.get("password", "")

        if not username:
            return jsonify({"success": False, "error": "Username is required."}), 400
        if len(password) < 6:
            return jsonify({"success": False, "error": "Password must be at least 6 characters long."}), 400

        user = register_user(username, display_name, department, password)
        token = create_session(user["user_id"])
        return jsonify({"success": True, "user": user, "token": token})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/auth/forgot-password", methods=["POST"])
@app.route("/api/auth/reset-password", methods=["POST"])
def auth_forgot_password():
    """Reset faculty password by username."""
    try:
        data = request.get_json() or {}
        username = data.get("username", "").strip()
        new_password = data.get("new_password", "").strip()
        if not username:
            return jsonify({"success": False, "error": "Faculty username or ID is required."}), 400
        if not new_password or len(new_password) < 6:
            return jsonify({"success": False, "error": "New password must be at least 6 characters long."}), 400

        ok = reset_user_password(username, new_password)
        if ok:
            return jsonify({
                "success": True,
                "message": f"Password for {username} reset successfully. You can now sign in with your new password."
            })
        return jsonify({"success": False, "error": "No teacher account found with that username."}), 400
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Destroy session token on logout."""
    token = request.headers.get("Authorization") or request.headers.get("X-Auth-Token")
    destroy_session(token)
    return jsonify({"success": True})


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Verify session token and return the currently authenticated faculty profile."""
    token = request.headers.get("Authorization") or request.headers.get("X-Auth-Token")
    user = get_user_by_token(token)
    if not user:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    return jsonify({"success": True, "user": user})


# =========================================================================
# PAST PAPER HISTORY ENDPOINTS (STRICT ISOLATION PER FACULTY)
# =========================================================================
@app.route("/api/history", methods=["GET"])
def get_history():
    """Retrieve history of question papers strictly for current authenticated user."""
    try:
        token = request.headers.get("Authorization") or request.headers.get("X-Auth-Token")
        user = get_user_by_token(token)
        if not user:
            return jsonify({"success": False, "error": "Please sign in to view your question papers."}), 401
        user_id = user["user_id"]

        history = get_user_history(user_id)
        return jsonify({"success": True, "history": history})
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history/<paper_id>", methods=["GET"])
def get_history_single(paper_id):
    """Retrieve complete question paper data strictly from current user's archive."""
    try:
        token = request.headers.get("Authorization") or request.headers.get("X-Auth-Token")
        user = get_user_by_token(token)
        if not user:
            return jsonify({"success": False, "error": "Please sign in to view your question papers."}), 401
        user_id = user["user_id"]

        paper_data = get_history_paper(user_id, paper_id)
        if not paper_data:
            return jsonify({"success": False, "error": "Paper not found in your archive."}), 404

        return jsonify({"success": True, "paper": paper_data})
    except Exception as e:
        logger.error(f"Error retrieving paper from history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history/<paper_id>", methods=["DELETE"])
def delete_history_single(paper_id):
    """Delete a past paper strictly from current user's archive."""
    try:
        token = request.headers.get("Authorization") or request.headers.get("X-Auth-Token")
        user = get_user_by_token(token)
        if not user:
            return jsonify({"success": False, "error": "Please sign in to view your question papers."}), 401
        user_id = user["user_id"]

        deleted = delete_history_paper(user_id, paper_id)
        return jsonify({"success": True, "deleted": deleted})
    except Exception as e:
        logger.error(f"Error deleting paper from history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================================
# CUSTOM TEMPLATES ENDPOINTS
# =========================================================================
@app.route("/api/templates", methods=["GET"])
def get_templates():
    """Retrieve all available templates (built-in + custom)."""
    try:
        return jsonify({"success": True, "templates": load_all_templates()})
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/templates", methods=["POST"])
def save_template_endpoint():
    """Create or update a custom exam template."""
    try:
        data = request.get_json() or {}
        template_id = data.get("id")
        template_data = data.get("template")

        if not template_id or not template_data:
            return jsonify({"success": False, "error": "Template ID and template data are required."}), 400

        # Mark as custom
        template_data["is_custom"] = True
        save_custom_template(template_id, template_data)
        return jsonify({"success": True, "template_id": template_id, "template": template_data})
    except Exception as e:
        logger.error(f"Error saving custom template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/templates/<template_id>", methods=["DELETE"])
def delete_template_endpoint(template_id):
    """Delete a custom exam template."""
    try:
        if template_id in EXAM_TEMPLATES:
            return jsonify({"success": False, "error": "Built-in standard templates cannot be deleted."}), 400

        deleted = delete_custom_template(template_id)
        return jsonify({"success": True, "deleted": deleted})
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/blueprint/marking-scheme-template", methods=["GET"])
def get_marking_scheme_template():
    """Returns standard university marking scheme format template JSON."""
    template = {
        "scheme_name": "Standard University Examination Format",
        "total_marks": 100,
        "duration": "3 Hours",
        "instructions": [
            "Part A is compulsory. All questions carry 2 marks each.",
            "Part B contains analytical problems with internal choice (10 marks each).",
            "Part C contains design/synthesis comprehensive questions (20 marks each)."
        ],
        "sections": [
            {
                "id": "sec_a",
                "name": "Part A - Fundamental Recall & Understanding",
                "instructions": "Answer all 10 questions. (2 Marks each)",
                "type": "compulsory",
                "question_count": 10,
                "marks_per_question": 2,
                "total_section_marks": 20,
                "allowed_levels": ["L1", "L2"],
                "has_internal_choice": False
            },
            {
                "id": "sec_b",
                "name": "Part B - Problem Solving & Critical Analysis",
                "instructions": "Answer any four questions out of five with internal choice. (10 Marks each)",
                "type": "choice",
                "question_count": 4,
                "marks_per_question": 10,
                "total_section_marks": 40,
                "allowed_levels": ["L3", "L4"],
                "has_internal_choice": True
            },
            {
                "id": "sec_c",
                "name": "Part C - Architecture Synthesis & Design",
                "instructions": "Answer two comprehensive design questions with internal choice. (20 Marks each)",
                "type": "comprehensive",
                "question_count": 2,
                "marks_per_question": 20,
                "total_section_marks": 40,
                "allowed_levels": ["L5", "L6"],
                "has_internal_choice": True
            }
        ]
    }
    return jsonify({"success": True, "template": template})


@app.route("/api/blueprint/upload-marking-scheme", methods=["POST"])
def upload_marking_scheme():
    """
    Parses and validates an uploaded marking scheme file (JSON or formatted text).
    """
    try:
        raw_data = None
        if "file" in request.files:
            uploaded_file = request.files["file"]
            content = uploaded_file.read().decode("utf-8", errors="replace")
            try:
                raw_data = json.loads(content)
            except Exception:
                return jsonify({"success": False, "error": "Uploaded file must be valid JSON format matching the schema."}), 400
        elif request.is_json:
            raw_data = request.get_json()
        else:
            return jsonify({"success": False, "error": "Invalid format. Send JSON payload or multipart file."}), 400

        if not raw_data:
            return jsonify({"success": False, "error": "Empty marking scheme data received."}), 400

        # Validate sections
        sections = raw_data.get("sections")
        if not sections or not isinstance(sections, list) or len(sections) == 0:
            return jsonify({"success": False, "error": "Marking scheme must specify at least one section with questions."}), 400

        sanitized_sections = []
        total_computed_marks = 0

        for idx, s in enumerate(sections, 1):
            q_count = max(1, int(s.get("question_count", 1)))
            marks_per_q = max(1, int(s.get("marks_per_question", 2)))
            sec_marks = int(s.get("total_section_marks", q_count * marks_per_q))
            total_computed_marks += sec_marks

            allowed_lvls = s.get("allowed_levels", ["L1", "L2"])
            if not isinstance(allowed_lvls, list):
                allowed_lvls = ["L1", "L2"]
            allowed_lvls = [lvl for lvl in allowed_lvls if lvl in BLOOM_LEVELS]
            if not allowed_lvls:
                allowed_lvls = ["L2"]

            sanitized_sections.append({
                "id": s.get("id", f"sec_{idx}"),
                "name": s.get("name", f"Section {chr(64 + idx)}"),
                "instructions": s.get("instructions", f"Answer questions in Section {chr(64 + idx)}."),
                "type": s.get("type", "compulsory"),
                "question_count": q_count,
                "marks_per_question": marks_per_q,
                "total_section_marks": sec_marks,
                "allowed_levels": allowed_lvls,
                "has_internal_choice": bool(s.get("has_internal_choice", False))
            })

        duration = raw_data.get("duration", "3 Hours")
        exam_title = raw_data.get("scheme_name", raw_data.get("exam_title", "Custom Examination Format"))
        total_marks = int(raw_data.get("total_marks", total_computed_marks))

        return jsonify({
            "success": True,
            "marking_scheme": {
                "exam_title": exam_title,
                "total_marks": total_marks,
                "duration": duration,
                "instructions": raw_data.get("instructions", []),
                "sections": sanitized_sections
            }
        })

    except Exception as e:
        logger.error(f"Error parsing marking scheme: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download-zip", methods=["GET"])
def download_project_zip():
    """
    Dynamically packages the complete project into a clean zip archive and streams it.
    Excludes venv, __pycache__, .git, and temporary files.
    """
    try:
        memory_file = io.BytesIO()
        exclude_dirs = {"venv", ".venv", "__pycache__", ".git", ".idea", ".vscode", "node_modules"}
        exclude_exts = {".pyc", ".pyo", ".pyd"}

        with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(BASE_DIR):
                dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]

                for file in files:
                    if any(file.endswith(ext) for ext in exclude_exts) or file.endswith(".zip"):
                        continue

                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, BASE_DIR)
                    zf.write(file_path, arcname)

        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name="bloomcraft_ai_project.zip"
        )
    except Exception as e:
        logger.error(f"Error packaging zip: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/paper/regenerate-question", methods=["POST"])
def regenerate_question():
    """
    Regenerates a single question slot with a fresh alternative.
    """
    try:
        data = request.get_json() or {}
        slot = data.get("slot")
        if not slot:
            return jsonify({"success": False, "error": "Slot specification is required."}), 400

        api_config = data.get("api_config", {})
        exclude_texts = data.get("exclude_texts", [])

        fresh_question = generate_single_question(
            slot,
            api_config=api_config,
            exclude_texts=exclude_texts,
            diagram_mode=data.get("diagram_mode", "auto")
        )

        return jsonify({"success": True, "question": fresh_question})

    except Exception as e:
        logger.error(f"Error regenerating question: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/llm/status", methods=["POST"])
def llm_status():
    """Shows which free-tier providers have keys and which models were discovered (for the Settings screen)."""
    try:
        from core import llm_client
        data = request.get_json() or {}
        return jsonify({"success": True, **llm_client.status(data.get("api_config", {}), refresh=bool(data.get("refresh")))})
    except Exception as e:
        logger.error(f"Error reading LLM status: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/diagram/generate", methods=["POST"])
def generate_diagram_endpoint():
    """
    On-demand technical schematic and diagram generation for any examination question.
    Supports runtime AI diagram design (free-tier Groq/OpenRouter/Cerebras/Mistral) with an offline fallback.
    """
    try:
        data = request.get_json() or {}
        topic = data.get("topic", "Engineering Concept")
        question_text = data.get("question_text", "")
        bloom_level = data.get("bloom_level", "L2")
        display_num = data.get("display_num", "Q")
        diagram_type = data.get("diagram_type", "auto")
        custom_prompt = data.get("custom_prompt")
        api_config = data.get("api_config", {})
        marks = data.get("marks")
        variation = int(data.get("variation") or 0)

        # An explicit request from the teacher always draws something (force=True)
        figure = generate_technical_diagram(
            topic=topic,
            bloom_level=bloom_level,
            question_num=display_num,
            question_text=question_text,
            custom_prompt=custom_prompt,
            api_config=api_config,
            diagram_type=diagram_type,
            marks=marks,
            force=True,
            variation=variation
        )

        if not figure:
            from core import llm_client
            if llm_client.is_available(api_config):
                # AI is configured: do not hide the failure behind a fixed template diagram
                reason = "; ".join(llm_client.last_errors[-2:]) or "the model returned no usable diagram"
                logger.warning(f"AI diagram failed for {display_num}: {reason}")
                return jsonify({
                    "success": False,
                    "error": "AI could not design this diagram right now (usually a free-tier rate limit). "
                             "Wait a few seconds and press regenerate. Details: " + reason[:200]
                }), 502
            # No key configured: offline fallback guarantee
            from core.figure_generator import synthesize_parametric_diagram
            figure = synthesize_parametric_diagram(
                topic=topic,
                question_text=question_text,
                bloom_level=bloom_level,
                question_num=display_num,
                custom_prompt=custom_prompt,
                diagram_type=diagram_type
            )

        return jsonify({"success": True, "figure": figure})

    except Exception as e:
        logger.error(f"Error generating diagram: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/paper/export-doc", methods=["POST"])
@app.route("/api/export/word", methods=["POST"])
def export_doc():
    """
    Exports the question paper as a Word (.docx) file with diagrams embedded.
    """
    try:
        data = request.get_json() or {}
        paper_data = data.get("paper")
        if not paper_data:
            return jsonify({"success": False, "error": "Paper data is required."}), 400

        docx_bytes = generate_word_docx(paper_data)
        course_code = (paper_data.get("course_code") or "EXAM").replace(" ", "_")

        return Response(
            docx_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={course_code}_Question_Paper.docx"}
        )

    except Exception as e:
        logger.error(f"Error exporting Word document: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f"  BloomCraft - Bloom's Taxonomy Question Paper Generator")
    print(f"  Server running on http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
