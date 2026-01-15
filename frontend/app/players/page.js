'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Users } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

export default function PlayersPage() {
  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)

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
        <h1 className="text-2xl font-semibold tracking-tight mb-1">Players</h1>
        <p className="text-sm text-white/60">
          Browse all Valorant esports players and their teams
        </p>
      </motion.div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5">
        <div className="grid grid-cols-1 gap-0 divide-y divide-white/5">
          {players.map((player, index) => (
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
              <div className="flex items-center gap-2 text-sm text-white/60">
                <Users className="h-3.5 w-3.5 text-white/40" />
                <span>{player.team_name || 'Free Agent'}</span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {players.length === 0 && (
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
