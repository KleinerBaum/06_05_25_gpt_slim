import streamlit as st

# Alle Keys nach Wizard‑Schritt
KEYS = {
    "step1": [
        "job_title", "input_url", "uploaded_text", "parsed_data_raw", "source_language"
    ],
    "step2": [
        "company_name", "brand_name", "headquarters_location", "city", "company_website",
        "company_size", "industry_sector", "job_type", "contract_type", "job_level",
        "team_structure", "date_of_employment_start"
    ],
    "step3": [
        "role_description", "reports_to", "supervises", "role_type",
        "role_performance_metrics", "role_priority_projects", "travel_requirements",
        "work_schedule", "decision_making_authority", "role_keywords"
    ],
    "step4": [
        "task_list", "key_responsibilities", "technical_tasks", "managerial_tasks",
        "administrative_tasks", "customer_facing_tasks", "internal_reporting_tasks",
        "performance_tasks", "innovation_tasks", "task_prioritization"
    ],
    "step5": [
        "must_have_skills", "hard_skills", "nice_to_have_skills", "soft_skills",
        "language_requirements", "tool_proficiency", "technical_stack", "domain_expertise",
        "leadership_competencies", "certifications_required", "industry_experience",
        "analytical_skills", "communication_skills", "project_management_skills",
        "soft_requirement_details", "visa_sponsorship"
    ],
    "step6": [
        "salary_range", "currency", "pay_frequency", "bonus_scheme",
        "commission_structure", "vacation_days", "remote_work_policy", "flexible_hours",
        "relocation_assistance", "childcare_support", "travel_requirements_link"
    ],
    "step7": [
        "recruitment_steps", "number_of_interviews", "assessment_tests", "interview_format",
        "recruitment_timeline", "onboarding_process_overview", "recruitment_contact_email",
        "recruitment_contact_phone", "application_instructions"
    ],
    "step8": [
        "ad_seniority_tone", "ad_length_preference", "language_of_ad", "translation_required",
        "desired_publication_channels", "employer_branding_elements", "diversity_inclusion_statement",
        "legal_disclaimers", "company_awards", "social_media_links", "video_introduction_option",
        "internal_job_id", "deadline_urgency", "comments_internal"
    ],
}

ALL_KEYS = [k for group in KEYS.values() for k in group]


# utils/session_keys.py
def init_session_state():
    if st.session_state.get("_session_keys_initialized_"):
        return
    for key in ALL_KEYS:
        st.session_state.setdefault(key, None)
    st.session_state["_session_keys_initialized_"] = True

