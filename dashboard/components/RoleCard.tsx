'use client'

import { Role } from '@/lib/types'
import { ExternalLink, MapPin, DollarSign, Users, Sparkles, CheckCircle, HelpCircle, XCircle, Star, FileText } from 'lucide-react'
import { useState } from 'react'
import { BriefingModal } from './BriefingModal'

interface RoleCardProps {
  role: Role
  isNew?: boolean
}

export function RoleCard({ role, isNew = false }: RoleCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showBriefing, setShowBriefing] = useState(false)

  const tierColors = {
    QUALIFIED: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      badge: 'bg-green-500',
      text: 'text-green-700',
      icon: CheckCircle
    },
    MAYBE: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      badge: 'bg-yellow-500',
      text: 'text-yellow-700',
      icon: HelpCircle
    },
    SKIP: {
      bg: 'bg-gray-50',
      border: 'border-gray-200',
      badge: 'bg-gray-500',
      text: 'text-gray-700',
      icon: XCircle
    }
  }

  const tier = (role.qualification_tier || 'SKIP') as keyof typeof tierColors
  const colors = tierColors[tier]
  const TierIcon = colors.icon

  // Use formatted display fields from API
  const salaryDisplay = role.salary_display
  const locationDisplay = role.workplace_display

  // Format company info using API-formatted fields
  const companyInfo = []
  if (role.funding_stage_display) companyInfo.push(role.funding_stage_display)
  if (role.funding_display) companyInfo.push(role.funding_display)
  if (role.company_size) companyInfo.push(`${role.company_size} employees`)

  return (
    <div className={`border rounded-lg overflow-hidden ${colors.border} ${colors.bg} hover:shadow-md transition-shadow`}>
      <div className="p-4">
        {/* Header */}
        <div className="flex justify-between items-start mb-3">
          <div className="flex items-start gap-3 flex-1">
            {role.company_logo_url && (
              <img
                src={role.company_logo_url}
                alt={role.company_name}
                className="w-12 h-12 rounded-lg object-contain bg-white flex-shrink-0"
              />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <h3 className="text-lg font-semibold text-gray-900">
                  {role.title}
                </h3>
                {isNew && (
                  <span className="inline-flex items-center gap-1 bg-blue-600 text-white px-2 py-0.5 rounded-full text-xs font-bold animate-pulse">
                    <Sparkles className="w-3 h-3" />
                    NEW
                  </span>
                )}
              </div>
              <p className="text-gray-700 font-medium">
                {role.company_name}
              </p>
              {companyInfo.length > 0 && (
                <p className="text-sm text-gray-600 mt-1">
                  {companyInfo.join(' • ')}
                </p>
              )}
            </div>
          </div>
          <span className={`inline-flex items-center gap-1 ${colors.badge} text-white px-3 py-1 rounded-full text-sm font-semibold whitespace-nowrap ml-4`}>
            <TierIcon className="w-4 h-4" />
            {tier}
          </span>
        </div>

        {/* Quick Info */}
        <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
          <div className="flex items-center gap-2 text-gray-700">
            <DollarSign className="w-4 h-4 text-green-600" />
            <span>{salaryDisplay}</span>
          </div>
          <div className="flex items-center gap-2 text-gray-700">
            <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">
              {role.percent_fee_display}
            </span>
          </div>
          <div className="flex items-center gap-2 text-gray-700">
            <MapPin className="w-4 h-4 text-gray-500" />
            <span className="truncate">{locationDisplay}</span>
          </div>
          {role.hiring_count_display && (
            <div className="flex items-center gap-2 text-gray-700">
              <Users className="w-4 h-4 text-gray-500" />
              <span>Hiring {role.hiring_count_display}</span>
            </div>
          )}
        </div>

        {/* Investors */}
        {role.investors.length > 0 && (
          <div className="mb-3">
            <p className="text-sm text-gray-600">
              <span className="font-medium">Investors:</span> {role.investors.slice(0, 3).join(', ')}
              {role.investors.length > 3 && ` +${role.investors.length - 3} more`}
            </p>
          </div>
        )}

        {/* Highlights */}
        {role.highlights.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {role.highlights.map((highlight, i) => (
              <span key={i} className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs font-medium">
                <Star className="w-3 h-3" />
                {highlight.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}

        {/* Expanded Details */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-gray-200 space-y-3">
            {/* Tech Stack */}
            {role.tech_stack.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-1">Tech Stack</h4>
                <div className="flex flex-wrap gap-2">
                  {role.tech_stack.map((tech, i) => (
                    <span key={i} className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs">
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Role Types */}
            {role.role_types.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-1">Role Type</h4>
                <div className="flex flex-wrap gap-2">
                  {role.role_types.map((type, i) => (
                    <span key={i} className="bg-purple-100 text-purple-700 px-2 py-1 rounded text-xs">
                      {type.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Manager Rating */}
            {role.manager_rating && (
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-1">Manager Rating</h4>
                <p className="text-sm text-gray-700">
                  {role.manager_rating.toFixed(1)} / 5.0
                </p>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <a
            href={role.paraform_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            View on Paraform
            <ExternalLink className="w-4 h-4" />
          </a>

          {(role.has_briefing || (role.combined_score !== null && role.combined_score >= 0.80)) && (
            <button
              onClick={() => setShowBriefing(true)}
              className="inline-flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
            >
              <FileText className="w-4 h-4" />
              View Briefing
            </button>
          )}

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="inline-flex items-center gap-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
          >
            {isExpanded ? 'Show Less' : 'Show More'}
          </button>
        </div>
      </div>

      <BriefingModal
        paraformId={role.paraform_id}
        isOpen={showBriefing}
        onClose={() => setShowBriefing(false)}
      />
    </div>
  )
}
