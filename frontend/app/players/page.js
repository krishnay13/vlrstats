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

  useEffect(() => {
    async function fetchPlayers() {
      try {
        const data = await fetchJson('/api/players')
        setPlayers(data)
      } catch (error) {
        console.error(error)
      } finally {
        setLoading(false)
      }
    }
    fetchPlayers()
  }, [])

  // Sort players
  const sortedPlayers = useMemo(() => {
    if (!players.length) return []
    
    return [...players].sort((a, b) => {
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
    })
  }, [players, sortBy, sortDirection])

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
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/60">Sort by:</span>
            {SORT_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => handleSort(option.value)}
                className={`flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                  sortBy === option.value
                    ? 'border-emerald-400/50 bg-emerald-500/10 text-emerald-200'
                    : 'border-white/10 bg-white/5 text-white/70 hover:bg-white/10'
                }`}
              >
                {option.label}
                {sortBy === option.value && (
                  sortDirection === 'asc' ? (
                    <ArrowUp className="h-3 w-3" />
                  ) : (
                    <ArrowDown className="h-3 w-3" />
                  )
                )}
              </button>
            ))}
          </div>
        </div>
      </motion.div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <div className="grid grid-cols-1 gap-0 divide-y divide-white/5">
          {sortedPlayers.map((player, index) => (
            <motion.div
              key={player.player_name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.01 }}
              className="flex items-center justify-between px-4 py-3 transition-colors hover:bg-white/5"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-300/20 bg-emerald-500/10 text-sm font-semibold text-emerald-100">
                  {player.player_name?.charAt(0) || 'P'}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white">{player.player_name}</span>
                  {player.is_inactive && (
                    <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-2 py-0.5 text-[11px] text-rose-200">
                      Inactive
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 text-sm text-white/60">
                  {player.team_logo ? (
                    <img
                      src={player.team_logo}
                      alt={`${player.team_name} logo`}
                      className="h-4 w-4 bg-white/5 object-contain"
                    />
                  ) : (
                    <Users className="h-3.5 w-3.5 text-white/40" />
                  )}
                  <span>{player.team_name || 'Free Agent'}</span>
                </div>
                {player.region && player.region !== 'UNKNOWN' && (
                  <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-white/50 uppercase">
                    {player.region}
                  </span>
                )}
              </div>
            </motion.div>
          ))}
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
