'use client'

/**
 * React context for shared constants from backend.
 *
 * Provides constants to all components via useConstants() hook.
 * Fetches from /shared/constants on app initialization.
 */

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { Constants, fetchConstants } from '../constants'

interface ConstantsContextType {
  constants: Constants | null
  loading: boolean
  error: Error | null
}

const ConstantsContext = createContext<ConstantsContextType>({
  constants: null,
  loading: true,
  error: null,
})

export function ConstantsProvider({ children }: { children: ReactNode }) {
  const [constants, setConstants] = useState<Constants | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadConstants() {
      try {
        const data = await fetchConstants()
        if (!cancelled) {
          setConstants(data)
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error('Failed to load constants'))
          setLoading(false)
        }
      }
    }

    loadConstants()

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <ConstantsContext.Provider value={{ constants, loading, error }}>
      {children}
    </ConstantsContext.Provider>
  )
}

/**
 * Hook to access shared constants.
 *
 * Returns constants, loading state, and error.
 * Use loading state to show loading UI while constants are fetched.
 */
export function useConstants() {
  const context = useContext(ConstantsContext)
  if (context === undefined) {
    throw new Error('useConstants must be used within a ConstantsProvider')
  }
  return context
}
