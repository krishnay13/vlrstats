'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { Users, ArrowRight } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

const REGION_ORDER = ['AMERICAS', 'EMEA', 'APAC', 'CHINA', 'UNKNOWN']
const REGION_LABELS = {
  'AMERICAS': 'Americas',
  'EMEA': 'EMEA',
  'APAC': 'APAC',
  'CHINA': 'China',
  'UNKNOWN': 'Unknown',
}

export default function TeamsPage() {
  const [teams, setTeams] = useState([])
  const [loading, setLoading] = useState(true)
  const [showInactive, setShowInactive] = useState(false)

  useEffect(() => {
    async function fetchTeams() {
      try {
        const data = await fetchJson('/api/teams')
        setTeams(data)
      } catch (error) {
        console.error(error)
      } finally {
        setLoading(false)
      }
    }
    fetchTeams()
  }, [])

  if (loading) {
    return (
      <div className="container py-6">
        <div className="flex items-center justify-center min-h-[300px]">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="h-6 w-6 rounded-full border-2 border-emerald-300/70 border-t-transparent"
          />
        </div>
      </div>
    )
  }

  // Filter teams based on showInactive toggle
  const filteredTeams = showInactive ? teams : teams.filter(team => !team.is_inactive)

  // Group teams by region
  const teamsByRegion = filteredTeams.reduce((acc, team) => {
    const region = team.region || 'UNKNOWN'
    if (!acc[region]) {
      acc[region] = []
    }
    acc[region].push(team)
    return acc
  }, {})

  return (
    <div className="container py-6 max-w-7xl">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight mb-1">Teams</h1>
            <p className="text-sm text-white/60">
              Explore all Valorant esports teams organized by region
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={(e) => setShowInactive(e.target.checked)}
                className="h-4 w-4 rounded border border-white/20 bg-white/5 accent-emerald-500"
              />
              <span className="text-xs text-white/60">Show Inactive</span>
            </label>
          </div>
        </div>
      </motion.div>

      <div className="space-y-6">
        {REGION_ORDER.map((region) => {
          const regionTeams = teamsByRegion[region] || []
          if (regionTeams.length === 0) return null

          return (
            <motion.div
              key={region}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="overflow-hidden rounded-2xl border border-white/10 bg-white/5"
            >
              <div className="border-b border-white/10 bg-white/5 px-4 py-3">
                <h2 className="text-lg font-semibold text-white mb-3">{REGION_LABELS[region] || region}</h2>
                <div className="grid grid-cols-5 gap-4 text-xs font-semibold uppercase tracking-wide text-white/60">
                  <div className="col-span-2">Team</div>
                  <div className="text-center">Match Record</div>
                  <div className="text-center">Map Record</div>
                  <div className="text-center">Round Diff</div>
                </div>
              </div>

              <div className="divide-y divide-white/5">
                {regionTeams.map((team, index) => (
                  <motion.div
                    key={team.team_name}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.01 }}
                    className="grid grid-cols-5 gap-4 items-center px-4 py-3 transition-colors hover:bg-white/5"
                  >
                    <div className="col-span-2 flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-300/20 bg-emerald-500/10 text-sm font-semibold text-emerald-100">
                        {team.logo_url ? (
                          <img
                            src={team.logo_url}
                            alt={`${team.team_name} logo`}
                            className="h-7 w-7 bg-white/5 object-contain"
                          />
                        ) : (
                          team.team_name?.charAt(0) || 'T'
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/teams/${encodeURIComponent(team.team_name)}`}
                          className="text-sm font-medium text-white hover:text-emerald-200 transition-colors"
                        >
                          {team.team_name}
                        </Link>
                        {team.is_inactive && (
                          <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-2 py-0.5 text-[11px] text-rose-200">
                            Inactive
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-center">
                      <span className="text-sm text-white/80">
                        {team.match_wins || 0}-{team.match_losses || 0}
                      </span>
                    </div>
                    <div className="text-center">
                      <span className="text-sm text-white/80">
                        {team.map_wins || 0}-{team.map_losses || 0}
                      </span>
                    </div>
                    <div className="text-center">
                      <span className={`text-sm font-medium ${
                        team.round_differential > 0 
                          ? 'text-emerald-200' 
                          : team.round_differential < 0 
                          ? 'text-rose-200' 
                          : 'text-white/60'
                      }`}>
                        {team.round_differential > 0 ? '+' : ''}{team.round_differential || 0}
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )
        })}
      </div>

      {teams.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="py-12 text-center"
        >
          <p className="text-white/60">No teams found.</p>
        </motion.div>
      )}
    </div>
  )
}
