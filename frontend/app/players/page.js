'use client'

import { useEffect, useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Users, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

const SORT_OPTIONS = [
  { value: 'name', label: 'Name' },
  { value: 'team', label: 'Team' },
  { value: 'region', label: 'Region' },
]

export default function PlayersPage() {
  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('name')
  const [sortDirection, setSortDirection] = useState('asc')
  const [showInactive, setShowInactive] = useState(false)
  const [selectedTeam, setSelectedTeam] = useState('all')
  const [selectedYear, setSelectedYear] = useState(2026)

  useEffect(() => {
    async function fetchPlayers() {
      try {
        const data = await fetchJson(`/api/players?year=${selectedYear}`)
        setPlayers(data)
      } catch (error) {
        console.error(error)
      } finally {
        setLoading(false)
      }
    }
    fetchPlayers()
  }, [selectedYear])

  // Get unique teams for filter
  const allTeams = useMemo(() => {
    const teams = new Set()
    players.forEach(p => {
      if (p.team_name) teams.add(p.team_name)
    })
    return Array.from(teams).sort()
  }, [players])

  // Sort players
  const sortedPlayers = useMemo(() => {
    if (!players.length) return []
    
    // Filter by team if selected
    let filtered = players
    if (selectedTeam !== 'all') {
      filtered = players.filter(p => p.team_name === selectedTeam)
    }
    
    // Separate active and inactive
    const activePlayers = filtered.filter(p => !p.is_inactive)
    const inactivePlayers = filtered.filter(p => p.is_inactive)
    
    const sortFn = (a, b) => {
      let comparison = 0
      
      if (sortBy === 'name') {
        comparison = a.player_name.localeCompare(b.player_name)
      } else if (sortBy === 'team') {
        const teamA = a.team_name || 'ZZZ'
        const teamB = b.team_name || 'ZZZ'
        comparison = teamA.localeCompare(teamB)
      } else if (sortBy === 'region') {
        const regionOrder = { AMERICAS: 1, EMEA: 2, APAC: 3, CHINA: 4, UNKNOWN: 5 }
        const orderA = regionOrder[a.region] || 99
        const orderB = regionOrder[b.region] || 99
        comparison = orderA - orderB
        // If same region, sort by team name
        if (comparison === 0) {
          const teamA = a.team_name || 'ZZZ'
          const teamB = b.team_name || 'ZZZ'
          comparison = teamA.localeCompare(teamB)
        }
      }
      
      return sortDirection === 'asc' ? comparison : -comparison
    }
    
    const sortedActive = [...activePlayers].sort(sortFn)
    const sortedInactive = [...inactivePlayers].sort(sortFn)
    
    return showInactive ? [...sortedActive, ...sortedInactive] : sortedActive
  }, [players, sortBy, sortDirection, showInactive, selectedTeam])

  const handleSort = (newSortBy) => {
    if (sortBy === newSortBy) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(newSortBy)
      setSortDirection('asc')
    }
  }

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

  return (
    <div className="container py-6 max-w-7xl">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight mb-1">Players</h1>
            <p className="text-sm text-white/60">
              Browse all Valorant esports players and their teams
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/60">Year:</span>
              <div className="flex items-center gap-1">
                {[2024, 2025, 2026].map((year) => (
                  <button
                    key={year}
                    onClick={() => setSelectedYear(year)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                      selectedYear === year
                        ? 'border border-emerald-400/50 bg-emerald-500/10 text-emerald-200'
                        : 'border border-white/10 bg-white/5 text-white/70 hover:bg-white/10'
                    }`}
                  >
                    {year}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/60">Team:</span>
              <select
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value)}
                className="rounded-lg border border-white/10 bg-[#0a0f1a]/90 px-3 py-1.5 text-xs font-medium text-white/80 transition hover:border-emerald-400/30 hover:bg-white/5 focus:border-emerald-400/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              >
                <option value="all" className="bg-[#0a0f1a] text-white/80">All Teams</option>
                {allTeams.map((team) => (
                  <option key={team} value={team} className="bg-[#0a0f1a] text-white/80">
                    {team}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/60">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value)
                  setSortDirection('asc')
                }}
                className="rounded-lg border border-white/10 bg-[#0a0f1a]/90 px-3 py-1.5 text-xs font-medium text-white/80 transition hover:border-emerald-400/30 hover:bg-white/5 focus:border-emerald-400/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value} className="bg-[#0a0f1a] text-white/80">
                    {option.label}
                  </option>
                ))}
              </select>
              <button
                onClick={() => setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')}
                className="flex items-center justify-center rounded-lg border border-white/10 bg-white/5 p-1.5 text-white/70 transition hover:border-emerald-400/30 hover:bg-white/10"
                title={sortDirection === 'asc' ? 'Ascending' : 'Descending'}
              >
                {sortDirection === 'asc' ? (
                  <ArrowUp className="h-3.5 w-3.5" />
                ) : (
                  <ArrowDown className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
            <div className="flex items-center gap-2 border-l border-white/10 pl-4">
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
        </div>
      </motion.div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-white/5 text-xs font-semibold uppercase tracking-wide text-white/60">
              <tr className="h-11">
                <th className="px-4 text-left">Player</th>
                <th className="px-4 text-left">Team</th>
                <th className="px-4 text-center">Region</th>
                <th className="px-4 text-center">Avg Rating</th>
                <th className="px-4 text-center">Avg K/Map</th>
                <th className="px-4 text-center">Avg A/Map</th>
                <th className="px-4 text-center">Maps</th>
                <th className="px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {sortedPlayers.map((player, index) => (
                <motion.tr
                  key={player.player_name}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.01 }}
                  className="h-12 border-b border-white/5 transition-colors hover:bg-white/5"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-300/20 bg-emerald-500/10 text-sm font-semibold text-emerald-100">
                        {player.player_name?.charAt(0) || 'P'}
                      </div>
                      <span className="text-sm font-medium text-white">{player.player_name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {player.team_logo ? (
                        <img
                          src={player.team_logo}
                          alt={`${player.team_name} logo`}
                          className="h-5 w-5 bg-white/5 object-contain"
                          onError={(e) => {
                            e.target.style.display = 'none'
                            e.target.nextElementSibling.style.display = 'flex'
                          }}
                        />
                      ) : null}
                      <Users className="h-4 w-4 text-white/40" style={{ display: player.team_logo ? 'none' : 'flex' }} />
                      <span className="text-sm text-white/80">{player.team_name || 'Free Agent'}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {player.region && player.region !== 'UNKNOWN' ? (
                      <span className="inline-block rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-white/60 uppercase">
                        {player.region}
                      </span>
                    ) : (
                      <span className="text-xs text-white/40">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-sm font-medium text-emerald-200">
                      {player.avg_rating ? player.avg_rating.toFixed(2) : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-sm text-white/80">
                      {player.avg_kills ? player.avg_kills.toFixed(1) : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-sm text-white/80">
                      {player.avg_assists ? player.avg_assists.toFixed(1) : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-xs text-white/60">
                      {player.maps_played || 0}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {player.is_inactive ? (
                      <span className="inline-block rounded-full border border-rose-400/30 bg-rose-500/10 px-2 py-0.5 text-[11px] font-medium text-rose-200">
                        Inactive
                      </span>
                    ) : (
                      <span className="inline-block rounded-full border border-emerald-400/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-200">
                        Active
                      </span>
                    )}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {sortedPlayers.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="py-12 text-center"
        >
          <p className="text-white/60">No players found.</p>
        </motion.div>
      )}
    </div>
  )
}
