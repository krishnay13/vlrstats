'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ChevronRight, Calendar, Trophy } from 'lucide-react'
import { getTournamentSortPriority } from '@/app/lib/region-utils'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function MatchesPage() {
  const [data, setData] = useState({ matches: [], grouped: {}, groupedByYear: {} })
  const [loading, setLoading] = useState(true)
  const [selectedYear, setSelectedYear] = useState(null)
  const [expandedEvents, setExpandedEvents] = useState({})

  useEffect(() => {
    async function fetchMatches() {
      try {
        const res = await fetch('/api/matches', { cache: 'no-store' })
        if (!res.ok) throw new Error('Failed to fetch matches')
        const data = await res.json()
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
            className="h-6 w-6 border-3 border-primary border-t-transparent rounded-full"
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
      <div className="container py-4 max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <button
            onClick={() => setSelectedYear(null)}
            className="mb-4 text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          >
            <ChevronRight className="h-4 w-4 rotate-180" />
            Back to Years
          </button>
          <h1 className="text-3xl font-bold tracking-tight mb-2">VCT {selectedYear}</h1>
          <p className="text-sm text-muted-foreground">
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
                className="border rounded-xl overflow-hidden bg-card shadow-sm hover:shadow-md transition-shadow"
              >
                <button
                  onClick={() => toggleEvent(eventKey)}
                  className="w-full bg-gradient-to-r from-muted/50 to-muted/30 px-6 py-4 border-b hover:from-muted/70 hover:to-muted/50 transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-4">
                    <ChevronRight 
                      className={`h-5 w-5 transition-transform text-muted-foreground group-hover:text-foreground ${isExpanded ? 'rotate-90' : ''}`}
                    />
                    <Calendar className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                    <div className="text-left">
                      <h2 className="text-lg font-semibold group-hover:text-primary transition-colors">{displayName}</h2>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {matches.length} match{matches.length !== 1 ? 'es' : ''}
                      </p>
                    </div>
                  </div>
                  <Badge variant="secondary" className="text-xs px-3 py-1">
                    {matches.length}
                  </Badge>
                </button>
                
                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="px-6 pb-6 bg-background"
                  >
                    <div className="mt-4 border rounded-lg overflow-hidden bg-background">
                      <Table>
                        <TableHeader>
                          <TableRow className="h-11 bg-muted/30">
                            <TableHead className="h-11 px-4 text-xs font-semibold w-24">ID</TableHead>
                            <TableHead className="h-11 px-4 text-xs font-semibold">Team 1</TableHead>
                            <TableHead className="h-11 px-4 text-xs font-semibold w-28 text-center">Score</TableHead>
                            <TableHead className="h-11 px-4 text-xs font-semibold">Team 2</TableHead>
                            <TableHead className="h-11 px-4 text-xs font-semibold w-32">Stage</TableHead>
                            <TableHead className="h-11 px-4 text-xs font-semibold w-28">Date</TableHead>
                            <TableHead className="h-11 px-4 text-xs font-semibold w-24"></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {matches.map((match, index) => {
                            const winner = match.team1_score > match.team2_score ? 1 : 
                                          match.team2_score > match.team1_score ? 2 : null
                            
                            return (
                              <motion.tr
                                key={match.match_id}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: index * 0.02 }}
                                className="hover:bg-muted/30 h-12 border-b border-border/50 transition-colors"
                              >
                                <TableCell className="px-4 py-3 text-xs text-muted-foreground font-mono">
                                  {match.match_id}
                                </TableCell>
                                <TableCell className="px-4 py-3">
                                  <span className={`text-sm font-medium ${winner === 1 ? 'text-primary font-semibold' : ''}`}>
                                    {match.team1_name}
                                  </span>
                                </TableCell>
                                <TableCell className="px-4 py-3 text-center">
                                  <div className="flex items-center justify-center space-x-2">
                                    <span className={`text-sm font-bold ${winner === 1 ? 'text-primary' : 'text-foreground'}`}>
                                      {match.team1_score}
                                    </span>
                                    <span className="text-xs text-muted-foreground">-</span>
                                    <span className={`text-sm font-bold ${winner === 2 ? 'text-primary' : 'text-foreground'}`}>
                                      {match.team2_score}
                                    </span>
                                  </div>
                                </TableCell>
                                <TableCell className="px-4 py-3">
                                  <span className={`text-sm font-medium ${winner === 2 ? 'text-primary font-semibold' : ''}`}>
                                    {match.team2_name}
                                  </span>
                                </TableCell>
                                <TableCell className="px-4 py-3">
                                  <Badge variant="outline" className="text-xs">
                                    {match.stage || '-'}
                                  </Badge>
                                </TableCell>
                                <TableCell className="px-4 py-3 text-xs text-muted-foreground">
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
                                </TableCell>
                                <TableCell className="px-4 py-3">
                                  <Link
                                    href={`/matches/${match.match_id}`}
                                    className="text-xs text-primary hover:text-primary/80 hover:underline font-medium transition-colors inline-flex items-center gap-1"
                                  >
                                    View
                                    <ChevronRight className="h-3 w-3" />
                                  </Link>
                                </TableCell>
                              </motion.tr>
                            )
                          })}
                        </TableBody>
                      </Table>
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
            className="text-center py-12"
          >
            <p className="text-muted-foreground">No events found for {selectedYear}.</p>
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
        <h1 className="text-3xl font-bold tracking-tight mb-2">Matches</h1>
        <p className="text-sm text-muted-foreground">
          Select a year to browse Valorant esports matches
        </p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {years.map((year, index) => {
          const yearData = groupedByYear[year] || {}
          const eventCount = Object.keys(yearData).length
          const totalMatches = Object.values(yearData).reduce((sum, matches) => sum + matches.length, 0)
          const isEmpty = eventCount === 0

          return (
            <motion.div
              key={year}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card 
                className={`cursor-pointer h-full transition-all hover:shadow-lg ${
                  isEmpty 
                    ? 'opacity-50 cursor-not-allowed' 
                    : 'hover:border-primary/50 hover:scale-[1.02]'
                }`}
                onClick={() => !isEmpty && setSelectedYear(year)}
              >
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="p-3 rounded-lg bg-primary/10">
                      <Trophy className="h-6 w-6 text-primary" />
                    </div>
                    {isEmpty && (
                      <Badge variant="outline" className="text-xs">Empty</Badge>
                    )}
                  </div>
                  <CardTitle className="text-2xl">VCT {year}</CardTitle>
                  <CardDescription className="text-sm mt-2">
                    {isEmpty ? 'No matches available' : `${eventCount} event${eventCount !== 1 ? 's' : ''} • ${totalMatches} matches`}
                  </CardDescription>
                </CardHeader>
                {!isEmpty && (
                  <CardContent>
                    <div className="flex items-center text-sm text-primary font-medium">
                      View Events
                      <ChevronRight className="h-4 w-4 ml-2" />
                    </div>
                  </CardContent>
                )}
              </Card>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
