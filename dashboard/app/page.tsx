'use client'

import { useQuery } from '@tanstack/react-query'
import { fetchRoles, fetchStats, fetchScrapeRuns } from '@/lib/api'
import { RoleCard } from '@/components/RoleCard'
import { RoleTable } from '@/components/RoleTable'
import { HotRolesView } from '@/components/HotRolesView'
import { useState, useMemo, useEffect } from 'react'
import {
  CheckCircle,
  Search,
  RefreshCw,
  LayoutGrid,
  List,
  Calendar,
  TrendingUp,
} from 'lucide-react'
import type { Role } from '@/lib/types'
import { useConstants } from '@/lib/context/ConstantsContext'
import { getHighestInvestorTier } from '@/lib/constants'

// Format relative time (e.g., "2 hours ago", "5 mins ago")
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins} min${diffMins === 1 ? '' : 's'} ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`
  if (diffDays < 7) return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`
  return date.toLocaleDateString()
}

const VIEW_MODE_KEY = 'paraform_view_mode'

export type SortOption = 'salary' | 'company' | 'fee' | 'rating' | 'funding' | 'raised' | 'stage' | 'posted' | 'priority' | 'eng_score' | 'hh_score' | 'combined_score' | 'role' | 'investors' | 'industry' | 'tech' | 'founded' | 'yoe' | 'rounds' | 'responsiveness' | 'active' | 'interviewing' | 'hired' | 'recruiters' | 'hiring' | 'location' | 'workplace_type'
export type SortDirection = 'asc' | 'desc'

// Parse funding amount string like "12.5M" or "150M+" to number
const parseFundingAmount = (amount: string | null): number => {
  if (!amount) return 0
  const match = amount.match(/^([\d.]+)/)
  return match ? parseFloat(match[1]) : 0
}

// Parse YOE string to number for sorting
const parseYoe = (yoe: string | null): number => {
  if (!yoe) return 0
  const match = yoe.match(/(\d+)/)
  return match ? parseInt(match[1]) : 0
}

export default function Home() {
  const { constants, loading: constantsLoading } = useConstants()
  const [qualifiedOnly, setQualifiedOnly] = useState(true)  // Default to qualified only
  const [postedAfter, setPostedAfter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('table')
  const [sortBy, setSortBy] = useState<SortOption>('combined_score')  // Default to score
  const [sortDir, setSortDir] = useState<SortDirection>('desc')
  const [showHotRoles, setShowHotRoles] = useState(false)

  // Load view mode preference
  useEffect(() => {
    const storedViewMode = localStorage.getItem(VIEW_MODE_KEY) as 'grid' | 'table' | null
    if (storedViewMode) {
      setViewMode(storedViewMode)
    }
  }, [])

  // Save view mode preference
  useEffect(() => {
    localStorage.setItem(VIEW_MODE_KEY, viewMode)
  }, [viewMode])

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
  })

  // Fetch latest completed scrape run
  const { data: latestScrape } = useQuery({
    queryKey: ['latestScrape'],
    queryFn: () => fetchScrapeRuns(10), // Fetch more to find a completed one
    select: (data) => data.find((run) => run.status === 'completed'), // Get first completed scrape run
  })

  // Fetch roles (all live roles - backend filters by lifecycle_status=ACTIVE)
  const { data: roles, isLoading, refetch } = useQuery({
    queryKey: ['roles'],
    queryFn: () => fetchRoles({ qualified_only: false, page_size: 1000 }),
  })

  // Count qualified roles from actual data (not stats API)
  const qualifiedCount = useMemo(() => {
    if (!roles) return 0
    return roles.filter(role => role.qualification_tier === 'QUALIFIED').length
  }, [roles])

  // Filter and sort roles
  const filteredRoles = useMemo(() => {
    if (!roles) return []

    let filtered: Role[] = roles

    // Filter by qualification status
    if (qualifiedOnly) {
      filtered = filtered.filter(role => role.qualification_tier === 'QUALIFIED')
    }

    // Filter by posted_at date
    if (postedAfter) {
      const afterDate = new Date(postedAfter)
      filtered = filtered.filter(role => {
        const postedDate = new Date(role.posted_at || role.first_seen_at)
        return postedDate >= afterDate
      })
    }

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(role =>
        role.title.toLowerCase().includes(query) ||
        role.company_name.toLowerCase().includes(query) ||
        role.locations.some(loc => loc.toLowerCase().includes(query))
      )
    }

    // Sort roles
    filtered = [...filtered].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1
      switch (sortBy) {
        case 'salary':
          return dir * ((a.salary_upper || 0) - (b.salary_upper || 0))
        case 'company':
          return dir * a.company_name.localeCompare(b.company_name)
        case 'fee':
          return dir * ((a.percent_fee || 0) - (b.percent_fee || 0))
        case 'rating':
          return dir * ((a.manager_rating || 0) - (b.manager_rating || 0))
        case 'funding':
        case 'raised':
          return dir * (parseFundingAmount(a.funding_amount) - parseFundingAmount(b.funding_amount))
        case 'stage':
          return dir * ((a.funding_stage || '').localeCompare(b.funding_stage || ''))
        case 'posted':
          return dir * (new Date(a.posted_at || a.first_seen_at).getTime() - new Date(b.posted_at || b.first_seen_at).getTime())
        case 'priority':
          return dir * ((a.priority || 0) - (b.priority || 0))
        case 'eng_score':
          return dir * ((a.engineer_score || 0) - (b.engineer_score || 0))
        case 'hh_score':
          return dir * ((a.headhunter_score || 0) - (b.headhunter_score || 0))
        case 'combined_score':
          return dir * ((a.combined_score || 0) - (b.combined_score || 0))
        case 'role':
          return dir * (a.role_types[0] || '').localeCompare(b.role_types[0] || '')
        case 'investors':
          if (!constants) return 0
          return dir * (getHighestInvestorTier(a.investors, constants) - getHighestInvestorTier(b.investors, constants))
        case 'industry':
          return dir * (a.industries[0] || '').localeCompare(b.industries[0] || '')
        case 'tech':
          return dir * (a.tech_stack[0] || '').localeCompare(b.tech_stack[0] || '')
        case 'founded':
          return dir * ((a.founding_year || 0) - (b.founding_year || 0))
        case 'yoe':
          return dir * (parseYoe(a.yoe_string) - parseYoe(b.yoe_string))
        case 'rounds':
          return dir * ((a.interview_stages || 0) - (b.interview_stages || 0))
        case 'responsiveness':
          return dir * ((a.responsiveness_days || 0) - (b.responsiveness_days || 0))
        case 'active':
          // Sort by manager_last_active (more recent = higher)
          const aTime = a.manager_last_active ? new Date(a.manager_last_active).getTime() : 0
          const bTime = b.manager_last_active ? new Date(b.manager_last_active).getTime() : 0
          return dir * (aTime - bTime)
        case 'interviewing':
          return dir * ((a.total_interviewing || 0) - (b.total_interviewing || 0))
        case 'hired':
          return dir * ((a.total_hired || 0) - (b.total_hired || 0))
        case 'recruiters':
          return dir * ((a.approved_recruiters_count || 0) - (b.approved_recruiters_count || 0))
        case 'hiring':
          return dir * ((a.hiring_count || 1) - (b.hiring_count || 1))
        case 'location':
          const aLoc = a.locations[0] || ''
          const bLoc = b.locations[0] || ''
          return dir * aLoc.localeCompare(bLoc)
        case 'workplace_type':
          const aWork = a.workplace_type || 'On-site'
          const bWork = b.workplace_type || 'On-site'
          return dir * aWork.localeCompare(bWork)
        default:
          return 0
      }
    })

    return filtered
  }, [roles, qualifiedOnly, postedAfter, searchQuery, sortBy, sortDir])

  // Handle column header click for sorting
  const handleSort = (column: SortOption) => {
    if (sortBy === column) {
      setSortDir(prev => prev === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(column)
      setSortDir('desc')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Compact Header with integrated filters */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-screen-2xl mx-auto px-3 py-2">
          {/* Single row: Title + Qualified toggle + Date Filter + Search + View Toggle + Refresh */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Title & Stats */}
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-gray-900">Paraform Roles</h1>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                {stats && (
                  <span>{stats.total_roles} total</span>
                )}
                {latestScrape?.completed_at && (
                  <>
                    <span className="text-gray-300">•</span>
                    <span title={`Last scraped: ${new Date(latestScrape.completed_at).toLocaleString()}`}>
                      scraped {formatRelativeTime(latestScrape.completed_at)}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Qualified Toggle Pill */}
            <button
              onClick={() => setQualifiedOnly(!qualifiedOnly)}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all ${
                qualifiedOnly ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <CheckCircle className="w-3 h-3" />
              Qualified
              <span className={`px-1 rounded text-[10px] ${qualifiedOnly ? 'bg-white/20' : 'bg-gray-200'}`}>
                {qualifiedCount}
              </span>
            </button>

            {/* Hot Roles Toggle */}
            <button
              onClick={() => setShowHotRoles(!showHotRoles)}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-all ${
                showHotRoles ? 'bg-orange-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
              title="Show roles with surging interview activity"
            >
              <TrendingUp className="w-3 h-3" />
              Hot Roles
            </button>

            {/* Posted After Date Filter */}
            <div className="flex items-center gap-2 border-l border-gray-200 pl-3">
              <div className="relative flex items-center">
                <Calendar className="absolute left-2 w-3 h-3 text-gray-400" />
                <input
                  type="date"
                  value={postedAfter}
                  onChange={(e) => setPostedAfter(e.target.value)}
                  className="pl-6 pr-2 py-1 text-xs border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500 w-32"
                  title="Filter roles posted after this date"
                />
                {postedAfter && (
                  <button
                    onClick={() => setPostedAfter('')}
                    className="ml-1 text-gray-400 hover:text-gray-600 text-xs"
                    title="Clear date filter"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>

            {/* Search - compact */}
            <div className="relative flex-1 min-w-[120px] max-w-[200px]">
              <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-3 h-3 text-gray-400" />
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-6 pr-2 py-1 text-xs border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* View Toggle - compact */}
            <div className="flex gap-0.5 bg-gray-100 rounded p-0.5">
              <button
                onClick={() => setViewMode('table')}
                className={`p-1 rounded ${viewMode === 'table' ? 'bg-white shadow-sm' : 'text-gray-500'}`}
                title="Table view"
              >
                <List className="w-3 h-3" />
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1 rounded ${viewMode === 'grid' ? 'bg-white shadow-sm' : 'text-gray-500'}`}
                title="Card view"
              >
                <LayoutGrid className="w-3 h-3" />
              </button>
            </div>

            {/* Refresh */}
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-1 px-2 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-xs"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-screen-2xl mx-auto px-3 py-2">
        {/* Conditionally render Hot Roles view or normal filtered view */}
        {showHotRoles ? (
          <HotRolesView />
        ) : (
          <>
            {/* Results count */}
            <div className="text-xs text-gray-600 mb-2">
              Showing {filteredRoles.length} {qualifiedOnly ? 'qualified' : 'live'} roles
              {postedAfter && ` posted after ${postedAfter}`}
              {searchQuery && ` matching "${searchQuery}"`}
            </div>

            {/* Main Content */}
            {isLoading ? (
              <div className="text-center py-12">
                <RefreshCw className="w-8 h-8 text-gray-400 animate-spin mx-auto mb-4" />
                <p className="text-gray-600">Loading roles...</p>
              </div>
            ) : filteredRoles.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <p className="text-gray-600">
                  {searchQuery
                    ? `No roles found matching "${searchQuery}"`
                    : 'No roles found with selected filters'}
                </p>
              </div>
            ) : viewMode === 'table' ? (
              <RoleTable
                roles={filteredRoles}
                sortBy={sortBy}
                sortDir={sortDir}
                onSort={handleSort}
              />
            ) : (
              <div className="space-y-4">
                {filteredRoles.map((role) => (
                  <RoleCard key={role.id} role={role} isNew={false} />
                ))}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
