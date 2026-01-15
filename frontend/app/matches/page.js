'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ChevronRight, Calendar, Trophy } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

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

  const formatEventName = (eventKey) => {
    if (eventKey.includes(' - ')) {
      const parts = eventKey.split(' - ')
      if (parts.length === 3) {
        const yearMatch = parts[0].match(/\b(202[0-9]|203[0-9])\b/);
        const year = yearMatch ? yearMatch[1] : '';
        const stage = parts[1];
        const region = parts[2];
        return `${year} ${stage} - ${region}`;
      }
    }
    return eventKey;
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
  const groupedByYear = data.groupedByYear || {}

  // If a year is selected, show events for that year
  if (selectedYear !== null) {
    const yearEvents = groupedByYear[selectedYear] || {}
    const eventKeys = Object.keys(yearEvents).sort((a, b) => {
      const matchesA = yearEvents[a] || []
      const matchesB = yearEvents[b] || []

      // Helper to get the earliest match date in an event
      const getEarliestDate = (matches) => {
        let earliest = null
        for (const m of matches) {
          const raw = m.match_date || m.match_ts_utc
          if (!raw) continue
          const d = new Date(raw)
          if (isNaN(d.getTime())) continue
          if (!earliest || d < earliest) earliest = d
        }
        return earliest
      }

      const dateA = getEarliestDate(matchesA)
      const dateB = getEarliestDate(matchesB)

      // If both have valid dates, sort by time (earlier events first)
      if (dateA && dateB) {
        if (dateA.getTime() !== dateB.getTime()) {
          return dateA.getTime() - dateB.getTime()
        }
      } else if (dateA && !dateB) {
        // A has a date, B does not -> A first
        return -1
      } else if (!dateA && dateB) {
        // B has a date, A does not -> B first
        return 1
      }

      // Fallback: alphabetical by key
      return a.localeCompare(b)
    })

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

        <div className="space-y-4">
          {eventKeys.map((eventKey) => {
            const matches = yearEvents[eventKey] || []
            const isExpanded = expandedEvents[eventKey]
            const displayName = formatEventName(eventKey)
            
            return (
              <motion.div
                key={eventKey}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="overflow-hidden rounded-2xl border border-white/10 bg-white/5 shadow-[0_12px_35px_rgba(0,0,0,0.35)]"
              >
                <button
                  onClick={() => toggleEvent(eventKey)}
                  className="flex w-full items-center justify-between gap-4 border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent px-6 py-4 transition-all hover:from-white/10 group"
                >
                  <div className="flex items-center space-x-4">
                    <ChevronRight 
                      className={`h-5 w-5 transition-transform text-white/60 group-hover:text-white ${isExpanded ? 'rotate-90' : ''}`}
                    />
                    <Calendar className="h-5 w-5 text-white/60 group-hover:text-emerald-200 transition-colors" />
                    <div className="text-left">
                      <h2 className="text-lg font-semibold group-hover:text-emerald-100 transition-colors">{displayName}</h2>
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
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="bg-transparent px-6 pb-6"
                  >
                    <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-black/20">
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
                            const winner = match.team1_score > match.team2_score ? 1 : 
                                          match.team2_score > match.team1_score ? 2 : null
                            
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
                                  <span className={`text-sm font-medium ${winner === 1 ? 'text-emerald-200 font-semibold' : 'text-white'}`}>
                                    {match.team1_name}
                                  </span>
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
                                  <span className={`text-sm font-medium ${winner === 2 ? 'text-emerald-200 font-semibold' : 'text-white'}`}>
                                    {match.team2_name}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className="rounded-full border border-white/15 bg-white/5 px-2 py-1 text-xs text-white/60">
                                    {match.stage || '-'}
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-xs text-white/60">
                                  {(() => {
                                    const dateStr = match.match_date || match.match_ts_utc;
                                    if (!dateStr) return '-';
                                    try {
                                      const date = new Date(dateStr);
                                      if (!isNaN(date.getTime())) {
                                        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                                      }
                                    } catch (e) {}
                                    return dateStr.substring(0, 10) || '-';
                                  })()}
                                </td>
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
                  </motion.div>
                )}
              </motion.div>
            )
          })}
        </div>

        {eventKeys.length === 0 && (
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
          const yearData = groupedByYear[year] || {}
          const eventCount = Object.keys(yearData).length
          const totalMatches = Object.values(yearData).reduce((sum, matches) => sum + matches.length, 0)
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
