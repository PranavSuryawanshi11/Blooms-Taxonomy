"""
Bloom's Taxonomy Question Paper Generator - System Configuration & Presets
Revised Bloom's Taxonomy (Anderson & Krathwohl 2001)
"""

BLOOM_LEVELS = {
    "L1": {
        "code": "L1",
        "aicte_level": 1,
        "name": "Remembering",
        "short_name": "Remember",
        "aicte_descriptor": "Recalling from the memory of the previously learned material",
        "description": "Recall facts, terms, basic concepts, definitions, and answers without necessarily understanding them.",
        "color": "#3B82F6",  # Blue
        "bg_color": "rgba(59, 130, 246, 0.15)",
        "border_color": "#3B82F6",
        "default_marks_range": [1, 5],
        "verbs": [
            "Arrange", "Define", "Describe", "Duplicate", "Identify", "Label", 
            "List", "Match", "Memorize", "Name", "Order", "Outline", 
            "Recognize", "Relate", "Recall", "Repeat", "Reproduce", "Select", "State"
        ],
        "aicte_verbs": [
            "arrange", "define", "describe", "duplicate", "identify", "label", 
            "list", "match", "memorize", "name", "order", "outline", 
            "recognize", "relate", "recall", "repeat", "reproduce", "select", "state"
        ]
    },
    "L2": {
        "code": "L2",
        "aicte_level": 2,
        "name": "Understanding",
        "short_name": "Understand",
        "aicte_descriptor": "Explaining ideas or concepts",
        "description": "Demonstrate understanding of facts and ideas by organizing, comparing, translating, interpreting, giving descriptions, and stating main ideas.",
        "color": "#10B981",  # Emerald Green
        "bg_color": "rgba(16, 185, 129, 0.15)",
        "border_color": "#10B981",
        "default_marks_range": [2, 6],
        "verbs": [
            "Explain", "Describe", "Summarize", "Paraphrase", "Illustrate", "Classify", 
            "Convert", "Defend", "Discuss", "Distinguish", "Estimate", "Express", 
            "Extend", "Generalize", "Give example", "Identify", "Indicate", "Infer", 
            "Locate", "Predict", "Recognize", "Rewrite", "Review", "Select", "Translate"
        ],
        "aicte_verbs": [
            "explain", "summarize", "paraphrase", "describe", "illustrate", "classify", 
            "convert", "defend", "discuss", "distinguish", "estimate", "express", 
            "extend", "generalized", "give example(s)", "identify", "indicate", "infer", 
            "locate", "predict", "recognize", "rewrite", "review", "select", "translate"
        ]
    },
    "L3": {
        "code": "L3",
        "aicte_level": 3,
        "name": "Applying",
        "short_name": "Apply",
        "aicte_descriptor": "Using the information in another familiar situation",
        "description": "Solve problems in new situations by applying acquired knowledge, facts, techniques and rules in a different way.",
        "color": "#F59E0B",  # Amber
        "bg_color": "rgba(245, 158, 11, 0.15)",
        "border_color": "#F59E0B",
        "default_marks_range": [4, 10],
        "verbs": [
            "Apply", "Solve", "Compute", "Demonstrate", "Construct", "Use", 
            "Calculate", "Determine", "Change", "Choose", "Discover", "Dramatize", 
            "Employ", "Illustrate", "Interpret", "Manipulate", "Modify", "Operate", 
            "Practice", "Predict", "Prepare", "Produce", "Relate", "Schedule", "Show", "Sketch", "Write"
        ],
        "aicte_verbs": [
            "use", "compute", "solve", "demonstrate", "apply", "construct", 
            "change", "choose", "discover", "dramatize", "employ", "illustrate", 
            "interpret", "manipulate", "modify", "operate", "practice", "predict", 
            "prepare", "produce", "relate", "schedule", "show", "sketch", "write"
        ]
    },
    "L4": {
        "code": "L4",
        "aicte_level": 4,
        "name": "Analyzing",
        "short_name": "Analyze",
        "aicte_descriptor": "Breaking information into the part to explore understandings and relationships",
        "description": "Examine and break information into parts by identifying motives or causes. Make inferences and find evidence to support generalizations.",
        "color": "#F97316",  # Orange
        "bg_color": "rgba(249, 115, 22, 0.15)",
        "border_color": "#F97316",
        "default_marks_range": [6, 12],
        "verbs": [
            "Analyze", "Categorize", "Compare", "Contrast", "Separate", "Differentiate", 
            "Deconstruct", "Distinguish", "Investigate", "Apply", "Change", "Discover", 
            "Choose", "Compute", "Demonstrate", "Dramatize", "Employ", "Illustrate", 
            "Interpret", "Manipulate", "Modify", "Operate", "Practice", "Predict", 
            "Prepare", "Produce", "Relate", "Schedule", "Show", "Sketch", "Solve", "Use", "Write"
        ],
        "aicte_verbs": [
            "analyze", "categorize", "compare", "contrast", "separate", "apply", 
            "change", "discover", "choose", "compute", "demonstrate", "dramatize", 
            "employ", "illustrate", "interpret", "manipulate", "modify", "operate", 
            "practice", "predict", "prepare", "produce", "relate", "schedule", 
            "show", "sketch", "solve", "use", "write"
        ]
    },
    "L5": {
        "code": "L5",
        "aicte_level": 5,
        "name": "Evaluating",
        "short_name": "Evaluate",
        "aicte_descriptor": "Justifying a decision or course of action",
        "description": "Present and defend opinions by making judgments about information, validity of ideas, or quality of work based on a set of criteria.",
        "color": "#EC4899",  # Rose Pink
        "bg_color": "rgba(236, 72, 153, 0.15)",
        "border_color": "#EC4899",
        "default_marks_range": [8, 15],
        "verbs": [
            "Judge", "Recommend", "Critique", "Justify", "Appraise", "Argue", 
            "Assess", "Attach", "Choose", "Compare", "Conclude", "Contrast", 
            "Defend", "Describe", "Discriminate", "Estimate", "Evaluate", "Explain", 
            "Interpret", "Relate", "Predict", "Rate", "Select", "Summarize", "Support", "Value"
        ],
        "aicte_verbs": [
            "judge", "recommend", "critique", "justify", "appraise", "argue", 
            "assess", "attach", "choose", "compare", "conclude", "contrast", 
            "defend", "describe", "discriminate", "estimate", "evaluate", "explain", 
            "interpret", "relate", "predict", "rate", "select", "summarize", "support", "value"
        ]
    },
    "L6": {
        "code": "L6",
        "aicte_level": 6,
        "name": "Creating",
        "short_name": "Create",
        "aicte_descriptor": "Generating new ideas, products or new ways of viewing things",
        "description": "Compile information together in a different way by combining elements in a new pattern or proposing alternative solutions.",
        "color": "#8B5CF6",  # Purple
        "bg_color": "rgba(139, 92, 246, 0.15)",
        "border_color": "#8B5CF6",
        "default_marks_range": [10, 16],
        "verbs": [
            "Create", "Design", "Hypothesize", "Invent", "Develop", "Arrange", 
            "Assemble", "Categorize", "Collect", "Combine", "Comply", "Construct", 
            "Devise", "Explain", "Formulate", "Generate", "Plan", "Prepare", 
            "Rearrange", "Reconstruct", "Relate", "Reorganize", "Revise", "Rewrite", 
            "Set up", "Summarize", "Synthesize", "Tell", "Write"
        ],
        "aicte_verbs": [
            "create", "design", "hypothesize", "invent", "develop", "arrange", 
            "assemble", "categorize", "collect", "combine", "comply", "construct", 
            "devise", "explain", "formulate", "generate", "plan", "prepare", 
            "rearrange", "reconstruct", "relate", "reorganize", "revise", "rewrite", 
            "set up", "summarize", "synthesize", "tell", "write"
        ]
    }
}

BLOOM_ORDER = ["L1", "L2", "L3", "L4", "L5", "L6"]

# Blueprint Cognitive Presets (Percentages must sum to 100)
BLOOM_PRESETS = {
    "balanced": {
        "id": "balanced",
        "name": "AICTE / NBA Balanced Academic",
        "description": "Standard engineering university distribution balancing foundational recall with analytical and evaluation capabilities.",
        "distribution": {"L1": 20, "L2": 25, "L3": 25, "L4": 15, "L5": 10, "L6": 5}
    },
    "analytical": {
        "id": "analytical",
        "name": "Problem Solving & Analytical Focus",
        "description": "Heavy emphasis on application, problem solving, analysis, and algorithm implementation.",
        "distribution": {"L1": 10, "L2": 20, "L3": 35, "L4": 20, "L5": 10, "L6": 5}
    },
    "foundational": {
        "id": "foundational",
        "name": "Conceptual & Foundational (Beginner)",
        "description": "Suitable for introductory semester subjects or 1st year foundational theory tests.",
        "distribution": {"L1": 35, "L2": 35, "L3": 20, "L4": 10, "L5": 0, "L6": 0}
    },
    "advanced": {
        "id": "advanced",
        "name": "Advanced Synthesis & Design (Senior/PG)",
        "description": "Focuses on higher-order cognitive skills: deconstructing architecture, critique, and system design.",
        "distribution": {"L1": 10, "L2": 15, "L3": 20, "L4": 25, "L5": 20, "L6": 10}
    }
}

# Standard Exam Blueprint Templates
EXAM_TEMPLATES = {
    "end_sem_100": {
        "id": "end_sem_100",
        "name": "Semester End Examination (100 Marks)",
        "duration": "3 Hours",
        "total_marks": 100,
        "instructions": [
            "Answer all questions from Part A and any five questions from Part B.",
            "Make suitable assumptions wherever necessary and state them clearly.",
            "Draw neat sketches and diagrams wherever required."
        ],
        "sections": [
            {
                "id": "sec_a",
                "name": "Part A - Short Conceptual Questions",
                "instructions": "Answer all questions. Each carries 2 marks.",
                "type": "compulsory",
                "question_count": 10,
                "marks_per_question": 2,
                "total_section_marks": 20,
                "allowed_levels": ["L1", "L2"]
            },
            {
                "id": "sec_b",
                "name": "Part B - Analytical & Applied Problems",
                "instructions": "Answer any four questions out of five. Each carries 10 marks.",
                "type": "choice",
                "question_count": 5,
                "marks_per_question": 10,
                "total_section_marks": 40,
                "allowed_levels": ["L2", "L3", "L4"],
                "has_internal_choice": True
            },
            {
                "id": "sec_c",
                "name": "Part C - Comprehensive Design & Evaluation",
                "instructions": "Answer two questions with internal choice. Each carries 20 marks (or 2 x 10 marks).",
                "type": "comprehensive",
                "question_count": 2,
                "marks_per_question": 20,
                "total_section_marks": 40,
                "allowed_levels": ["L4", "L5", "L6"],
                "has_internal_choice": True
            }
        ]
    },
    "mid_sem_50": {
        "id": "mid_sem_50",
        "name": "Mid-Semester Examination / Internal Assessment (50 Marks)",
        "duration": "2 Hours",
        "total_marks": 50,
        "instructions": [
            "Answer all questions in Section A and Section B.",
            "All questions are compulsory."
        ],
        "sections": [
            {
                "id": "sec_a",
                "name": "Section A - Fundamental Principles",
                "instructions": "Answer all questions. Each carries 2 marks.",
                "type": "compulsory",
                "question_count": 5,
                "marks_per_question": 2,
                "total_section_marks": 10,
                "allowed_levels": ["L1", "L2"]
            },
            {
                "id": "sec_b",
                "name": "Section B - Analytical & Implementation",
                "instructions": "Answer all questions. Each carries 8 marks.",
                "type": "compulsory",
                "question_count": 5,
                "marks_per_question": 8,
                "total_section_marks": 40,
                "allowed_levels": ["L2", "L3", "L4", "L5"],
                "has_internal_choice": True
            }
        ]
    },
    "cat_70": {
        "id": "cat_70",
        "name": "Continuous Assessment Test (70 Marks)",
        "duration": "3 Hours",
        "total_marks": 70,
        "instructions": [
            "Part A is compulsory. Part B contains either-or questions for each unit."
        ],
        "sections": [
            {
                "id": "sec_a",
                "name": "Part A - Objective & Short Answers",
                "instructions": "Answer all 10 questions. Each carries 2 marks.",
                "type": "compulsory",
                "question_count": 10,
                "marks_per_question": 2,
                "total_section_marks": 20,
                "allowed_levels": ["L1", "L2"]
            },
            {
                "id": "sec_b",
                "name": "Part B - Core Subjective Problems",
                "instructions": "Answer 5 questions (one from each unit with internal choice). Each carries 10 marks.",
                "type": "either_or",
                "question_count": 5,
                "marks_per_question": 10,
                "total_section_marks": 50,
                "allowed_levels": ["L3", "L4", "L5", "L6"],
                "has_internal_choice": True
            }
        ]
    },
    "quiz_30": {
        "id": "quiz_30",
        "name": "Unit Assessment / Class Quiz (30 Marks)",
        "duration": "1 Hour",
        "total_marks": 30,
        "instructions": [
            "Answer all questions within 60 minutes."
        ],
        "sections": [
            {
                "id": "sec_a",
                "name": "Section A - Quick Recall",
                "instructions": "Answer all 5 questions. (2 Marks each)",
                "type": "compulsory",
                "question_count": 5,
                "marks_per_question": 2,
                "total_section_marks": 10,
                "allowed_levels": ["L1", "L2"]
            },
            {
                "id": "sec_b",
                "name": "Section B - Problem Solving",
                "instructions": "Answer any 2 out of 3 questions. (10 Marks each)",
                "type": "choice",
                "question_count": 2,
                "marks_per_question": 10,
                "total_section_marks": 20,
                "allowed_levels": ["L3", "L4"],
                "has_internal_choice": False
            }
        ]
    },
    "rcpit_sem_65": {
        "id": "rcpit_sem_65",
        "name": "R. C. Patel Institute of Technology, Shirpur - End Semester (65 Marks)",
        "duration": "02:00 Hrs.",
        "total_marks": 65,
        "college_profile": {
            "society": "Shirpur Education Society's",
            "college": "R. C. PATEL INSTITUTE OF TECHNOLOGY, SHIRPUR",
            "tagline": "An Autonomous Institute",
            "affiliation": "[ Affiliated to Dr. Babasaheb Ambedkar Technological University, Lonere ]",
            "regional_title": "आर. सी. पटेल इन्स्टिट्यूट ऑफ टेक्नॉलॉजी, शिरपूर (स्वायत्त महाविद्यालय)",
            "programme": "B.Tech in Computer Science and Engineering (Data Science)",
            "year_semester": "Year: II / Semester IV (Exam Year: 2024-2025)",
            "exam_title": "END SEMESTER EXAMINATION EVEN SEM-IV",
            "logo_text": "SES - RCPIT"
        },
        "instructions": [
            "This question paper contains standard pages.",
            "Answer to each new question to be started on a fresh page.",
            "Figure in right hand side indicates full marks.",
            "All four questions are compulsory.",
            "Assume suitable data where required.",
            "Draw neat graphs and diagrams wherever applicable.",
            "Options are given inside the questions."
        ],
        "sections": [
            {
                "id": "sec_1",
                "name": "Question 1 - Compulsory Conceptual & Foundational Sub-Questions",
                "instructions": "All sub-questions of Question 1 are compulsory. (4 x 5 Marks = 20 Marks)",
                "type": "compulsory",
                "question_count": 4,
                "marks_per_question": 5,
                "question_marks": [5, 5, 5, 5],
                "question_choices": [False, False, False, False],
                "total_section_marks": 20,
                "allowed_levels": ["L1", "L2", "L3", "L4"],
                "has_internal_choice": False
            },
            {
                "id": "sec_2",
                "name": "Question 2 - Core Formulation & Technical Analysis",
                "instructions": "Question 2a is compulsory (5M) and solve any one from Question 2b (10M). (15 Marks)",
                "type": "choice",
                "question_count": 2,
                "marks_per_question": 10,
                "question_marks": [5, 10],
                "question_choices": [False, True],
                "total_section_marks": 15,
                "allowed_levels": ["L2", "L3", "L4"],
                "has_internal_choice": True
            },
            {
                "id": "sec_3",
                "name": "Question 3 - Applied Problem Solving & Model Synthesis",
                "instructions": "Question 3a is compulsory (5M) and solve any one from Question 3b (10M). (15 Marks)",
                "type": "choice",
                "question_count": 2,
                "marks_per_question": 10,
                "question_marks": [5, 10],
                "question_choices": [False, True],
                "total_section_marks": 15,
                "allowed_levels": ["L3", "L4", "L5"],
                "has_internal_choice": True
            },
            {
                "id": "sec_4",
                "name": "Question 4 - Comprehensive Design & Evaluative Case Study",
                "instructions": "Solve any one from Question 4a or Question 4b with internal choice. (15 Marks)",
                "type": "either_or",
                "question_count": 1,
                "marks_per_question": 15,
                "question_marks": [15],
                "question_choices": [True],
                "total_section_marks": 15,
                "allowed_levels": ["L4", "L5", "L6"],
                "has_internal_choice": True
            }
        ]
    },
    "rcpit_sem_60": {
        "id": "rcpit_sem_60",
        "name": "R. C. Patel Institute of Technology, Shirpur - Regular (60 Marks)",
        "duration": "02:00 Hrs.",
        "total_marks": 60,
        "college_profile": {
            "society": "Shirpur Education Society's",
            "college": "R. C. PATEL INSTITUTE OF TECHNOLOGY, SHIRPUR",
            "tagline": "An Autonomous Institute",
            "affiliation": "[ Affiliated to Dr. Babasaheb Ambedkar Technological University, Lonere ]",
            "regional_title": "आर. सी. पटेल इन्स्टिट्यूट ऑफ टेक्नॉलॉजी, शिरपूर",
            "programme": "B.Tech in C S E (Data Science)",
            "year_semester": "Year: II / Semester IV",
            "exam_title": "END SEMESTER EXAMINATION EVEN SEM IV REGULAR",
            "logo_text": "SES - RCPIT"
        },
        "instructions": [
            "This question paper contains standard pages.",
            "Figure in right hand side indicates full marks.",
            "Draw neat graphs wherever necessary.",
            "Use of Statistical Tables is allowed."
        ],
        "sections": [
            {
                "id": "sec_1",
                "name": "Part 1 - Fundamental Analysis & Formulation",
                "instructions": "Answer questions. Marks indicated on right.",
                "type": "compulsory",
                "question_count": 4,
                "marks_per_question": 5,
                "total_section_marks": 20,
                "allowed_levels": ["L1", "L2", "L3"],
                "has_internal_choice": True
            },
            {
                "id": "sec_2",
                "name": "Part 2 - Core Applied Problems",
                "instructions": "Answer questions with internal choice.",
                "type": "choice",
                "question_count": 2,
                "marks_per_question": 10,
                "total_section_marks": 20,
                "allowed_levels": ["L3", "L4"],
                "has_internal_choice": True
            },
            {
                "id": "sec_3",
                "name": "Part 3 - Advanced Statistical/Algorithm Execution",
                "instructions": "Solve questions with internal choice.",
                "type": "comprehensive",
                "question_count": 2,
                "marks_per_question": 10,
                "total_section_marks": 20,
                "allowed_levels": ["L4", "L5", "L6"],
                "has_internal_choice": True
            }
        ]
    },
    "djsce_sem_60": {
        "id": "djsce_sem_60",
        "name": "SVKM D. J. Sanghvi College of Engineering, Mumbai (60 Marks)",
        "duration": "02:00 Hrs.",
        "total_marks": 60,
        "college_profile": {
            "society": "SVKM",
            "college": "D. J. Sanghvi College of Engineering",
            "tagline": "Autonomous College Affiliated to University of Mumbai",
            "programme": "B.Tech in Computer Science and Engineering (Data Science)",
            "year_semester": "Year: II / Semester IV (Exam Year: 2024-2025)",
            "exam_title": "FINAL EXAMINATION (2024-2025)",
            "logo_text": "SVKM - DJSCE"
        },
        "instructions": [
            "This question paper contains examination pages.",
            "Answer to each new question to be started on a fresh page.",
            "Figure in right hand side indicates full marks.",
            "Assume suitable data where needed.",
            "Read the questions and options carefully.",
            "Show all the steps of numerical in fair work.",
            "Draw neat graphs and charts wherever necessary."
        ],
        "sections": [
            {
                "id": "sec_1",
                "name": "Question 1 - Core Theory & Analytical Concepts",
                "instructions": "All sub-questions compulsory or internal choice as specified. (15 Marks)",
                "type": "compulsory",
                "question_count": 3,
                "marks_per_question": 5,
                "total_section_marks": 15,
                "allowed_levels": ["L1", "L2", "L3"],
                "has_internal_choice": True
            },
            {
                "id": "sec_2",
                "name": "Question 2 - Mathematical Formulation & Optimization",
                "instructions": "Solve sub-questions with internal choice. (15 Marks)",
                "type": "choice",
                "question_count": 2,
                "marks_per_question": 7,
                "total_section_marks": 15,
                "allowed_levels": ["L3", "L4"],
                "has_internal_choice": True
            },
            {
                "id": "sec_3",
                "name": "Question 3 - Algorithm Execution & Clustering",
                "instructions": "Solve sub-questions with internal choice. (15 Marks)",
                "type": "choice",
                "question_count": 2,
                "marks_per_question": 7,
                "total_section_marks": 15,
                "allowed_levels": ["L3", "L4", "L5"],
                "has_internal_choice": True
            },
            {
                "id": "sec_4",
                "name": "Question 4 - Machine Learning & Statistical Inference",
                "instructions": "Solve any one comprehensive problem. (15 Marks)",
                "type": "either_or",
                "question_count": 1,
                "marks_per_question": 15,
                "total_section_marks": 15,
                "allowed_levels": ["L4", "L5", "L6"],
                "has_internal_choice": True
            }
        ]
    },
    "unit_test_20": {
        "id": "unit_test_20",
        "name": "Continuous Internal Evaluation / Unit Test (20 Marks)",
        "duration": "45 Mins - 1 Hour",
        "total_marks": 20,
        "instructions": [
            "All questions are compulsory.",
            "Figures to the right indicate full marks."
        ],
        "sections": [
            {
                "id": "sec_a",
                "name": "Part A - Fundamental Recall & Understanding",
                "instructions": "Answer all questions. (2 x 2.5 = 5 Marks)",
                "type": "compulsory",
                "question_count": 2,
                "marks_per_question": 2,
                "total_section_marks": 5,
                "allowed_levels": ["L1", "L2"],
                "has_internal_choice": False
            },
            {
                "id": "sec_b",
                "name": "Part B - Core Analytical Problem",
                "instructions": "Solve the analytical problem. (5 Marks)",
                "type": "compulsory",
                "question_count": 1,
                "marks_per_question": 5,
                "total_section_marks": 5,
                "allowed_levels": ["L3", "L4"],
                "has_internal_choice": False
            },
            {
                "id": "sec_c",
                "name": "Part C - Applied Problem with Internal Choice",
                "instructions": "Solve with internal option. (10 Marks)",
                "type": "either_or",
                "question_count": 1,
                "marks_per_question": 10,
                "total_section_marks": 10,
                "allowed_levels": ["L3", "L4", "L5"],
                "has_internal_choice": True
            }
        ]
    },
    "insem_25": {
        "id": "insem_25",
        "name": "In-Semester Assessment / Mid-Term Test (25 Marks)",
        "duration": "1 Hour",
        "total_marks": 25,
        "instructions": [
            "Answer all sections in sequence.",
            "Figures to the right indicate full marks."
        ],
        "sections": [
            {
                "id": "sec_a",
                "name": "Section A - Conceptual Foundations",
                "instructions": "Answer both conceptual questions. (2 x 2.5 = 5 Marks)",
                "type": "compulsory",
                "question_count": 2,
                "marks_per_question": 2,
                "total_section_marks": 5,
                "allowed_levels": ["L1", "L2"],
                "has_internal_choice": False
            },
            {
                "id": "sec_b",
                "name": "Section B - Analytical Problems",
                "instructions": "Answer both problems. (2 x 5 = 10 Marks)",
                "type": "compulsory",
                "question_count": 2,
                "marks_per_question": 5,
                "total_section_marks": 10,
                "allowed_levels": ["L3", "L4"],
                "has_internal_choice": False
            },
            {
                "id": "sec_c",
                "name": "Section C - Design & Synthesis",
                "instructions": "Answer with internal choice. (10 Marks)",
                "type": "either_or",
                "question_count": 1,
                "marks_per_question": 10,
                "total_section_marks": 10,
                "allowed_levels": ["L4", "L5", "L6"],
                "has_internal_choice": True
            }
        ]
    }
}
