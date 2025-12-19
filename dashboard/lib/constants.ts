/**
 * Shared constants from backend API.
 *
 * Single source of truth for investor tiers, funding stages, industries, etc.
 * Fetched from /shared/constants endpoint to stay in sync with backend.
 */

// In production, NEXT_PUBLIC_API_URL points to the API directly
// In development, fall back to relative /api which uses Next.js proxy
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api'

export interface Constants {
  investors: {
    tier_1: string[]
    tier_2: string[]
    notable_angels: string[]
  }
  companies: {
    hot: string[]
  }
  thresholds: {
    high: number
    medium: number
  }
}

let cachedConstants: Constants | null = null

/**
 * Fetch shared constants from backend API.
 * Results are cached for the session to avoid repeated API calls.
 */
export async function fetchConstants(): Promise<Constants> {
  if (cachedConstants) {
    return cachedConstants
  }

  const url = `${API_BASE}/shared/constants`
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`Failed to fetch constants: ${response.statusText}`)
  }

  const data: Constants = await response.json()
  cachedConstants = data
  return data
}

/**
 * Clear the constants cache (useful for testing or force refresh).
 */
export function clearConstantsCache() {
  cachedConstants = null
}

/**
 * Get investor tier for a given investor name.
 * Returns 1 for Tier 1, 2 for Tier 2, 0 for unknown.
 * Case-insensitive matching.
 */
export function getInvestorTier(investorName: string, constants: Constants): number {
  const normalized = investorName.toLowerCase().trim()

  // Check Tier 1
  for (const tier1 of constants.investors.tier_1) {
    if (tier1.toLowerCase() === normalized) {
      return 1
    }
  }

  // Check Tier 2
  for (const tier2 of constants.investors.tier_2) {
    if (tier2.toLowerCase() === normalized) {
      return 2
    }
  }

  return 0
}

/**
 * Get the highest tier from a list of investors.
 * Returns 1 for Tier 1, 2 for Tier 2, 0 for no tier investors.
 */
export function getHighestInvestorTier(investors: string[], constants: Constants): number {
  let highestTier = 0

  for (const investor of investors) {
    const tier = getInvestorTier(investor, constants)
    if (tier > 0 && (highestTier === 0 || tier < highestTier)) {
      highestTier = tier
    }
  }

  return highestTier
}

/**
 * Get investor short name for display.
 * Maps full names to common abbreviations.
 */
export function getInvestorShortName(investorName: string): string {
  const shortNames: Record<string, string> = {
    'Y Combinator': 'YC',
    'Sequoia Capital': 'Sequoia',
    'Andreessen Horowitz': 'a16z',
    'Lightspeed Venture Partners': 'Lightspeed',
    'First Round Capital': 'First Round',
    'Bessemer Venture Partners': 'Bessemer',
    'New Enterprise Associates': 'NEA',
    'Tiger Global Management': 'Tiger',
    'Google Ventures': 'GV',
    'Union Square Ventures': 'USV',
    'Bain Capital Ventures': 'Bain',
    'Scale Venture Partners': 'Scale',
    'Redpoint Ventures': 'Redpoint',
    'Kleiner Perkins': 'KP',
    'General Catalyst': 'GC',
  }

  return shortNames[investorName] || investorName
}
