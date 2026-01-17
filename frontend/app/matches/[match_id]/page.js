'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowLeft, Trophy, MapPin, TrendingUp } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

// Helper function to clean map names - remove leading numbers, 'pick', timestamps, etc.
function cleanMapName(mapName) {
  if (!mapName) return mapName
  let cleaned = mapName
    .replace(/^\d+\s*-?\s*/, '')  // Remove leading numbers
    .replace(/\s*\(pick\)/gi, '')  // Remove (pick)
    .replace(/\s*pick\s*$/gi, '')  // Remove trailing 'pick'
    .replace(/\s*\d{1,2}:\d{2}\s*(AM|PM)?/gi, '')  // Remove timestamps
    .trim()
  return cleaned
}

// Helper function to group stats by team
function groupStatsByTeam(stats, team1Name, team2Name) {
  const team1Stats = stats.filter(stat => stat.team_name === team1Name)
  const team2Stats = stats.filter(stat => stat.team_name === team2Name)
  const unknownStats = stats.filter(stat => !stat.team_name || (stat.team_name !== team1Name && stat.team_name !== team2Name))
  return { team1Stats, team2Stats, unknownStats }
}

function StatsTable({ rows, showAgents = false, maxAgentsPerPlayer = 1 }) {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'desc' })

  const handleSort = (key) => {
    let direction = 'desc'
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc'
    }
    setSortConfig({ key, direction })
  }

  const sortedRows = [...rows].sort((a, b) => {
    if (!sortConfig.key) return 0
    
    const aVal = a[sortConfig.key] ?? 0
    const bVal = b[sortConfig.key] ?? 0
    
    if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
    if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
    return 0
  })

  const SortableHeader = ({ label, sortKey }) => (
    <th 
      className="px-3 text-left cursor-pointer hover:text-white transition-colors select-none"
      onClick={() => handleSort(sortKey)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortConfig.key === sortKey && (
          <span className="text-emerald-300">
            {sortConfig.direction === 'asc' ? '↑' : '↓'}
          </span>
        )}
      </div>
    </th>
  )

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/20">
      <table className="w-full text-sm">
        <thead className="bg-white/5 text-xs uppercase tracking-wide text-white/60">
          <tr className="h-9">
            <th className="px-3 text-left">Player</th>
            <SortableHeader label="K" sortKey="kills" />
            <SortableHeader label="D" sortKey="deaths" />
            <SortableHeader label="A" sortKey="assists" />
            <SortableHeader label="ACS" sortKey="acs" />
            <SortableHeader label="FK" sortKey="first_kills" />
            <SortableHeader label="FD" sortKey="first_deaths" />
            <SortableHeader label="Rating" sortKey="rating" />
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((stat, index) => {
            // Handle multiple agents per player (for match totals)
            const agents = stat.agents || (stat.agent ? [stat.agent] : [])
            const agentIcons = agents.map(agent => 
              agent ? `/images/${agent.toLowerCase()}.png` : null
            ).filter(Boolean)
            
            return (
              <motion.tr
                key={stat.stat_id || `${stat.player_name}-${index}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.02 }}
                className="h-9 border-b border-white/5 text-white/80 hover:bg-white/5"
              >
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    {showAgents && (
                      <div className="flex items-center gap-0.5">
                        {agentIcons.map((icon, i) => (
                          <img
                            key={i}
                            src={icon}
                            alt={agents[i]}
                            className="h-5 w-5 rounded-sm object-contain"
                            title={agents[i]}
                          />
                        ))}
                        {/* Padding with empty space for alignment */}
                        {Array.from({ length: maxAgentsPerPlayer - agentIcons.length }).map((_, i) => (
                          <div key={`pad-${i}`} className="h-5 w-5" />
                        ))}
                      </div>
                    )}
                    <span className="text-sm font-medium text-white">{stat.player_name}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-sm">{stat.kills}</td>
                <td className="px-3 py-2 text-sm">{stat.deaths}</td>
                <td className="px-3 py-2 text-sm">{stat.assists}</td>
                <td className="px-3 py-2 text-sm">{stat.acs}</td>
                <td className="px-3 py-2 text-sm text-emerald-300">{stat.first_kills || 0}</td>
                <td className="px-3 py-2 text-sm text-red-300">{stat.first_deaths || 0}</td>
                <td className="px-3 py-2">
                  <span className={`rounded-full border px-2 py-0.5 text-xs ${
                    stat.rating >= 1.0
                      ? 'border-emerald-300/40 bg-emerald-500/10 text-emerald-100'
                      : 'border-white/10 bg-white/5 text-white/70'
                  }`}>
                    {stat.rating?.toFixed(2) || 'N/A'}
                  </span>
                </td>
              </motion.tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function MatchDetailsPage() {
  const params = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedMapId, setSelectedMapId] = useState(null)
  const [activeTab, setActiveTab] = useState('maps')

  useEffect(() => {
    async function fetchMatchDetails() {
      try {
        let matchData
        try {
          matchData = await fetchJson(`/api/matches/${params.match_id}`)
        } catch (err) {
          if (err?.message?.includes('404')) {
            setError('Match not found')
            return
          }
          throw err
        }
        setData(matchData)
        // Set initial selected map
        if (matchData.maps && matchData.maps.length > 0) {
          const firstMap = matchData.maps[0]
          setSelectedMapId(firstMap.map_id || firstMap.id)
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchMatchDetails()
  }, [params.match_id])

  if (loading) {
    return (
      <div className="container py-6">
        <div className="flex min-h-[300px] items-center justify-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="h-6 w-6 rounded-full border-2 border-emerald-300/70 border-t-transparent"
          />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="container py-6">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h2 className="text-lg font-semibold text-white">Error</h2>
          <p className="mt-2 text-sm text-white/60">{error || 'Match not found'}</p>
          <Link
            href="/matches"
            className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white/80 hover:border-white/30 hover:bg-white/10"
          >
            <ArrowLeft className="h-3 w-3" />
            Back to Matches
          </Link>
        </div>
      </div>
    )
  }

  const { match, maps, playerStats } = data
  const winner = match.team1_score > match.team2_score ? 1 : match.team2_score > match.team1_score ? 2 : null
  const selectedMap = maps.find(m => (m.map_id || m.id) === selectedMapId) || (maps.length > 0 ? maps[0] : null)
  
  // Check if any player stats have agent data
  const hasAgentData = playerStats?.some(s => s.agent) || maps?.some(m => m.playerStats?.some(s => s.agent))
  
  // Aggregate agents per player from all maps for match totals
  const playerAgentMap = new Map()
  const allAgentsUsed = new Set()
  if (hasAgentData && maps) {
    maps.forEach(map => {
      map.playerStats?.forEach(stat => {
        if (stat.player && stat.agent) {
          const key = stat.player
          if (!playerAgentMap.has(key)) {
            playerAgentMap.set(key, new Set())
          }
          playerAgentMap.get(key).add(stat.agent)
          allAgentsUsed.add(stat.agent)
        }
      })
    })
  }
  
  // Find max agents any player used
  const maxAgentsPerPlayer = Math.max(1, ...Array.from(playerAgentMap.values()).map(agents => agents.size))
  
  // Get all unique agents used across all maps in the match
  const uniqueAgents = hasAgentData ? Array.from(allAgentsUsed).sort() : []
  
  // Enhance playerStats with aggregated agents for match totals
  const enhancedPlayerStats = playerStats?.map(stat => {
    const agents = playerAgentMap.get(stat.player)
    return {
      ...stat,
      agents: agents ? Array.from(agents).sort() : (stat.agent ? [stat.agent] : [])
    }
  }) || []

  return (
    <div className="container py-6 max-w-7xl">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <Link
          href="/matches"
          className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white/80 hover:border-white/30 hover:bg-white/10"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to Matches
        </Link>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight mb-1">
              <span className="inline-flex items-center gap-2">
                {match.team1_logo ? (
                  <img
                    src={match.team1_logo}
                    alt={`${match.team1_name} logo`}
                    className="h-8 w-8 bg-white/5 object-contain"
                  />
                ) : null}
                {match.team1_name}
              </span>
              <span className={`mx-3 text-xl font-bold ${winner === 1 ? 'text-emerald-200' : winner === 2 ? 'text-white' : 'text-white/60'}`}>
                {match.team1_score}
              </span>
              <span className="mx-2 text-white/40">-</span>
              <span className={`mx-3 text-xl font-bold ${winner === 2 ? 'text-emerald-200' : winner === 1 ? 'text-white' : 'text-white/60'}`}>
                {match.team2_score}
              </span>
              <span className="inline-flex items-center gap-2">
                {match.team2_logo ? (
                  <img
                    src={match.team2_logo}
                    alt={`${match.team2_name} logo`}
                    className="h-8 w-8 bg-white/5 object-contain"
                  />
                ) : null}
                {match.team2_name}
              </span>
            </h1>
            <p className="text-sm text-white/60">
              Match{" "}
              <a
                href={`https://www.vlr.gg/${match.match_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-emerald-200"
              >
                #{match.match_id}
              </a>
            </p>
          </div>
          {winner && (
            <span className="inline-flex items-center rounded-full border border-emerald-300/30 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-100">
              <Trophy className="mr-1 h-3 w-3" />
              {winner === 1 ? match.team1_name : match.team2_name} Wins
            </span>
          )}
        </div>
      </motion.div>

      {/* Score Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-6"
      >
        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
          <h2 className="text-lg font-semibold text-white">Final Score</h2>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2 }}
              className={`rounded-2xl p-4 text-center ${
                winner === 1 ? 'border border-emerald-300/40 bg-emerald-500/10' : 'border border-white/10 bg-white/5'
              }`}
            >
              {match.team1_logo ? (
                <img
                  src={match.team1_logo}
                  alt={`${match.team1_name} logo`}
                  className="mx-auto mb-2 h-8 w-8 bg-white/5 object-contain"
                />
              ) : null}
              <div className={`mb-1 text-3xl font-semibold ${winner === 1 ? 'text-emerald-200' : 'text-white'}`}>
                {match.team1_score}
              </div>
              <div className="text-sm font-semibold text-white/80">{match.team1_name}</div>
              <Link
                href={`/teams/${encodeURIComponent(match.team1_name)}`}
                className="mt-3 inline-flex items-center gap-1 rounded-lg border border-white/20 bg-white/5 px-3 py-1.5 text-xs font-medium text-white/80 transition-all hover:border-emerald-300/40 hover:bg-emerald-500/10 hover:text-emerald-200"
              >
                View Roster
              </Link>
            </motion.div>
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.3 }}
              className={`rounded-2xl p-4 text-center ${
                winner === 2 ? 'border border-emerald-300/40 bg-emerald-500/10' : 'border border-white/10 bg-white/5'
              }`}
            >
              {match.team2_logo ? (
                <img
                  src={match.team2_logo}
                  alt={`${match.team2_name} logo`}
                  className="mx-auto mb-2 h-8 w-8 bg-white/5 object-contain"
                />
              ) : null}
              <div className={`mb-1 text-3xl font-semibold ${winner === 2 ? 'text-emerald-200' : 'text-white'}`}>
                {match.team2_score}
              </div>
              <div className="text-sm font-semibold text-white/80">{match.team2_name}</div>
              <Link
                href={`/teams/${encodeURIComponent(match.team2_name)}`}
                className="mt-3 inline-flex items-center gap-1 rounded-lg border border-white/20 bg-white/5 px-3 py-1.5 text-xs font-medium text-white/80 transition-all hover:border-emerald-300/40 hover:bg-emerald-500/10 hover:text-emerald-200"
              >
                View Roster
              </Link>
            </motion.div>
          </div>

          {/* Bans/Picks Display */}
          {match.bans_picks && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4"
            >
              <h3 className="mb-2 text-sm font-semibold text-white/80">Map Vetoes</h3>
              <p className="text-sm text-white/60">{match.bans_picks}</p>
            </motion.div>
          )}
        </div>
      </motion.div>

      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1">
          <button
            type="button"
            onClick={() => setActiveTab('maps')}
            className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
              activeTab === 'maps' ? 'bg-emerald-500/20 text-emerald-100' : 'text-white/60 hover:text-white'
            }`}
          >
            <MapPin className="h-3.5 w-3.5" />
            Maps ({maps.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('totals')}
            className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
              activeTab === 'totals' ? 'bg-emerald-500/20 text-emerald-100' : 'text-white/60 hover:text-white'
            }`}
          >
            <TrendingUp className="h-3.5 w-3.5" />
            Match Totals
          </button>
        </div>

        {activeTab === 'maps' && (
          <div className="space-y-4">
            {maps.length > 0 && (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  {maps.map((map) => {
                    const cleanName = cleanMapName(map.map_name || map.map)
                    const mapId = map.map_id || map.id
                    if (!mapId) {
                      return null
                    }
                    const team1Score = map.team1_score || map.team_a_score || 0
                    const team2Score = map.team2_score || map.team_b_score || 0
                    const isSelected = selectedMapId === mapId
                    return (
                      <button
                        key={mapId}
                        type="button"
                        onClick={() => setSelectedMapId(mapId)}
                        className={`rounded-full border px-4 py-2 text-sm font-medium transition-all ${
                          isSelected
                            ? 'border-emerald-300/40 bg-emerald-500/20 text-emerald-100 shadow-[0_0_15px_rgba(16,185,129,0.3)]'
                            : 'border-white/20 bg-white/5 text-white/80 hover:border-white/30 hover:bg-white/10'
                        }`}
                      >
                        {cleanName}
                        <span className="ml-2 text-xs opacity-70">
                          {team1Score}-{team2Score}
                        </span>
                      </button>
                    )
                  }).filter(Boolean)}
                </div>

                {selectedMap && (() => {
                  const map = selectedMap
                  const mapId = map.map_id || map.id
                  const mapIndex = maps.findIndex(m => (m.map_id || m.id) === mapId)
                  const team1Score = map.team1_score || map.team_a_score || 0
                  const team2Score = map.team2_score || map.team_b_score || 0
                  const mapWinner = team1Score > team2Score ? 1 : team2Score > team1Score ? 2 : null
                  const { team1Stats, team2Stats, unknownStats } = groupStatsByTeam(
                    map.playerStats || [],
                    map.team1_name || match.team1_name,
                    map.team2_name || match.team2_name
                  )
                  const cleanName = cleanMapName(map.map_name || map.map)

                  return (
                    <motion.div
                      key={mapId}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: mapIndex * 0.05 }}
                      className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-[0_10px_30px_rgba(0,0,0,0.35)]"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <h3 className="text-lg font-semibold text-white">{cleanName}</h3>
                          <p className="text-xs text-white/50">
                            {map.team1_name || match.team1_name} {team1Score} - {team2Score} {map.team2_name || match.team2_name}
                          </p>
                        </div>
                        {mapWinner && (
                          <span className="rounded-full border border-emerald-300/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-100">
                            {mapWinner === 1 ? (map.team1_name || match.team1_name) : (map.team2_name || match.team2_name)} Wins
                          </span>
                        )}
                      </div>

                      <div className="mt-4 space-y-4">
                        {team1Stats.length > 0 && (
                          <div>
                            <h4 className="mb-2 text-sm font-semibold text-emerald-200">{map.team1_name || match.team1_name}</h4>
                            <StatsTable rows={team1Stats} showAgents={hasAgentData} />
                          </div>
                        )}

                        {team2Stats.length > 0 && (
                          <div>
                            <h4 className="mb-2 text-sm font-semibold text-white/80">{map.team2_name || match.team2_name}</h4>
                            <StatsTable rows={team2Stats} showAgents={hasAgentData} />
                          </div>
                        )}

                        {unknownStats.length > 0 && (
                          <div>
                            <h4 className="mb-2 text-sm font-semibold text-white/70">Unassigned Players</h4>
                            <StatsTable rows={unknownStats} showAgents={hasAgentData} />
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )
                })()}
              </>
            )}

            {maps.length === 0 && (
              <div className="rounded-2xl border border-white/10 bg-white/5 py-8 text-center text-white/60">
                No maps available for this match.
              </div>
            )}
          </div>
        )}

        {activeTab === 'totals' && (
          <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
            <div className="border-b border-white/10 pb-4">
              <h3 className="text-lg font-semibold text-white">Match Totals</h3>
              <p className="text-xs text-white/50">Overall player statistics for the entire match</p>
            </div>
            <div className="mt-4 space-y-4">
              {(() => {
                const { team1Stats, team2Stats, unknownStats } = groupStatsByTeam(
                  enhancedPlayerStats || [],
                  match.team1_name,
                  match.team2_name
                )

                const hasStats = team1Stats.length > 0 || team2Stats.length > 0 || unknownStats.length > 0

                if (!hasStats) {
                  return (
                    <div className="py-8 text-center text-white/60">
                      No match totals available. Stats are shown per map above.
                    </div>
                  )
                }

                return (
                  <>
                    {team1Stats.length > 0 && (
                      <div>
                        <h4 className="mb-2 text-sm font-semibold text-emerald-200">{match.team1_name}</h4>
                        <StatsTable rows={team1Stats} showAgents={hasAgentData} maxAgentsPerPlayer={maxAgentsPerPlayer} />
                      </div>
                    )}

                    {team2Stats.length > 0 && (
                      <div>
                        <h4 className="mb-2 text-sm font-semibold text-white/80">{match.team2_name}</h4>
                        <StatsTable rows={team2Stats} showAgents={hasAgentData} maxAgentsPerPlayer={maxAgentsPerPlayer} />
                      </div>
                    )}

                    {unknownStats.length > 0 && (
                      <div>
                        <h4 className="mb-2 text-sm font-semibold text-white/70">Unassigned Players</h4>
                        <StatsTable rows={unknownStats} showAgents={hasAgentData} maxAgentsPerPlayer={maxAgentsPerPlayer} />
                      </div>
                    )}
                  </>
                )
              })()}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
