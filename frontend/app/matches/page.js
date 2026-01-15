'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ChevronRight, Calendar, Trophy } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

const REGION_ORDER = ['AMERICAS', 'EMEA', 'APAC', 'CHINA']
const REGION_LABELS = {
  AMERICAS: 'Americas',
  EMEA: 'EMEA',
  APAC: 'APAC',
  CHINA: 'China',
}

const REGIONAL_STAGES = ['Kickoff', 'Stage 1', 'Stage 2']

const getMatchDate = (match) => {
  const raw = match.match_date || match.match_ts_utc
  if (!raw) return null
  const date = new Date(raw)
  return isNaN(date.getTime()) ? null : date
}

const formatMatchDate = (match) => {
  const date = getMatchDate(match)
  if (!date) {
    const raw = match.match_date || match.match_ts_utc
    return raw ? raw.substring(0, 10) : '-'
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const getRegionalStage = (tournament) => {
  const tLower = (tournament || '').toLowerCase()
  if (tLower.includes('kickoff')) return 'Kickoff'
  if (tLower.includes('stage 1')) return 'Stage 1'
  if (tLower.includes('stage 2')) return 'Stage 2'
  return null
}

const isPlayoffsMatch = (match) => {
  const stage = (match.stage || '').toLowerCase()
  const matchType = (match.match_type || '').toLowerCase()
  return (
    stage.includes('playoff') ||
    stage.includes('bracket') ||
    stage.includes('final') ||
    matchType.includes('playoff') ||
    matchType.includes('final')
  )
}

function MatchTable({ matches }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/20">
      <table className="w-full text-sm">
        <thead className="bg-white/5 text-xs font-semibold uppercase tracking-wide text-white/60">
          <tr className="h-11">
            <th className="px-4 text-left w-24">ID</th>
            <th className="px-4 text-left">Team 1</th>
            <th className="px-4 text-center w-28">Score</th>
            <th className="px-4 text-left">Team 2</th>
            <th className="px-4 text-left w-32">Stage</th>
            <th className="px-4 text-left w-28">Date</th>
            <th className="px-4 text-left w-24"></th>
          </tr>
        </thead>
        <tbody>
          {matches.map((match, index) => {
            const winner =
              match.team1_score > match.team2_score
                ? 1
                : match.team2_score > match.team1_score
                  ? 2
                  : null

            return (
              <motion.tr
                key={match.match_id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.02 }}
                className="h-12 border-b border-white/5 transition-colors hover:bg-white/5"
              >
                <td className="px-4 py-3 text-xs font-mono text-white/50">
                  <a
                    href={`https://www.vlr.gg/${match.match_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-emerald-200 hover:underline"
                  >
                    {match.match_id}
                  </a>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {match.team1_logo ? (
                      <img
                        src={match.team1_logo}
                        alt={`${match.team1_name} logo`}
                        className="h-5 w-5 bg-white/5 object-contain"
                      />
                    ) : null}
                    <span className={`text-sm font-medium ${winner === 1 ? 'text-emerald-200 font-semibold' : 'text-white'}`}>
                      {match.team1_name}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex items-center justify-center space-x-2">
                    <span className={`text-sm font-bold ${winner === 1 ? 'text-emerald-200' : 'text-white'}`}>
                      {match.team1_score}
                    </span>
                    <span className="text-xs text-white/50">-</span>
                    <span className={`text-sm font-bold ${winner === 2 ? 'text-emerald-200' : 'text-white'}`}>
                      {match.team2_score}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {match.team2_logo ? (
                      <img
                        src={match.team2_logo}
                        alt={`${match.team2_name} logo`}
                        className="h-5 w-5 bg-white/5 object-contain"
                      />
                    ) : null}
                    <span className={`text-sm font-medium ${winner === 2 ? 'text-emerald-200 font-semibold' : 'text-white'}`}>
                      {match.team2_name}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-full border border-white/15 bg-white/5 px-2 py-1 text-xs text-white/60">
                    {match.stage || '-'}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-white/60">{formatMatchDate(match)}</td>
                <td className="px-4 py-3">
                  <Link
                    href={`/matches/${match.match_id}`}
                    className="inline-flex items-center gap-1 text-xs font-medium text-emerald-200 transition-colors hover:text-emerald-100 hover:underline"
                  >
                    View
                    <ChevronRight className="h-3 w-3" />
                  </Link>
                </td>
              </motion.tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function MatchesPage() {
  const [data, setData] = useState({ matches: [], grouped: {}, groupedByYear: {} })
  const [loading, setLoading] = useState(true)
  const [selectedYear, setSelectedYear] = useState(null)
  const [expandedEvents, setExpandedEvents] = useState({})

  useEffect(() => {
    async function fetchMatches() {
      try {
        const data = await fetchJson('/api/matches')
        setData(data)
      } catch (error) {
        console.error(error)
      } finally {
        setLoading(false)
      }
    }
    fetchMatches()
  }, [])

  const toggleEvent = (eventKey) => {
    setExpandedEvents(prev => ({
      ...prev,
      [eventKey]: !prev[eventKey]
    }))
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

  const years = [2026, 2025, 2024]
  const allMatches = data.matches || []

  // If a year is selected, show events for that year
  if (selectedYear !== null) {
    const yearMatches = allMatches.filter((match) => match.year === selectedYear)
    const regionalBuckets = REGION_ORDER.reduce((acc, region) => {
      acc[region] = {
        Kickoff: [],
        'Stage 1': [],
        'Stage 2': [],
      }
      return acc
    }, {})
    const mastersEvents = {}
    const championsEvents = {}

    yearMatches.forEach((match) => {
      const tLower = (match.tournament || '').toLowerCase()
      const isChampionsMain = tLower.includes('champions') && !tLower.includes('champions tour')
      if (tLower.includes('masters')) {
        if (!mastersEvents[match.tournament]) {
          mastersEvents[match.tournament] = {
            logo: match.event_logo,
            group: [],
            playoffs: [],
          }
        }
        const bucket = isPlayoffsMatch(match) ? 'playoffs' : 'group'
        mastersEvents[match.tournament][bucket].push(match)
        return
      }
      if (isChampionsMain) {
        if (!championsEvents[match.tournament]) {
          championsEvents[match.tournament] = {
            logo: match.event_logo,
            matches: [],
          }
        }
        championsEvents[match.tournament].matches.push(match)
        return
      }
      if (REGION_ORDER.includes(match.region)) {
        const stage = getRegionalStage(match.tournament)
        if (stage) {
          regionalBuckets[match.region][stage].push(match)
        }
      }
    })

    const hasRegional = REGION_ORDER.some((region) =>
      REGIONAL_STAGES.some((stage) => regionalBuckets[region][stage].length > 0)
    )
    const hasMasters = Object.keys(mastersEvents).length > 0
    const hasChampions = Object.keys(championsEvents).length > 0

    return (
      <div className="container py-6 max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <button
            onClick={() => setSelectedYear(null)}
            className="mb-4 flex items-center gap-2 text-sm text-white/60 transition-colors hover:text-white"
          >
            <ChevronRight className="h-4 w-4 rotate-180" />
            Back to Years
          </button>
          <h1 className="text-3xl font-semibold tracking-tight mb-2">VCT {selectedYear}</h1>
          <p className="text-sm text-white/60">
            Browse all Valorant esports matches for {selectedYear}
          </p>
        </motion.div>

        {(hasMasters || hasChampions) && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white/80">International Events</h2>
            {Object.entries(mastersEvents).map(([eventName, event]) => {
              const key = `masters-${eventName}`
              const isExpanded = expandedEvents[key]
              const groupMatches = [...event.group].sort(
                (a, b) => (getMatchDate(a)?.getTime() || 0) - (getMatchDate(b)?.getTime() || 0)
              )
              const playoffMatches = [...event.playoffs].sort(
                (a, b) => (getMatchDate(a)?.getTime() || 0) - (getMatchDate(b)?.getTime() || 0)
              )

              return (
                <motion.div
                  key={eventName}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="overflow-hidden rounded-2xl border border-white/10 bg-white/5 shadow-[0_12px_35px_rgba(0,0,0,0.35)]"
                >
                  <button
                    onClick={() => toggleEvent(key)}
                    className="flex w-full items-center justify-between gap-4 border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent px-6 py-4 transition-all hover:from-white/10 group"
                  >
                    <div className="flex items-center gap-4">
                      <ChevronRight
                        className={`h-5 w-5 transition-transform text-white/60 group-hover:text-white ${isExpanded ? 'rotate-90' : ''}`}
                      />
                      {event.logo ? (
                        <img src={event.logo} alt={`${eventName} logo`} className="h-7 w-7 bg-white/5 object-contain" />
                      ) : (
                        <Calendar className="h-5 w-5 text-white/60 group-hover:text-emerald-200 transition-colors" />
                      )}
                      <div className="text-left">
                        <h3 className="text-lg font-semibold text-white">{eventName}</h3>
                        <p className="mt-0.5 text-xs text-white/50">
                          {groupMatches.length + playoffMatches.length} matches
                        </p>
                      </div>
                    </div>
                    <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs text-white/70">
                      {groupMatches.length + playoffMatches.length}
                    </span>
                  </button>

                  {isExpanded && (
                    <div className="space-y-6 px-6 pb-6 pt-4">
                      <div>
                        <h4 className="mb-3 text-sm font-semibold text-white/70">Group Stage</h4>
                        {groupMatches.length > 0 ? (
                          <MatchTable matches={groupMatches} />
                        ) : (
                          <p className="text-sm text-white/50">No group stage matches yet.</p>
                        )}
                      </div>
                      <div>
                        <h4 className="mb-3 text-sm font-semibold text-white/70">Playoffs</h4>
                        {playoffMatches.length > 0 ? (
                          <MatchTable matches={playoffMatches} />
                        ) : (
                          <p className="text-sm text-white/50">No playoff matches yet.</p>
                        )}
                      </div>
                    </div>
                  )}
                </motion.div>
              )
            })}

            {Object.entries(championsEvents).map(([eventName, event]) => {
              const key = `champions-${eventName}`
              const isExpanded = expandedEvents[key]
              const matches = [...event.matches].sort(
                (a, b) => (getMatchDate(a)?.getTime() || 0) - (getMatchDate(b)?.getTime() || 0)
              )
              return (
                <motion.div
                  key={eventName}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="overflow-hidden rounded-2xl border border-white/10 bg-white/5 shadow-[0_12px_35px_rgba(0,0,0,0.35)]"
                >
                  <button
                    onClick={() => toggleEvent(key)}
                    className="flex w-full items-center justify-between gap-4 border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent px-6 py-4 transition-all hover:from-white/10 group"
                  >
                    <div className="flex items-center gap-4">
                      <ChevronRight
                        className={`h-5 w-5 transition-transform text-white/60 group-hover:text-white ${isExpanded ? 'rotate-90' : ''}`}
                      />
                      {event.logo ? (
                        <img src={event.logo} alt={`${eventName} logo`} className="h-7 w-7 bg-white/5 object-contain" />
                      ) : (
                        <Calendar className="h-5 w-5 text-white/60 group-hover:text-emerald-200 transition-colors" />
                      )}
                      <div className="text-left">
                        <h3 className="text-lg font-semibold text-white">{eventName}</h3>
                        <p className="mt-0.5 text-xs text-white/50">
                          {matches.length} match{matches.length !== 1 ? 'es' : ''}
                        </p>
                      </div>
                    </div>
                    <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs text-white/70">
                      {matches.length}
                    </span>
                  </button>
                  {isExpanded && (
                    <div className="px-6 pb-6 pt-4">
                      <MatchTable matches={matches} />
                    </div>
                  )}
                </motion.div>
              )
            })}
          </div>
        )}

        {hasRegional && (
          <div className="mt-8 space-y-6">
            <h2 className="text-lg font-semibold text-white/80">Regional Leagues</h2>
            {REGION_ORDER.map((region) => {
              const stages = regionalBuckets[region]
              const regionMatches = REGIONAL_STAGES.flatMap((stage) => stages[stage])
              if (regionMatches.length === 0) return null
              const regionLogo = regionMatches[0]?.event_logo

              return (
                <motion.div
                  key={region}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-3xl border border-white/10 bg-white/5 p-5"
                >
                  <div className="flex items-center gap-3 border-b border-white/10 pb-4">
                    {regionLogo ? (
                      <img src={regionLogo} alt={`${REGION_LABELS[region]} logo`} className="h-8 w-8 bg-white/5 object-contain" />
                    ) : (
                      <Calendar className="h-5 w-5 text-white/60" />
                    )}
                    <h3 className="text-lg font-semibold text-white">{REGION_LABELS[region] || region}</h3>
                  </div>
                  <div className="mt-5 grid gap-4 md:grid-cols-3">
                    {REGIONAL_STAGES.map((stage) => {
                      const matches = stages[stage]
                      const key = `${region}-${stage}`
                      const isExpanded = expandedEvents[key]
                      const sortedMatches = [...matches].sort(
                        (a, b) => (getMatchDate(a)?.getTime() || 0) - (getMatchDate(b)?.getTime() || 0)
                      )

                      return (
                        <div key={stage} className="rounded-2xl border border-white/10 bg-black/20">
                          <button
                            onClick={() => toggleEvent(key)}
                            className="flex w-full items-center justify-between gap-2 border-b border-white/10 px-4 py-3"
                          >
                            <div className="text-left">
                              <p className="text-sm font-semibold text-white">{stage}</p>
                              <p className="text-xs text-white/50">{matches.length} matches</p>
                            </div>
                            <ChevronRight
                              className={`h-4 w-4 text-white/60 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                            />
                          </button>
                          {isExpanded && (
                            <div className="p-4">
                              {sortedMatches.length > 0 ? (
                                <MatchTable matches={sortedMatches} />
                              ) : (
                                <p className="text-sm text-white/50">No matches yet.</p>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}

        {!hasRegional && !hasMasters && !hasChampions && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="py-12 text-center"
          >
            <p className="text-white/60">No events found for {selectedYear}.</p>
          </motion.div>
        )}
      </div>
    )
  }

  // Show year selection boxes
  return (
    <div className="container py-6 max-w-7xl">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-semibold tracking-tight mb-2">Matches</h1>
        <p className="text-sm text-white/60">
          Select a year to browse Valorant esports matches
        </p>
      </motion.div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {years.map((year, index) => {
          const yearMatches = allMatches.filter((match) => match.year === year)
          const totalMatches = yearMatches.length
          const eventCount = new Set(yearMatches.map((match) => match.tournament)).size
          const isEmpty = eventCount === 0

          return (
            <motion.button
              key={year}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              onClick={() => !isEmpty && setSelectedYear(year)}
              className={`text-left rounded-3xl border px-6 py-5 transition-all ${
                isEmpty
                  ? 'cursor-not-allowed border-white/5 bg-white/5 text-white/40'
                  : 'border-white/10 bg-white/5 text-white hover:-translate-y-1 hover:border-emerald-300/40 hover:bg-white/10'
              }`}
              disabled={isEmpty}
            >
              <div className="flex items-center justify-between">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-300/30 bg-emerald-500/10">
                  <Trophy className="h-6 w-6 text-emerald-200" />
                </div>
                {isEmpty && (
                  <span className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs">
                    Empty
                  </span>
                )}
              </div>
              <h2 className="mt-4 text-2xl font-semibold">VCT {year}</h2>
              <p className="mt-2 text-sm text-white/60">
                {isEmpty ? 'No matches available' : `${eventCount} event${eventCount !== 1 ? 's' : ''} • ${totalMatches} matches`}
              </p>
              {!isEmpty && (
                <div className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-emerald-200">
                  View Events
                  <ChevronRight className="h-4 w-4" />
                </div>
              )}
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
