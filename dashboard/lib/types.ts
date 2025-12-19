// v0.1 Types - matches new JSONB-based schema

export interface Role {
  id: number
  paraform_id: string
  qualification_tier: TierType | null
  qualification_reasons: string[]
  disqualification_reasons: string[]
  first_seen_at: string

  // Raw values (for backward compatibility)
  title: string
  company_name: string
  company_logo_url: string | null
  salary_lower: number | null
  salary_upper: number | null
  salary_string: string | null
  locations: string[]
  workplace_type: string | null
  role_types: string[]
  qualifying_core_type: string | null
  tech_stack: string[]
  hiring_count: number | null
  percent_fee: number | null
  manager_rating: number | null
  investors: string[]
  highlights: string[]
  funding_amount: string | null
  funding_stage: string | null
  company_size: number | null
  paraform_url: string
  total_interviewing: number | null
  total_hired: number | null
  interview_stages: number | null
  responsiveness_days: number | null
  manager_last_active: string | null
  approved_recruiters_count: number | null
  yoe_string: string | null
  one_liner: string | null
  priority: number | null
  posted_at: string | null
  industries: string[]
  industry: string
  founding_year: number | null
  engineer_score: number | null
  headhunter_score: number | null
  excitement_score: number | null
  combined_score: number | null
  has_briefing: boolean
  trend?: string | null
  extracted_location?: string | null
  location_confidence?: string | null

  // Formatted display fields (rendered by backend, single source of truth)
  salary_display: string  // "225"
  funding_display: string  // "11" (integer millions)
  funding_stage_display: string  // "A", "Seed"
  role_type_display: string  // "Backend", "Full Stack"
  location_display: string  // "NYC", "SF", "Remote"
  workplace_display: string  // "Remote", "Hybrid", "On-site"
  yoe_display: string  // "3-7", "5+"
  posted_at_display: string  // "12-09" (MM-DD)
  hiring_count_display: string  // "5", "100" (total positions)
  remaining_positions_display: string  // "5", "83" (after hires)
  percent_fee_display: string  // "15.5"
  engineer_score_display: string  // "85"
  headhunter_score_display: string  // "92"
  excitement_score_display: string  // "78"
  combined_score_display: string  // "85"
  manager_active_display: string  // "Today", "1d", "3d", "2w", "3mo"
}

export interface ScoreBreakdown {
  engineer: {
    score: number
    breakdown: Record<string, number>
    signals: string[]
  }
  headhunter: {
    score: number
    breakdown: Record<string, number>
    signals: string[]
  }
  excitement: {
    score: number
    signals: string[]
  }
}

export interface RoleDetail extends Role {
  equity: string | null
  visa_text: string | null
  company_website: string | null
  score_breakdown: ScoreBreakdown | null
  raw_response: Record<string, any>
}

export interface RoleListResponse {
  roles: Role[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface RoleStats {
  total_roles: number
  qualified_count: number
  maybe_count: number
  skip_count: number
  qualified_percentage: number
}

export interface ScrapeRun {
  id: number
  run_id: string
  status: string
  roles_found: number
  new_roles: number
  updated_roles: number
  qualified_roles: number
  errors: string[]
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
  triggered_by: string | null
  created_at: string
  updated_at: string
}

export type TierType = 'QUALIFIED' | 'MAYBE' | 'SKIP'

// Temporal tracking types

export interface RoleChange {
  id: number
  role_id: number
  role_title: string
  company_name: string
  change_type: string
  field_name: string
  old_value: string | null
  new_value: string | null
  detected_at: string
}

export interface NewRolesResponse {
  roles: Role[]
  count: number
  since: string
}

export type ChangeType =
  | 'SALARY_INCREASE'
  | 'SALARY_DECREASE'
  | 'FEE_CHANGE'
  | 'HEADCOUNT_CHANGE'
  | 'LOCATION_CHANGE'
  | 'STATUS_CHANGE'
  | 'COMPETITION_CHANGE'
  | 'REAPPEARED'
  | 'DISAPPEARED'

// User settings
export interface LastVisitResponse {
  last_visit: string | null
  updated_at: string | null
}
