'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Trophy, TrendingUp, Calendar } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

const DATE_RANGES = [
  { value: 'all-time', label: 'All Time' },
  { value: '2024', label: '2024' },
  { value: '2025', label: '2025' },
  { value: '2026', label: '2026' },
]

export default function RankingsPage() {
  const [elo, setElo] = useState({ teams: [], players: [] })
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState('all-time')

  useEffect(() => {
    async function fetchElo() {
      setLoading(true)
      try {
        // Fetch top 100 for full rankings with date range
        const url = `/api/elo?topTeams=100&topPlayers=100&dateRange=${encodeURIComponent(dateRange)}`
        const data = await fetchJson(url)
        setElo({ teams: data.teams || [], players: data.players || [] })
      } catch (error) {
        console.error('Failed to fetch Elo data:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchElo()
  }, [dateRange])

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
        className="mb-8"
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight mb-2">Elo Rankings</h1>
            <p className="text-sm text-white/60">
              Complete leaderboards for teams and players based on Elo ratings
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Calendar className="h-4 w-4 text-white/60" />
            <div className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-1 py-1">
              {DATE_RANGES.map((range) => {
                const isActive = dateRange === range.value
                return (
                  <button
                    key={range.value}
                    type="button"
                    onClick={() => setDateRange(range.value)}
                    className={`rounded-full px-3 py-1 text-xs sm:text-sm font-medium transition ${
                      isActive
                        ? 'bg-emerald-400/80 text-black shadow-[0_0_18px_rgba(16,185,129,0.45)]'
                        : 'bg-transparent text-white/70 hover:bg-white/10'
                    }`}
                  >
                    {range.label}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </motion.div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Teams Rankings */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="rounded-3xl border border-emerald-400/20 bg-gradient-to-br from-emerald-500/10 via-white/5 to-transparent p-6 shadow-[0_0_45px_rgba(16,185,129,0.15)] backdrop-blur"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-emerald-200/70">Leaderboard</p>
              <h2 className="mt-2 text-2xl font-semibold">Top Teams</h2>
            </div>
            <Trophy className="h-6 w-6 text-emerald-200/80" />
          </div>

          <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/20">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-xs font-semibold uppercase tracking-wide text-white/60">
                <tr className="h-10">
                  <th className="px-4 text-left w-12">#</th>
                  <th className="px-4 text-left">Team</th>
                  <th className="px-4 text-right">Rating</th>
                  <th className="px-4 text-right">Matches</th>
                </tr>
              </thead>
              <tbody>
                {elo.teams.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-white/60">
                      No team rankings available. Run: python -m loadDB.cli elo compute --save
                    </td>
                  </tr>
                ) : (
                  elo.teams.map((team, index) => (
                    <motion.tr
                      key={team.team}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.01 }}
                      className="h-12 border-b border-white/5 transition-colors hover:bg-white/5"
                    >
                      <td className="px-4 text-sm font-semibold text-emerald-200/80">
                        {index + 1}
                      </td>
                      <td className="px-4">
                        <div className="flex items-center gap-3">
                          {team.logo_url ? (
                            <img
                              src={team.logo_url}
                              alt={`${team.team} logo`}
                              className="h-5 w-5 object-contain"
                            />
                          ) : null}
                          <span className="font-medium text-white">{team.team}</span>
                        </div>
                      </td>
                      <td className="px-4 text-right font-semibold text-emerald-100/90">
                        {team.rating?.toFixed(1) || '0.0'}
                      </td>
                      <td className="px-4 text-right text-white/60">
                        {team.matches || 0}
                      </td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Players Rankings */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 via-white/5 to-transparent p-6 shadow-[0_0_45px_rgba(0,0,0,0.4)] backdrop-blur"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-white/50">Leaderboard</p>
              <h2 className="mt-2 text-2xl font-semibold">Top Players</h2>
            </div>
            <TrendingUp className="h-6 w-6 text-white/70" />
          </div>

          <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/20">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-xs font-semibold uppercase tracking-wide text-white/60">
                <tr className="h-10">
                  <th className="px-4 text-left w-12">#</th>
                  <th className="px-4 text-left">Player</th>
                  <th className="px-4 text-left">Team</th>
                  <th className="px-4 text-right">Rating</th>
                  <th className="px-4 text-right">Matches</th>
                </tr>
              </thead>
              <tbody>
                {elo.players.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-white/60">
                      No player rankings available. Run: python -m loadDB.cli elo compute --save
                    </td>
                  </tr>
                ) : (
                  elo.players.map((player, index) => (
                    <motion.tr
                      key={player.player}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.01 }}
                      className="h-12 border-b border-white/5 transition-colors hover:bg-white/5"
                    >
                      <td className="px-4 text-sm font-semibold text-white/70">
                        {index + 1}
                      </td>
                      <td className="px-4">
                        <span className="font-medium text-white">{player.player}</span>
                      </td>
                      <td className="px-4">
                        <div className="flex items-center gap-2">
                          {player.team_logo ? (
                            <img
                              src={player.team_logo}
                              alt={`${player.team} logo`}
                              className="h-4 w-4 object-contain"
                            />
                          ) : null}
                          <span className="text-xs text-white/60">
                            {player.team || 'Free Agent'}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 text-right font-semibold text-white/90">
                        {player.rating?.toFixed(1) || '0.0'}
                      </td>
                      <td className="px-4 text-right text-white/60">
                        {player.matches || 0}
                      </td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
