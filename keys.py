# keys.py
# ─────────────────────────────────────────────────────────────────────────────
"""Canonical list of wizard fields grouped by step (★ mandatory, ◆ recommended, ⬚ optional)."""

STEP_KEYS: dict[int, list[str]] = {
    1: [  # Step 1: Discovery
        "job_title",            # ★
        "input_url",           # ⬚
        "uploaded_file",       # ⬚
        "parsed_data_raw"      # ⬚ (internal raw text storage)
    ],
    2: [  # Step 2: Basic Job & Company Info
        "company_name",        # ★
        "job_type",            # ★
        "contract_type",       # ★
        "job_level",           # ★
        "city",                # ★
        "headquarters_location", # ◆
        "brand_name",          # ⬚
        "company_website",     # ⬚
        "date_of_employment_start",  # ⬚
        "team_structure"       # ⬚
    ],
    3: [  # Step 3: Role Definition
        "role_description",    # ★
        "role_type",           # ★
        "reports_to",          # ◆
        "supervises",          # ◆
        "role_performance_metrics",    # ⬚
        "role_priority_projects",    # ⬚
        "travel_requirements", # ⬚
        "work_schedule",       # ⬚
        "role_keywords",       # ⬚
        "decision_making_authority"  # ⬚
    ],
    4: [  # Step 4: Tasks & Responsibilities
        "task_list",                 # ★
        "key_responsibilities",      # ◆
        "technical_tasks",           # ⬚
        "managerial_tasks",          # ⬚
        "administrative_tasks",      # ⬚
        "customer_facing_tasks",     # ⬚
        "internal_reporting_tasks",  # ⬚
        "performance_tasks",         # ⬚
        "innovation_tasks",          # ⬚
        "task_prioritization"        # ⬚
    ],
    5: [  # Step 5: Skills & Competencies
        "must_have_skills",         # ★
        "hard_skills",              # ◆
        "soft_skills",              # ◆
        "nice_to_have_skills",      # ⬚
        "certifications_required",  # ⬚
        "language_requirements",    # ⬚
        "tool_proficiency",         # ⬚
        "technical_stack",          # ⬚
        "domain_expertise",         # ⬚
        "leadership_competencies",  # ⬚
        "industry_experience",      # ⬚
        "analytical_skills",        # ⬚
        "communication_skills",     # ⬚
        "project_management_skills",# ⬚
        "soft_requirement_details", # ⬚
        "visa_sponsorship"          # ⬚
    ],
    6: [  # Step 6: Compensation & Benefits
        "salary_range",            # ★
        "currency",                # ★
        "pay_frequency",           # ★
        "bonus_scheme",            # ◆
        "commission_structure",    # ◆
        "vacation_days",           # ◆
        "remote_work_policy",      # ◆
        "flexible_hours",          # ◆
        "relocation_assistance",   # ⬚
        "childcare_support"        # ⬚
    ],
    7: [  # Step 7: Recruitment Process
        "recruitment_contact_email",   # ★
        "recruitment_steps",           # ◆
        "recruitment_timeline",        # ⬚
        "number_of_interviews",        # ⬚
        "interview_format",            # ⬚
        "assessment_tests",            # ⬚
        "onboarding_process_overview", # ⬚
        "recruitment_contact_phone",   # ⬚
        "application_instructions"     # ⬚
    ],
    8: [  # Step 8: Additional Information & Summary
        "language_of_ad",              # ★
        "translation_required",        # ◆
        "ad_seniority_tone",           # ⬚
        "ad_length_preference",        # ⬚
        "desired_publication_channels",# ⬚
        "employer_branding_elements",  # ⬚
        "diversity_inclusion_statement", # ⬚
        "legal_disclaimers",           # ⬚
        "company_awards",              # ⬚
        "social_media_links",          # ⬚
        "video_introduction_option",   # ⬚
        "internal_job_id",             # ⬚
        "deadline_urgency",            # ⬚
        "comments_internal"            # ⬚
    ],
}

# Fields generated or used internally (not shown in UI steps)
GENERATED_KEYS: list[str] = [
    "generated_job_ad",
    "generated_interview_prep",
    "generated_email_template",
    "target_group_analysis",
    "generated_boolean_query",
]
