'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { Calendar, ArrowRight, Trophy } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

export default function MatchesPage() {
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchMatches() {
      try {
        const res = await fetch('/api/matches', { cache: 'no-store' })
        if (!res.ok) throw new Error('Failed to fetch matches')
        const data = await res.json()
        setMatches(data)
      } catch (error) {
        console.error(error)
      } finally {
        setLoading(false)
      }
    }
    fetchMatches()
  }, [])

  if (loading) {
    return (
      <div className="container py-12">
        <div className="flex items-center justify-center min-h-[400px]">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="container py-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-4xl font-bold tracking-tight mb-2">Matches</h1>
        <p className="text-muted-foreground">
          Browse all Valorant esports matches and their detailed statistics
        </p>
      </motion.div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {matches.map((match, index) => {
          const winner = match.team1_score > match.team2_score ? 1 : match.team2_score > match.team1_score ? 2 : null
          
          return (
            <motion.div
              key={match.match_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              whileHover={{ y: -5 }}
            >
              <Card className="group h-full border-2 transition-all hover:border-primary/50 hover:shadow-lg">
                <CardHeader>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-2">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">
                        Match #{match.match_id}
                      </span>
                    </div>
                    {winner && (
                      <Badge variant={winner === 1 ? "default" : "secondary"}>
                        <Trophy className="h-3 w-3 mr-1" />
                        Winner
                      </Badge>
                    )}
                  </div>
                  <CardTitle className="text-xl">
                    {match.team1_name} vs {match.team2_name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                      <div className="text-center flex-1">
                        <div className={`text-3xl font-bold ${winner === 1 ? 'text-primary' : ''}`}>
                          {match.team1_score}
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          {match.team1_name}
                        </div>
                      </div>
                      <div className="text-2xl font-bold text-muted-foreground mx-4">-</div>
                      <div className="text-center flex-1">
                        <div className={`text-3xl font-bold ${winner === 2 ? 'text-primary' : ''}`}>
                          {match.team2_score}
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          {match.team2_name}
                        </div>
                      </div>
                    </div>
                    <Button asChild className="w-full group/btn">
                      <Link href={`/matches/${match.match_id}`}>
                        View Details
                        <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {matches.length === 0 && (
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
