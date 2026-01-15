'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowLeft, Users, User, Trophy } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

export default function TeamDetailsPage() {
  const params = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchTeamDetails() {
      try {
        let teamData
        try {
          teamData = await fetchJson(`/api/teams/${params.team_id}`)
        } catch (err) {
          if (err?.message?.includes('404')) {
            setError('Team not found')
            return
          }
          throw err
        }
        setData(teamData)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchTeamDetails()
  }, [params.team_id])

  if (loading) {
    return (
      <div className="container py-12">
        <div className="flex min-h-[400px] items-center justify-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="h-8 w-8 rounded-full border-2 border-emerald-300/70 border-t-transparent"
          />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="container py-12">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="text-lg font-semibold text-white">Error</h2>
          <p className="mt-2 text-sm text-white/60">{error || 'Team not found'}</p>
          <Link
            href="/teams"
            className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white/80 hover:border-white/30 hover:bg-white/10"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Teams
          </Link>
        </div>
      </div>
    )
  }

  const { team, activePlayers = [], inactivePlayers = [] } = data
  const totalPlayers = activePlayers.length + inactivePlayers.length

  return (
    <div className="container py-10">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <Link
          href="/teams"
          className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white/80 hover:border-white/30 hover:bg-white/10"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Teams
        </Link>

        <div className="flex items-center gap-4">
          <div className="flex h-20 w-20 items-center justify-center rounded-3xl border border-emerald-300/30 bg-emerald-500/10 text-3xl font-semibold text-emerald-100">
            {team.logo_url ? (
              <img
                src={team.logo_url}
                alt={`${team.team_name} logo`}
                className="h-14 w-14 bg-white/5 object-contain"
              />
            ) : (
              team.team_name?.charAt(0) || 'T'
            )}
          </div>
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">{team.team_name}</h1>
            <p className="text-sm text-white/60">
              {team.region !== 'UNKNOWN' ? `${team.region} • ` : ''}
              {team.is_inactive ? 'Inactive' : 'Active'}
            </p>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
            <div>
              <h2 className="flex items-center text-2xl font-semibold">
                <Users className="mr-2 h-5 w-5 text-emerald-200" />
                Roster
              </h2>
              <p className="text-sm text-white/60">
                {totalPlayers} player{totalPlayers !== 1 ? 's' : ''} on this team
              </p>
            </div>
            <span className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-white/70">
              {totalPlayers} Players
            </span>
          </div>

          <div className="mt-5 space-y-8">
            {activePlayers.length > 0 && (
              <div>
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-emerald-200">
                  <Trophy className="h-4 w-4" />
                  Active Roster
                </h3>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {activePlayers.map((player, index) => (
                    <motion.div
                      key={player.player_name}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: index * 0.1 }}
                      whileHover={{ scale: 1.02 }}
                      className="rounded-2xl border border-emerald-300/20 bg-emerald-500/10 p-4"
                    >
                      <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-300/40 bg-emerald-500/10 text-lg font-semibold text-emerald-100">
                          {player.player_name?.charAt(0) || 'P'}
                        </div>
                        <div className="flex-1">
                          <div className="text-base font-semibold text-white">{player.player_name}</div>
                          {player.last_match_date && (
                            <div className="text-xs text-white/60">
                              Last match: {player.last_match_date.slice(0, 10)}
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {inactivePlayers.length > 0 && (
              <div>
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white/50">
                  <User className="h-4 w-4" />
                  Inactive / Former Players
                </h3>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {inactivePlayers.map((player, index) => (
                    <motion.div
                      key={player.player_name}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: index * 0.1 }}
                      whileHover={{ scale: 1.02 }}
                      className="rounded-2xl border border-white/10 bg-white/5 p-4"
                    >
                      <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-lg font-semibold text-white/60">
                          {player.player_name?.charAt(0) || 'P'}
                        </div>
                        <div className="flex-1">
                          <div className="text-base font-semibold text-white">{player.player_name}</div>
                          {player.last_match_date && (
                            <div className="text-xs text-white/50">
                              Last match: {player.last_match_date.slice(0, 10)}
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {totalPlayers === 0 && (
              <div className="py-12 text-center">
                <User className="mx-auto mb-4 h-12 w-12 text-white/40" />
                <p className="text-white/60">No players found for this team.</p>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
