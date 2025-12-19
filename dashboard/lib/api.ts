import { Role, RoleChange, RoleDetail, RoleListResponse, RoleStats, ScrapeRun, NewRolesResponse, LastVisitResponse } from './types'

// In production, NEXT_PUBLIC_API_URL points to the API directly
// In development, fall back to relative /api which uses Next.js proxy
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api'

export interface FetchRolesParams {
  tier?: string
  qualified_only?: boolean
  search?: string
  min_salary?: number
  page?: number
  page_size?: number
}

export async function fetchRoles(params?: FetchRolesParams): Promise<Role[]> {
  const queryParams = new URLSearchParams()

  if (params?.tier) queryParams.set('tier', params.tier)
  if (params?.qualified_only !== undefined) queryParams.set('qualified_only', String(params.qualified_only))
  if (params?.search) queryParams.set('search', params.search)
  if (params?.min_salary) queryParams.set('min_salary', String(params.min_salary))
  if (params?.page) queryParams.set('page', String(params.page))
  if (params?.page_size) queryParams.set('page_size', String(params.page_size))

  const queryString = queryParams.toString()
  const url = `${API_BASE}/jobs/roles${queryString ? `?${queryString}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to fetch roles: ${response.statusText}`)
  }

  const data: RoleListResponse = await response.json()
  return data.roles
}

export async function fetchRolesWithPagination(params?: FetchRolesParams): Promise<RoleListResponse> {
  const queryParams = new URLSearchParams()

  if (params?.tier) queryParams.set('tier', params.tier)
  if (params?.qualified_only !== undefined) queryParams.set('qualified_only', String(params.qualified_only))
  if (params?.search) queryParams.set('search', params.search)
  if (params?.min_salary) queryParams.set('min_salary', String(params.min_salary))
  if (params?.page) queryParams.set('page', String(params.page))
  if (params?.page_size) queryParams.set('page_size', String(params.page_size))

  const queryString = queryParams.toString()
  const url = `${API_BASE}/jobs/roles${queryString ? `?${queryString}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to fetch roles: ${response.statusText}`)
  }

  return response.json()
}

export async function fetchRole(id: number): Promise<RoleDetail> {
  const response = await fetch(`${API_BASE}/jobs/roles/${id}`)

  if (!response.ok) {
    throw new Error(`Failed to fetch role: ${response.statusText}`)
  }

  return response.json()
}

export async function fetchStats(): Promise<RoleStats> {
  const response = await fetch(`${API_BASE}/jobs/stats`)

  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.statusText}`)
  }

  return response.json()
}

export async function fetchScrapeRuns(limit: number = 10): Promise<ScrapeRun[]> {
  const response = await fetch(`${API_BASE}/jobs/scrape-runs?limit=${limit}`)

  if (!response.ok) {
    throw new Error(`Failed to fetch scrape runs: ${response.statusText}`)
  }

  return response.json()
}

export async function triggerScrape(): Promise<{ message: string; status: string }> {
  const response = await fetch(`${API_BASE}/jobs/scrape`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error(`Failed to trigger scrape: ${response.statusText}`)
  }

  return response.json()
}

// Temporal tracking APIs

export async function fetchNewRoles(since?: string, tiers?: string[]): Promise<NewRolesResponse> {
  const params = new URLSearchParams()
  if (since) params.set('since', since)

  // If specific tiers provided, don't use qualified_only (let backend filter by tier)
  if (tiers && tiers.length > 0) {
    tiers.forEach(tier => params.append('tiers', tier))
  } else {
    params.set('qualified_only', 'true')
  }

  const url = `${API_BASE}/jobs/roles/new${params.toString() ? `?${params}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to fetch new roles: ${response.statusText}`)
  }

  return response.json()
}

export async function fetchRoleChanges(
  since?: string,
  changeTypes?: string[]
): Promise<RoleChange[]> {
  const params = new URLSearchParams()
  if (since) params.set('since', since)
  if (changeTypes && changeTypes.length > 0) {
    changeTypes.forEach(t => params.append('change_types', t))
  }

  const url = `${API_BASE}/jobs/roles/changes${params.toString() ? `?${params}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to fetch role changes: ${response.statusText}`)
  }

  return response.json()
}

export async function fetchDisappearedRoles(since?: string): Promise<Role[]> {
  const params = new URLSearchParams()
  if (since) params.set('since', since)

  const url = `${API_BASE}/jobs/roles/disappeared${params.toString() ? `?${params}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to fetch disappeared roles: ${response.statusText}`)
  }

  return response.json()
}

export async function fetchHotRoles(limit?: number): Promise<Role[]> {
  const params = new URLSearchParams()
  if (limit) params.set('limit', String(limit))

  const url = `${API_BASE}/jobs/roles/hot${params.toString() ? `?${params}` : ''}`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to fetch hot roles: ${response.statusText}`)
  }

  return response.json()
}

// User Settings APIs

export async function fetchLastVisit(): Promise<LastVisitResponse> {
  const response = await fetch(`${API_BASE}/jobs/settings/last-visit`)

  if (!response.ok) {
    throw new Error(`Failed to fetch last visit: ${response.statusText}`)
  }

  return response.json()
}

export async function updateLastVisit(lastVisit: Date): Promise<LastVisitResponse> {
  const response = await fetch(`${API_BASE}/jobs/settings/last-visit`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ last_visit: lastVisit.toISOString() }),
  })

  if (!response.ok) {
    throw new Error(`Failed to update last visit: ${response.statusText}`)
  }

  return response.json()
}
