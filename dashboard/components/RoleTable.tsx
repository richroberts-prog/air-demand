'use client'

import { Role } from '@/lib/types'
import { Sparkles, ArrowUp, ArrowDown, ArrowUpDown, Star } from 'lucide-react'
import type { SortOption, SortDirection } from '@/app/page'
import { useConstants } from '@/lib/context/ConstantsContext'
import { getInvestorTier, getInvestorShortName } from '@/lib/constants'

interface RoleTableProps {
  roles: Role[]
  isNew?: (role: Role) => boolean
  sortBy?: SortOption
  sortDir?: SortDirection
  onSort?: (column: SortOption) => void
}

export function RoleTable({ roles, isNew, sortBy, sortDir, onSort }: RoleTableProps) {
  const { constants, loading } = useConstants()

  // Get tiered investors sorted by tier (best first)
  const getTieredInvestors = (investors: string[]) => {
    if (!constants) return []
    return investors
      .map(inv => ({ name: inv, tier: getInvestorTier(inv, constants) }))
      .filter(x => x.tier > 0)
      .sort((a, b) => a.tier - b.tier) // Tier 1 first
      .slice(0, 1) // Max 1 shown (highest rated only)
      .map(x => ({
        name: getInvestorShortName(x.name) || x.name,
        tier: x.tier
      }))
  }

  // Tier colors
  const tierColors: Record<number, string> = {
    1: 'bg-green-100 text-green-800 font-semibold', // Elite - green
    2: 'bg-blue-100 text-blue-700',                  // Premier - blue
    3: 'bg-gray-100 text-gray-600',                  // Strong - gray
  }

  // Sortable header component
  const SortableHeader = ({ column, label, align = 'left', title }: { column: SortOption; label: string; align?: 'left' | 'right' | 'center'; title?: string }) => {
    const isActive = sortBy === column
    const Icon = isActive ? (sortDir === 'desc' ? ArrowDown : ArrowUp) : ArrowUpDown
    return (
      <th
        className={`px-1.5 py-1.5 text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors select-none ${
          align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
        }`}
        onClick={() => onSort?.(column)}
        title={title}
      >
        <span className={`inline-flex items-center gap-0.5 ${align === 'right' ? 'flex-row-reverse' : ''}`}>
          {label}
          <Icon className={`w-3 h-3 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
        </span>
      </th>
    )
  }

  // Format tech stack names to shortened versions for compact display
  const formatTechName = (tech: string): string => {
    const techMap: Record<string, string> = {
      'Python': 'py',
      'python': 'py',
      'TypeScript': 'TS',
      'typescript': 'TS',
      'JavaScript': 'JS',
      'javascript': 'JS',
      'PostgreSQL': 'Postgres',
      'postgresql': 'Postgres',
      'Kubernetes': 'K8s',
      'kubernetes': 'K8s',
      'TensorFlow': 'TF',
      'tensorflow': 'TF',
      'GraphQL': 'GQL',
      'graphql': 'GQL',
      'Node.js': 'Node',
      'MongoDB': 'Mongo',
      'mongodb': 'Mongo',
      'Next.js': 'Next',
      'React.js': 'React',
      'Vue.js': 'Vue',
      'Angular.js': 'Angular',
    }
    return techMap[tech] || tech
  }

  const formatLocation = (role: Role) => {
    // Normalize snake_case to title case: "new_york" -> "New York"
    const normalizeLocation = (loc: string): string => {
      return loc
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
    }

    // City shorthand mapping (handles both snake_case API and title case extracted)
    const cityShorthand: Record<string, string> = {
      'New York': 'NYC',
      'new_york': 'NYC',
      'San Francisco': 'SF',
      'san_francisco': 'SF',
      'Los Angeles': 'LA',
      'los_angeles': 'LA',
      'Washington': 'DC',
      'washington': 'DC',
      'Boston': 'BOS',
      'boston': 'BOS',
      'Austin': 'AUS',
      'austin': 'AUS',
      'Seattle': 'SEA',
      'seattle': 'SEA',
      'Chicago': 'CHI',
      'chicago': 'CHI',
      'Denver': 'DEN',
      'denver': 'DEN',
      'Portland': 'PDX',
      'portland': 'PDX',
      'Miami': 'MIA',
      'miami': 'MIA',
      'Atlanta': 'ATL',
      'atlanta': 'ATL',
      'London': 'LON',
      'london': 'LON',
      'Bay Area': 'Bay',
      'bay_area': 'Bay',
      'South Bay Area': 'Bay',
      'south_bay_area': 'Bay',
      'Remote': 'Rem',
      'remote': 'Rem',
    }

    // Priority 1: Extracted location (high confidence)
    if (role.extracted_location && role.location_confidence === 'high') {
      return cityShorthand[role.extracted_location] || role.extracted_location
    }

    // Priority 2: Extracted location (medium/low confidence)
    if (role.extracted_location) {
      return cityShorthand[role.extracted_location] || role.extracted_location
    }

    // Priority 3: First location from API array
    if (role.locations && role.locations.length > 0) {
      const firstLoc = role.locations[0]
      const shorthand = cityShorthand[firstLoc]
      if (shorthand) return shorthand

      // Fallback: normalize and shorten
      const normalized = normalizeLocation(firstLoc)
      return cityShorthand[normalized] || normalized.substring(0, 6)
    }

    return '—'
  }

  const formatWorkplaceType = (role: Role) => {
    if (role.workplace_type) {
      // Shorten workplace types
      const typeMap: Record<string, string> = {
        'Remote': 'Rem',
        'Hybrid': 'Hyb',
        'On-site': 'On-site',
        'Onsite': 'On-site',
      }
      return typeMap[role.workplace_type] || role.workplace_type
    }
    return '—'
  }

  const getLocationTooltip = (role: Role) => {
    const parts: string[] = []

    // Normalize snake_case for display
    const normalizeForDisplay = (loc: string): string => {
      return loc
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
    }

    // Show extracted location with confidence
    if (role.extracted_location) {
      const confidence = role.location_confidence
      const badge = confidence === 'high' ? '✓' : confidence === 'medium' ? '~' : '?'
      parts.push(`${badge} ${role.extracted_location}`)
    }

    // Show API locations (normalized)
    if (role.locations && role.locations.length > 0) {
      const normalized = role.locations.map(normalizeForDisplay)
      parts.push(`📍 ${normalized.join(', ')}`)
    }

    // Show workplace type
    if (role.workplace_type) {
      parts.push(`🏢 ${role.workplace_type}`)
    }

    return parts.join('\n') || 'No location data'
  }

  const formatResponsiveness = (days: number | null) => {
    if (days === null || days === undefined) return '—'
    if (days < 1) return '<1d'
    return `${Math.round(days)}d`
  }

  const formatManagerActive = (dateStr: string | null) => {
    if (!dateStr) return '—'
    const date = new Date(dateStr)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return '1d'
    if (diffDays < 7) return `${diffDays}d`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w`
    return `${Math.floor(diffDays / 30)}mo`
  }

  const isManagerStale = (dateStr: string | null) => {
    if (!dateStr) return true
    const date = new Date(dateStr)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
    return diffDays > 7
  }

  // Score formatting and styling
  const formatScore = (score: number | null): string => {
    if (score === null || score === undefined) return '—'
    return Math.round(score * 100).toString()
  }

  const getScoreStyle = (score: number | null): { textClass: string; bgClass: string; showStar: boolean } => {
    if (score === null || score === undefined) {
      return { textClass: 'text-gray-400', bgClass: '', showStar: false }
    }
    if (score >= 0.85) {
      return { textClass: 'text-green-700 font-semibold', bgClass: 'bg-green-100', showStar: true }
    }
    if (score >= 0.70) {
      return { textClass: 'text-blue-700 font-medium', bgClass: 'bg-blue-50', showStar: false }
    }
    if (score >= 0.55) {
      return { textClass: 'text-gray-600', bgClass: '', showStar: false }
    }
    return { textClass: 'text-red-500 opacity-75', bgClass: '', showStar: false }
  }

  // Format qualification tooltip
  const formatQualificationTooltip = (role: Role): string => {
    const parts: string[] = []

    // Add tier
    parts.push(`Tier: ${role.qualification_tier || 'SKIP'}`)

    // Add score
    if (role.combined_score !== null) {
      parts.push(`Score: ${Math.round(role.combined_score * 100)}`)
    }

    // Add qualification reasons for QUALIFIED/MAYBE
    if (role.qualification_reasons && role.qualification_reasons.length > 0) {
      parts.push('')
      parts.push('✓ Qualified because:')
      role.qualification_reasons.forEach(reason => {
        parts.push(`  • ${reason}`)
      })
    }

    // Add disqualification reasons for SKIP
    if (role.disqualification_reasons && role.disqualification_reasons.length > 0) {
      parts.push('')
      parts.push('✗ Disqualified because:')
      role.disqualification_reasons.forEach(reason => {
        parts.push(`  • ${reason}`)
      })
    }

    return parts.join('\n')
  }

  // Score cell component for consistent rendering
  const ScoreCell = ({ score, label, role }: { score: number | null; label: string; role?: Role }) => {
    const style = getScoreStyle(score)
    const tooltip = role ? formatQualificationTooltip(role) : `${label}: ${score !== null ? (score * 100).toFixed(1) : 'N/A'}%`

    return (
      <td className={`px-1.5 py-1 text-center ${style.bgClass}`}>
        <span
          className={`text-xs inline-flex items-center gap-0.5 ${style.textClass} ${role ? 'cursor-help' : ''}`}
          title={tooltip}
        >
          {style.showStar && <Star className="w-3 h-3 fill-current" />}
          {score != null ? Math.round(score * 100).toString() : "—"}
        </span>
      </td>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto max-h-[calc(100vh-100px)] overflow-y-auto">
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
          <tr>
            {/* Identity */}
            <SortableHeader column="combined_score" label="Score" align="center" title="Combined Score (0-100)" />
            <SortableHeader column="company" label="Company" />
            <SortableHeader column="role" label="Role" title="Role Type" />
            <SortableHeader column="posted" label="Posted" />
            <SortableHeader column="location" label="Loc" align="left" title="Primary Location (hover for details)" />
            <SortableHeader column="workplace_type" label="Type" align="center" title="Workplace Type (Remote/Hybrid/On-site)" />
            {/* Money */}
            <SortableHeader column="salary" label="$K" align="right" title="Salary $K" />
            <SortableHeader column="fee" label="Fee %" align="right" />
            <SortableHeader column="hiring" label="Tot" align="center" title="Total positions to fill (shows scale/ambition)" />
            <th className="px-1.5 py-1.5 text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 text-center" title="Remaining open positions after hires">Rem</th>
            {/* Funding */}
            <SortableHeader column="raised" label="$M" align="right" title="Raised $M" />
            <SortableHeader column="investors" label="VCs" title="Tier 1 Investors" />
            <SortableHeader column="stage" label="Stage" />
            {/* Role Details */}
            <SortableHeader column="tech" label="Tech" title="Tech Stack" />
            <SortableHeader column="industry" label="IND" title="Primary Industry" />
            <SortableHeader column="yoe" label="YOE" align="center" title="Years of Experience" />
            {/* Scores */}
            <SortableHeader column="eng_score" label="Eng" align="center" title="Engineer Attractiveness Score" />
            <SortableHeader column="hh_score" label="HH" align="center" title="Headhunter Score" />
            {/* Process */}
            <SortableHeader column="rating" label="★" align="center" title="Manager Rating" />
            <SortableHeader column="active" label="Active" align="center" title="Manager Last Active" />
            <SortableHeader column="responsiveness" label="Resp" align="center" title="Response Time (days)" />
            <SortableHeader column="rounds" label="Rnds" align="center" title="Interview Stages" />
            <SortableHeader column="interviewing" label="Intv" align="center" title="Total Interviewing" />
            <SortableHeader column="hired" label="Hire" align="center" title="Total Hired" />
            <th className="px-1.5 py-1.5 text-xs font-semibold text-gray-700 uppercase tracking-wider bg-gray-50 text-center" title="Interview Pipeline Trend">
              Trend
            </th>
            {/* Metadata */}
            <SortableHeader column="founded" label="Est." align="center" title="Year Founded" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {roles.map((role) => {
            const showNew = isNew && isNew(role)
            const stale = isManagerStale(role.manager_last_active)

            return (
              <tr key={role.id} className={`hover:bg-gray-50 transition-colors ${stale ? 'opacity-60' : ''}`}>
                {/* IDENTITY */}
                {/* 1. Score */}
                <ScoreCell score={role.combined_score} label="Combined Score" role={role} />

                {/* 2. Company */}
                <td className="px-1.5 py-1">
                  <div className="flex items-center gap-1.5" title={role.one_liner || role.company_name}>
                    {role.company_logo_url && (
                      <img
                        src={role.company_logo_url}
                        alt={role.company_name}
                        className="w-5 h-5 rounded object-contain bg-gray-50 flex-shrink-0"
                      />
                    )}
                    <span className="text-xs font-medium text-gray-900 truncate max-w-[100px] cursor-help">{role.company_name}</span>
                  </div>
                </td>

                {/* 3. Role */}
                <td className="px-1.5 py-1 whitespace-nowrap">
                  <div className="flex items-center gap-1">
                    <a
                      href={role.paraform_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {role.qualifying_core_type ? role.role_type_display : role.role_type_display}
                    </a>
                    {showNew && (
                      <span className="inline-flex items-center gap-0.5 bg-blue-600 text-white px-1 py-0.5 rounded text-[9px] font-bold flex-shrink-0">
                        <Sparkles className="w-2 h-2" />
                        NEW
                      </span>
                    )}
                  </div>
                </td>

                {/* 4. Posted */}
                <td className="px-1.5 py-1 whitespace-nowrap">
                  <span className="text-xs text-gray-600">{role.posted_at_display}</span>
                </td>

                {/* 5. Location */}
                <td className="px-1.5 py-1">
                  <span
                    className="text-xs text-gray-600 cursor-help"
                    title={getLocationTooltip(role)}
                  >
                    {role.location_display}
                  </span>
                </td>

                {/* 6. Workplace Type */}
                <td className="px-1.5 py-1 text-center">
                  <span className="text-xs text-gray-600">
                    {role.workplace_display}
                  </span>
                </td>

                {/* MONEY */}
                {/* 7. Salary */}
                <td className="px-1.5 py-1 text-right">
                  <span className="text-xs font-medium text-gray-900 whitespace-nowrap">{role.salary_display}</span>
                </td>

                {/* 6. Fee */}
                <td className="px-1.5 py-1 text-right">
                  <span className="text-xs font-medium text-gray-900">
                    {role.percent_fee_display}
                  </span>
                </td>

                {/* 7. Hiring Count (Total) */}
                <td className="px-1.5 py-1 text-center">
                  <span className={`text-xs font-semibold ${role.hiring_count && role.hiring_count >= 3 ? 'text-green-600' : 'text-gray-700'}`}>
                    {role.hiring_count_display}
                  </span>
                </td>

                {/* 8. Remaining Positions */}
                <td className="px-1.5 py-1 text-center">
                  <span className="text-xs text-gray-700">
                    {role.remaining_positions_display}
                  </span>
                </td>

                {/* FUNDING */}
                {/* 9. Raised */}
                <td className="px-1.5 py-1 text-right whitespace-nowrap">
                  <span className="text-xs font-medium text-gray-900">{role.funding_display}</span>
                </td>

                {/* 10. Investors */}
                <td className="px-1.5 py-1">
                  {(() => {
                    const tiered = getTieredInvestors(role.investors)
                    if (tiered.length === 0) return <span className="text-[10px] text-gray-400">—</span>
                    return (
                      <div className="flex flex-wrap gap-0.5" title={role.investors.join(', ')}>
                        {tiered.map((inv, i) => (
                          <span key={i} className={`px-1 py-0 rounded text-[9px] ${tierColors[inv.tier]}`}>
                            {inv.name}
                          </span>
                        ))}
                      </div>
                    )
                  })()}
                </td>

                {/* 10. Stage */}
                <td className="px-1.5 py-1 whitespace-nowrap">
                  <span className="text-xs text-gray-600">{role.funding_stage_display}</span>
                </td>

                {/* ROLE DETAILS */}
                {/* 11. Tech */}
                <td className="px-1.5 py-1 min-w-[120px]">
                  <div className="flex flex-wrap gap-0.5">
                    {role.tech_stack.slice(0, 4).map((tech, i) => (
                      <span key={i} className="px-1 py-0 rounded text-[9px] bg-slate-100 text-slate-600" title={tech}>
                        {formatTechName(tech)}
                      </span>
                    ))}
                    {role.tech_stack.length > 4 && (
                      <span className="text-[9px] text-gray-400">+{role.tech_stack.length - 4}</span>
                    )}
                  </div>
                </td>

                {/* 12. Industry */}
                <td className="px-1.5 py-1">
                  <span className="text-xs text-gray-600" title={role.industries?.join(', ') || ''}>
                    {role.industry || '—'}
                  </span>
                </td>

                {/* 13. YOE */}
                <td className="px-1.5 py-1 text-center">
                  <span className="text-[10px] text-gray-600">{role.yoe_display}</span>
                </td>

                {/* SCORES */}
                {/* 14-15. Eng/HH */}
                <ScoreCell score={role.engineer_score} label="Engineer Score" />
                <ScoreCell score={role.headhunter_score} label="Headhunter Score" />

                {/* PROCESS */}
                {/* 16. Manager Rating */}
                <td className="px-1.5 py-1 text-center">
                  <span className="text-xs text-gray-700">
                    {role.manager_rating ? `${role.manager_rating.toFixed(1)}` : '—'}
                  </span>
                </td>

                {/* 17. Manager Last Active */}
                <td className="px-1.5 py-1 text-center">
                  <span className={`text-xs ${stale ? 'text-red-500 font-medium' : 'text-gray-600'}`}>
                    {role.manager_active_display}
                  </span>
                </td>

                {/* 18. Responsiveness */}
                <td className="px-1.5 py-1 text-center">
                  <span className={`text-xs ${role.responsiveness_days && role.responsiveness_days < 2 ? 'text-green-600' : role.responsiveness_days && role.responsiveness_days > 5 ? 'text-red-500' : 'text-gray-600'}`}>
                    {role.responsiveness_days ? `${role.responsiveness_days.toFixed(1)}d` : "—"}
                  </span>
                </td>

                {/* 19. Interview Stages */}
                <td className="px-1.5 py-1 text-center">
                  <span className="text-xs text-gray-600">{role.interview_stages || '—'}</span>
                </td>

                {/* 20. Total Interviewing */}
                <td className="px-1.5 py-1 text-center">
                  <span className="text-xs text-gray-600">{role.total_interviewing ?? '—'}</span>
                </td>

                {/* 21. Total Hired */}
                <td className="px-1.5 py-1 text-center">
                  <span className={`text-xs ${role.total_hired && role.total_hired > 0 ? 'text-green-600 font-medium' : 'text-gray-600'}`}>
                    {role.total_hired ?? '—'}
                  </span>
                </td>

                {/* 22. Trend */}
                <td className="px-1.5 py-1 text-center">
                  {role.trend === 'surging' && (
                    <span className="text-orange-500" title="Interview activity surging">🔥</span>
                  )}
                  {role.trend === 'stalled' && (
                    <span className="text-red-500" title="Interviews stalled">⚠️</span>
                  )}
                  {role.trend === 'hired' && (
                    <span className="text-green-600" title="Recently hired">✅</span>
                  )}
                  {!role.trend && (
                    <span className="text-gray-400">—</span>
                  )}
                </td>

                {/* METADATA */}
                {/* 23. Founded Year */}
                <td className="px-1.5 py-1 text-center whitespace-nowrap">
                  <span className="text-xs text-gray-600">{role.founding_year || '—'}</span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
