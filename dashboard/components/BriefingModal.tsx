"use client";

import { useState, useEffect } from "react";
import {
  X,
  Sparkles,
  AlertTriangle,
  Building2,
  DollarSign,
} from "lucide-react";

interface BriefingHeaderMetadata {
  company_name: string;
  company_stage: string | null;
  team_size: number | null;
  salary_range: string;
  equity: string | null;
  location: string;
  workplace_type: string | null;
  hiring_count: number | null;
  interview_stages_count: number | null;
  commission_percent: number | null;
  commission_amount: string | null;
}

interface ProblemContext {
  problem_statement: string | null;
  technical_challenge: string | null;
  solution_approach: string | null;
  why_now: string | null;
}

interface CredibilitySignals {
  founder_background: string | null;
  team_pedigree: string | null;
  traction_metrics: string | null;
  customer_status: string | null;
}

interface RoleDetails {
  core_responsibility: string;
  day_to_day_tasks: string[];
  impact_statement: string | null;
}

interface InterviewProcess {
  stages: string[];
  evaluation_criteria: string[];
  prep_needed: string[];
}

interface BriefingData {
  paraform_id: string;
  header: BriefingHeaderMetadata;
  problem: ProblemContext;
  credibility: CredibilitySignals;
  role: RoleDetails;
  must_haves: string[];
  nice_to_haves: string[];
  interview: InterviewProcess;
  red_flags: string[];
  score_at_enrichment: number;
  enriched_at: string;
}

interface BriefingModalProps {
  paraformId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function BriefingModal({
  paraformId,
  isOpen,
  onClose,
}: BriefingModalProps) {
  const [briefing, setBriefing] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && paraformId) {
      fetchBriefing();
    }
  }, [isOpen, paraformId]);

  const fetchBriefing = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/jobs/roles/${paraformId}/briefing`,
      );
      if (!res.ok) {
        if (res.status === 404) {
          setError(
            "Briefing not available for this role (score < 80 or not yet generated)",
          );
        } else {
          setError("Failed to load briefing");
        }
        return;
      }
      const data = await res.json();
      setBriefing(data);
    } catch (err) {
      setError("Failed to load briefing");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-3">
            <Sparkles className="w-6 h-6 text-blue-600" />
            <h2 className="text-2xl font-bold">Role Profile</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="text-center py-12">
              <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-gray-600">Loading profile...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
              {error}
            </div>
          )}

          {briefing && (
            <>
              {/* SECTION 1: HEADER */}
              <section className="border-b pb-4">
                <div className="flex items-center gap-2 mb-2">
                  <Building2 className="w-5 h-5 text-gray-600" />
                  <h3 className="text-xl font-bold">
                    {briefing.header.company_name}
                  </h3>
                </div>
                <div className="flex items-center gap-2 mb-3">
                  <DollarSign className="w-5 h-5 text-green-600" />
                  <span className="text-lg font-semibold text-green-600">
                    {briefing.header.salary_range}
                  </span>
                  {briefing.header.equity && (
                    <span className="text-sm text-gray-600">
                      + {briefing.header.equity}
                    </span>
                  )}
                </div>
                <div className="text-sm text-gray-600 space-y-1">
                  {briefing.header.company_stage &&
                    briefing.header.team_size && (
                      <p>
                        {briefing.header.company_stage} •{" "}
                        {briefing.header.team_size} people
                      </p>
                    )}
                  <p>
                    {briefing.header.location} •{" "}
                    {briefing.header.workplace_type}
                  </p>
                  {briefing.header.hiring_count &&
                    briefing.header.interview_stages_count && (
                      <p>
                        {briefing.header.hiring_count} positions •{" "}
                        {briefing.header.interview_stages_count} interview
                        stages
                      </p>
                    )}
                  {briefing.header.commission_percent && (
                    <p className="font-semibold text-green-600">
                      {briefing.header.commission_percent}% commission
                      {briefing.header.commission_amount &&
                        ` (${briefing.header.commission_amount})`}
                    </p>
                  )}
                </div>
              </section>

              {/* SECTION 2: COMPANY INTEL */}
              <section>
                <h3 className="text-lg font-semibold mb-3">Company Intel</h3>
                <div className="space-y-2 text-sm">
                  {briefing.problem.problem_statement && (
                    <p className="text-gray-700">
                      {briefing.problem.problem_statement}
                    </p>
                  )}
                  {briefing.problem.technical_challenge && (
                    <p className="text-gray-700">
                      {briefing.problem.technical_challenge}
                    </p>
                  )}
                  {briefing.problem.solution_approach && (
                    <p className="text-gray-700">
                      {briefing.problem.solution_approach}
                    </p>
                  )}
                  {briefing.problem.why_now && (
                    <p className="text-gray-700">{briefing.problem.why_now}</p>
                  )}

                  {/* Credibility - only show if not all gaps */}
                  {briefing.credibility.founder_background &&
                    !briefing.credibility.founder_background.includes(
                      "[RESEARCH NEEDED]",
                    ) && (
                      <p className="text-gray-700">
                        {briefing.credibility.founder_background}
                      </p>
                    )}
                  {briefing.credibility.team_pedigree &&
                    !briefing.credibility.team_pedigree.includes(
                      "[RESEARCH NEEDED]",
                    ) && (
                      <p className="text-gray-700">
                        {briefing.credibility.team_pedigree}
                      </p>
                    )}
                  {briefing.credibility.traction_metrics &&
                    !briefing.credibility.traction_metrics.includes(
                      "[RESEARCH NEEDED]",
                    ) && (
                      <p className="text-gray-700">
                        {briefing.credibility.traction_metrics}
                      </p>
                    )}
                  {briefing.credibility.customer_status &&
                    !briefing.credibility.customer_status.includes(
                      "[RESEARCH NEEDED]",
                    ) && (
                      <p className="text-gray-700">
                        {briefing.credibility.customer_status}
                      </p>
                    )}

                  {/* Show if all fields are empty or gaps */}
                  {!briefing.problem.problem_statement &&
                    !briefing.problem.technical_challenge &&
                    !briefing.problem.solution_approach &&
                    !briefing.problem.why_now && (
                      <p className="text-gray-500 italic">
                        Limited company information available. Additional
                        research needed.
                      </p>
                    )}
                </div>
              </section>

              {/* SECTION 3: THE ROLE */}
              <section>
                <h3 className="text-lg font-semibold mb-3">The Role</h3>
                <p className="font-medium mb-2 text-gray-800">
                  {briefing.role.core_responsibility}
                </p>
                {briefing.role.day_to_day_tasks.length > 0 && (
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                    {briefing.role.day_to_day_tasks.map((task, i) => (
                      <li key={i}>{task}</li>
                    ))}
                  </ul>
                )}
                {briefing.role.impact_statement && (
                  <p className="mt-2 text-sm italic text-gray-600">
                    {briefing.role.impact_statement}
                  </p>
                )}
              </section>

              {/* SECTION 4: REQUIREMENTS */}
              <section>
                <h3 className="text-lg font-semibold mb-3">Requirements</h3>
                <div className="space-y-3">
                  {briefing.must_haves.length > 0 && (
                    <div>
                      <p className="font-medium text-sm mb-1 text-red-700">
                        Must-Haves:
                      </p>
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                        {briefing.must_haves.map((req, i) => (
                          <li key={i}>{req}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {briefing.nice_to_haves.length > 0 && (
                    <div>
                      <p className="font-medium text-sm mb-1 text-blue-700">
                        Nice-to-Haves:
                      </p>
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                        {briefing.nice_to_haves.map((req, i) => (
                          <li key={i}>{req}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>

              {/* SECTION 5: INTERVIEW PROCESS */}
              {briefing.interview.stages.length > 0 && (
                <section>
                  <h3 className="text-lg font-semibold mb-3">
                    Interview Process
                  </h3>
                  <ol className="list-decimal list-inside space-y-1 text-sm mb-3 text-gray-700">
                    {briefing.interview.stages.map((stage, i) => (
                      <li key={i}>{stage}</li>
                    ))}
                  </ol>
                  {briefing.interview.evaluation_criteria.length > 0 && (
                    <div className="space-y-2 text-sm">
                      <p className="font-medium text-gray-800">
                        What they're evaluating:
                      </p>
                      <ul className="list-disc list-inside space-y-1 text-gray-700">
                        {briefing.interview.evaluation_criteria.map(
                          (criteria, i) => (
                            <li key={i}>{criteria}</li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}
                  {briefing.interview.prep_needed.length > 0 && (
                    <div className="space-y-2 text-sm mt-3">
                      <p className="font-medium text-gray-800">
                        Candidate prep:
                      </p>
                      <ul className="list-disc list-inside space-y-1 text-gray-700">
                        {briefing.interview.prep_needed.map((prep, i) => (
                          <li key={i}>{prep}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </section>
              )}

              {/* SECTION 6: RED FLAGS */}
              {briefing.red_flags.length > 0 && (
                <section>
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-500" />
                    Red Flags
                  </h3>
                  <ul className="space-y-1 text-sm">
                    {briefing.red_flags.map((flag, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-yellow-500">⚠️</span>
                        <span className="text-gray-700">{flag}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
