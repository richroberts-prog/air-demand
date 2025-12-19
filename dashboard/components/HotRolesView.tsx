'use client'

import { useQuery } from '@tanstack/react-query'
import { fetchHotRoles } from '@/lib/api'
import { TrendingUp } from 'lucide-react'
import { RoleTable } from '@/components/RoleTable'

export function HotRolesView() {
  const { data: hotRoles, isLoading, error } = useQuery({
    queryKey: ['hot-roles'],
    queryFn: () => fetchHotRoles(20),
    refetchInterval: 60000, // Refresh every 60 seconds
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-500">Loading hot roles...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-red-500">Failed to load hot roles: {String(error)}</div>
      </div>
    )
  }

  if (!hotRoles || hotRoles.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-gray-500">
          No hot roles found. Hot roles show when interview activity increases.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 px-4">
        <TrendingUp className="w-5 h-5 text-orange-500" />
        <h2 className="text-lg font-semibold text-gray-900">
          Hot Roles - Surging Interview Activity
        </h2>
        <span className="text-sm text-gray-500">({hotRoles.length} roles)</span>
      </div>

      {/* Info banner */}
      <div className="mx-4 bg-orange-50 border border-orange-200 rounded-lg p-3">
        <p className="text-sm text-orange-800">
          🔥 These roles have seen an increase in interview activity in the last 7 days,
          indicating high employer urgency. Sorted by interview surge magnitude.
        </p>
      </div>

      {/* Use existing RoleTable component for consistent styling */}
      <div className="overflow-x-auto">
        <RoleTable roles={hotRoles} />
      </div>
    </div>
  )
}
