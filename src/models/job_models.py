"""Data models for structured job information."""
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional

class JobSpec(BaseModel):
    # Basic job and company info
    job_title: Optional[str] = None
    input_url: Optional[str] = None
    uploaded_file: Optional[str] = None
    parsed_data_raw: Optional[str] = None

    company_name: Optional[str] = None
    job_type: Optional[str] = None
    contract_type: Optional[str] = None
    job_level: Optional[str] = None
    city: Optional[str] = None
    headquarters_location: Optional[str] = None
    brand_name: Optional[str] = None
    company_website: Optional[str] = None
    date_of_employment_start: Optional[str] = None
    team_structure: Optional[str] = None

    # Role definition
    role_description: Optional[str] = None
    role_type: Optional[str] = None
    reports_to: Optional[str] = None
    supervises: Optional[str] = None
    role_performance_metrics: Optional[str] = None
    role_priority_projects: Optional[str] = None
    travel_requirements: Optional[str] = None
    work_schedule: Optional[str] = None
    role_keywords: Optional[str] = None
    decision_making_authority: Optional[str] = None

    # Tasks & responsibilities
    task_list: Optional[str] = None
    key_responsibilities: Optional[str] = None
    technical_tasks: Optional[str] = None
    managerial_tasks: Optional[str] = None
    administrative_tasks: Optional[str] = None
    customer_facing_tasks: Optional[str] = None
    internal_reporting_tasks: Optional[str] = None
    performance_tasks: Optional[str] = None
    innovation_tasks: Optional[str] = None
    task_prioritization: Optional[str] = None

    # Skills & competencies
    must_have_skills: Optional[str] = None
    hard_skills: Optional[str] = None
    soft_skills: Optional[str] = None
    nice_to_have_skills: Optional[str] = None
    certifications_required: Optional[str] = None
    language_requirements: Optional[str] = None
    tool_proficiency: Optional[str] = None
    technical_stack: Optional[str] = None
    domain_expertise: Optional[str] = None
    leadership_competencies: Optional[str] = None
    industry_experience: Optional[str] = None
    analytical_skills: Optional[str] = None
    communication_skills: Optional[str] = None
    project_management_skills: Optional[str] = None
    soft_requirement_details: Optional[str] = None
    visa_sponsorship: Optional[str] = None

    # Compensation & benefits
    salary_range: Optional[str] = None
    currency: Optional[str] = None
    pay_frequency: Optional[str] = None
    bonus_scheme: Optional[str] = None
    commission_structure: Optional[str] = None
    vacation_days: Optional[str] = None
    remote_work_policy: Optional[str] = None
    flexible_hours: Optional[str] = None
    relocation_assistance: Optional[str] = None
    childcare_support: Optional[str] = None

    # Recruitment process
    recruitment_contact_email: Optional[str] = None
    recruitment_steps: Optional[str] = None
    recruitment_timeline: Optional[str] = None
    number_of_interviews: Optional[str] = None
    interview_format: Optional[str] = None
    assessment_tests: Optional[str] = None
    onboarding_process_overview: Optional[str] = None
    recruitment_contact_phone: Optional[str] = None
    application_instructions: Optional[str] = None

    # Additional info
    language_of_ad: Optional[str] = None
    translation_required: Optional[str] = None
    ad_seniority_tone: Optional[str] = None
    ad_length_preference: Optional[str] = None
    desired_publication_channels: Optional[str] = None
    employer_branding_elements: Optional[str] = None
    diversity_inclusion_statement: Optional[str] = None
    legal_disclaimers: Optional[str] = None
    company_awards: Optional[str] = None
    social_media_links: Optional[str] = None
    video_introduction_option: Optional[str] = None
    internal_job_id: Optional[str] = None
    deadline_urgency: Optional[str] = None
    comments_internal: Optional[str] = None

    # Generated fields
    generated_job_ad: Optional[str] = None
    generated_interview_prep: Optional[str] = None
    generated_email_template: Optional[str] = None
    target_group_analysis: Optional[str] = None
    generated_boolean_query: Optional[str] = None

