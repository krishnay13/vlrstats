'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ChevronRight, Calendar } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function MatchesPage() {
  const [data, setData] = useState({ matches: [], grouped: {} })
  const [loading, setLoading] = useState(true)
  const [expandedTournaments, setExpandedTournaments] = useState({})

  useEffect(() => {
    async function fetchMatches() {
      try {
        const res = await fetch('/api/matches', { cache: 'no-store' })
        if (!res.ok) throw new Error('Failed to fetch matches')
        const data = await res.json()
        setData(data)
        // Expand first tournament by default
        const tournaments = Object.keys(data.grouped || {})
        if (tournaments.length > 0) {
          setExpandedTournaments({
            [tournaments[0]]: true,
          })
        }
      } catch (error) {
        console.error(error)
      } finally {
        setLoading(false)
      }
    }
    fetchMatches()
  }, [])

  const toggleTournament = (tournament) => {
    setExpandedTournaments(prev => ({
      ...prev,
      [tournament]: !prev[tournament]
    }))
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

  const tournaments = Object.keys(data.grouped || {})

  return (
    <div className="container py-4 max-w-7xl">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <h1 className="text-2xl font-bold tracking-tight mb-1">Matches</h1>
        <p className="text-sm text-muted-foreground">
          Browse all Valorant esports matches organized by event
        </p>
      </motion.div>

      <div className="space-y-3">
        {tournaments.map((tournament) => {
          const matches = data.grouped[tournament] || []
          const isExpanded = expandedTournaments[tournament]
          const firstMatch = matches[0]
          const displayName = firstMatch?.groupKey || tournament
          
          return (
            <motion.div
              key={tournament}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="border rounded-lg overflow-hidden"
            >
              <button
                onClick={() => toggleTournament(tournament)}
                className="w-full bg-muted/50 px-4 py-3 border-b hover:bg-muted transition-colors flex items-center justify-between"
              >
                <div className="flex items-center space-x-3">
                  <ChevronRight 
                    className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                  />
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <h2 className="text-lg font-semibold">{displayName}</h2>
                  <Badge variant="secondary" className="text-xs">
                    {matches.length} match{matches.length !== 1 ? 'es' : ''}
                  </Badge>
                </div>
              </button>
              
              {isExpanded && (
                <div className="px-4 pb-4 bg-background">
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="h-9">
                          <TableHead className="h-9 px-3 text-xs w-20">ID</TableHead>
                          <TableHead className="h-9 px-3 text-xs">Team 1</TableHead>
                          <TableHead className="h-9 px-3 text-xs w-24 text-center">Score</TableHead>
                          <TableHead className="h-9 px-3 text-xs">Team 2</TableHead>
                          <TableHead className="h-9 px-3 text-xs w-28">Stage</TableHead>
                          <TableHead className="h-9 px-3 text-xs w-24">Date</TableHead>
                          <TableHead className="h-9 px-3 text-xs w-20"></TableHead>
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
                              transition={{ delay: index * 0.01 }}
                              className="hover:bg-muted/50 h-9"
                            >
                              <TableCell className="px-3 py-2 text-xs text-muted-foreground font-mono">
                                {match.match_id}
                              </TableCell>
                              <TableCell className="px-3 py-2">
                                <span className="text-sm font-medium">
                                  {match.team1_name}
                                </span>
                              </TableCell>
                              <TableCell className="px-3 py-2 text-center">
                                <div className="flex items-center justify-center space-x-1.5">
                                  <span className={`text-sm font-semibold ${winner === 1 ? 'text-primary' : ''}`}>
                                    {match.team1_score}
                                  </span>
                                  <span className="text-xs text-muted-foreground">-</span>
                                  <span className={`text-sm font-semibold ${winner === 2 ? 'text-primary' : ''}`}>
                                    {match.team2_score}
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell className="px-3 py-2">
                                <span className="text-sm font-medium">
                                  {match.team2_name}
                                </span>
                              </TableCell>
                              <TableCell className="px-3 py-2 text-xs text-muted-foreground">
                                {match.stage || '-'}
                              </TableCell>
                              <TableCell className="px-3 py-2 text-xs text-muted-foreground">
                                {(() => {
                                  const dateStr = match.match_date || match.match_ts_utc;
                                  if (!dateStr) return '-';
                                  try {
                                    const date = new Date(dateStr);
                                    if (!isNaN(date.getTime())) {
                                      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                                    }
                                  } catch (e) {}
                                  return dateStr.substring(0, 10) || '-';
                                })()}
                              </TableCell>
                              <TableCell className="px-3 py-2">
                                <Link
                                  href={`/matches/${match.match_id}`}
                                  className="text-xs text-primary hover:underline font-medium"
                                >
                                  View →
                                </Link>
                              </TableCell>
                            </motion.tr>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </motion.div>
          )
        })}
      </div>

      {tournaments.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12"
        >
          <p className="text-muted-foreground">No matches found.</p>
        </motion.div>
      )}
    </div>
  )
}
