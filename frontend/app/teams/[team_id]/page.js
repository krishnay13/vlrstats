'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, Users, User, Trophy, Zap, ChevronDown, X } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

export default function TeamDetailsPage() {
  const params = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedYear, setSelectedYear] = useState(2026)
  const [bansPicks, setBansPicks] = useState(null)
  const [expandedMap, setExpandedMap] = useState(null)

  useEffect(() => {
    async function fetchTeamDetails() {
      try {
        let teamData
        try {
          teamData = await fetchJson(`/api/teams/${params.team_id}?year=${selectedYear}`)
        } catch (err) {
          if (err?.message?.includes('404')) {
            setError('Team not found')
            return
          }
          throw err
        }
        setData(teamData)
        
        // Fetch bans/picks data
        try {
          const bansPicksData = await fetchJson(`/api/teams/${params.team_id}/bans-picks?year=${selectedYear}`)
          setBansPicks(bansPicksData)
        } catch (err) {
          // Bans/picks data is optional
          setBansPicks(null)
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchTeamDetails()
  }, [params.team_id, selectedYear])

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
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSelectedYear(2024)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  selectedYear === 2024
                    ? 'border border-emerald-400/50 bg-emerald-500/10 text-emerald-200'
                    : 'border border-white/10 bg-white/5 text-white/70 hover:bg-white/10'
                }`}
              >
                2024
              </button>
              <button
                onClick={() => setSelectedYear(2025)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  selectedYear === 2025
                    ? 'border border-emerald-400/50 bg-emerald-500/10 text-emerald-200'
                    : 'border border-white/10 bg-white/5 text-white/70 hover:bg-white/10'
                }`}
              >
                2025
              </button>
              <button
                onClick={() => setSelectedYear(2026)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  selectedYear === 2026
                    ? 'border border-emerald-400/50 bg-emerald-500/10 text-emerald-200'
                    : 'border border-white/10 bg-white/5 text-white/70 hover:bg-white/10'
                }`}
              >
                2026
              </button>
            </div>
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

      {/* Map Veto Tendencies */}
      {bansPicks && (bansPicks.bans.length > 0 || bansPicks.picks.length > 0) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-6"
        >
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
            <h2 className="mb-1 flex items-center text-2xl font-semibold">
              <Zap className="mr-2 h-5 w-5 text-amber-200" />
              Map Veto Tendencies
            </h2>
            <p className="mb-4 text-sm text-white/60">
              Based on {bansPicks.total_matches_with_veto} match{bansPicks.total_matches_with_veto !== 1 ? 'es' : ''} with veto data in {selectedYear}
            </p>

            <div className="grid gap-6 md:grid-cols-2">
              {/* Bans */}
              <div>
                <h3 className="mb-3 text-sm font-semibold text-red-200">Maps Banned</h3>
                {bansPicks.bans.length > 0 ? (
                  <div className="space-y-2">
                    {bansPicks.bans.map((ban, index) => (
                      <motion.div
                        key={`ban-${ban.map}`}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="flex items-center justify-between rounded-lg border border-red-300/20 bg-red-500/10 p-3"
                      >
                        <span className="font-medium text-white capitalize">{ban.map}</span>
                        <span className="rounded-full border border-red-300/40 bg-red-500/20 px-2 py-1 text-xs text-red-100">
                          {ban.count} time{ban.count !== 1 ? 's' : ''}
                        </span>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-white/50">No map bans in this period</p>
                )}
              </div>

              {/* Picks */}
              <div>
                <h3 className="mb-3 text-sm font-semibold text-emerald-200">Maps Picked</h3>
                {bansPicks.picks.length > 0 ? (
                  <div className="space-y-2">
                    {bansPicks.picks.map((pick, index) => (
                      <motion.div
                        key={`pick-${pick.map}`}
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="flex items-center justify-between rounded-lg border border-emerald-300/20 bg-emerald-500/10 p-3"
                      >
                        <span className="font-medium text-white capitalize">{pick.map}</span>
                        <span className="rounded-full border border-emerald-300/40 bg-emerald-500/20 px-2 py-1 text-xs text-emerald-100">
                          {pick.count} time{pick.count !== 1 ? 's' : ''}
                        </span>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-white/50">No map picks in this period</p>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Map Winrates */}
      {bansPicks && bansPicks.map_winrates && bansPicks.map_winrates.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-6"
        >
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
            <h2 className="mb-1 flex items-center text-2xl font-semibold">
              <Trophy className="mr-2 h-5 w-5 text-blue-200" />
              Map Performance
            </h2>
            <p className="mb-6 text-sm text-white/60">
              Click any map to view detailed match history
            </p>

            <div className="space-y-3">
              {bansPicks.map_winrates.map((mapWR, index) => {
                const isExpanded = expandedMap === mapWR.map;
                const mapImageName = mapWR.map.toLowerCase().replace(/\s+/g, '-');
                const mapImagePath = `/api/image?name=valorant-${mapImageName}-map.png`;
                
                return (
                  <motion.div
                    key={`map-${mapWR.map}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={`group rounded-2xl border overflow-hidden transition-all relative ${
                      isExpanded 
                        ? 'border-blue-300/40' 
                        : 'border-blue-300/20'
                    }`}
                    style={{
                      backgroundImage: `url('${mapImagePath}')`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    }}
                  >
                    {/* Overlay for background image */}
                    <div className="absolute inset-0 bg-black/40" />

                    <motion.button
                      onClick={() => setExpandedMap(isExpanded ? null : mapWR.map)}
                      className="w-full text-left relative transition-all"
                    >
                      {/* Content */}
                      <div className="relative p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h3 className="text-lg font-semibold text-white capitalize">{mapWR.map}</h3>
                            <p className="text-xs text-white/60">{mapWR.total} maps</p>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className={`relative h-20 w-20 rounded-full border-4 flex items-center justify-center font-bold text-xl ${
                              mapWR.winPercent >= 60 ? 'border-emerald-400 bg-emerald-500/20 text-emerald-200' :
                              mapWR.winPercent >= 40 ? 'border-blue-400 bg-blue-500/20 text-blue-200' :
                              'border-red-400 bg-red-500/20 text-red-200'
                            }`}>
                              {mapWR.winPercent}%
                            </div>
                            <motion.div
                              animate={{ rotate: isExpanded ? 180 : 0 }}
                              transition={{ duration: 0.2 }}
                            >
                              <ChevronDown className="h-5 w-5 text-blue-200" />
                            </motion.div>
                          </div>
                        </div>

                        {/* Stats */}
                        <div className="text-sm text-white/80">
                          <span className="font-semibold text-white">{mapWR.wins}W - {mapWR.losses}L</span> ({mapWR.total} total)
                        </div>
                      </div>
                    </motion.button>

                    {/* Expanded Content */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.3 }}
                          className="overflow-hidden border-t border-blue-300/20 relative"
                        >
                          <div className="relative p-4">
                            <h4 className="text-sm font-semibold text-blue-200 mb-4">Match History</h4>
                            {mapWR.matches && mapWR.matches.length > 0 ? (
                              <div className="space-y-2 max-h-64 overflow-y-auto">
                                {mapWR.matches.map((match, idx) => (
                                  <Link
                                    key={`${mapWR.map}-match-${idx}`}
                                    href={`/matches/${match.match_id}`}
                                    className="block p-3 rounded-lg border border-blue-300/20 bg-blue-500/10 hover:bg-blue-500/20 transition-colors group/match"
                                  >
                                    <div className="flex items-center justify-between">
                                      <span className="text-sm text-white/80 capitalize group-hover/match:text-white transition-colors">{match.opponent}</span>
                                      <span className={`text-sm font-bold px-3 py-1 rounded-lg ${
                                        match.result === 'W' 
                                          ? 'bg-emerald-500/30 text-emerald-100' 
                                          : 'bg-red-500/30 text-red-100'
                                      }`}>
                                        {match.result} {match.scoreline}
                                      </span>
                                    </div>
                                    <div className="text-xs text-white/50 mt-1">{match.date}</div>
                                  </Link>
                                ))}
                              </div>
                            ) : (
                              <p className="text-sm text-white/50">No match data available</p>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </motion.div>
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
