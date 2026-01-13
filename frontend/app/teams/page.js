'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { Users, ArrowRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

const REGION_ORDER = ['AMERICAS', 'EMEA', 'APAC', 'CHINA', 'UNKNOWN']
const REGION_LABELS = {
  'AMERICAS': 'Americas',
  'EMEA': 'EMEA',
  'APAC': 'APAC',
  'CHINA': 'China',
  'UNKNOWN': 'Unknown',
}

export default function TeamsPage() {
  const [teams, setTeams] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchTeams() {
      try {
        const res = await fetch('/api/teams', { cache: 'no-store' })
        if (!res.ok) throw new Error('Failed to fetch teams')
        const data = await res.json()
        setTeams(data)
      } catch (error) {
        console.error(error)
      } finally {
        setLoading(false)
      }
    }
    fetchTeams()
  }, [])

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

  // Group teams by region
  const teamsByRegion = teams.reduce((acc, team) => {
    const region = team.region || 'UNKNOWN'
    if (!acc[region]) {
      acc[region] = []
    }
    acc[region].push(team)
    return acc
  }, {})

  return (
    <div className="container py-4 max-w-7xl">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <h1 className="text-2xl font-bold tracking-tight mb-1">Teams</h1>
        <p className="text-sm text-muted-foreground">
          Explore all Valorant esports teams organized by region
        </p>
      </motion.div>

      <div className="space-y-6">
        {REGION_ORDER.map((region) => {
          const regionTeams = teamsByRegion[region] || []
          if (regionTeams.length === 0) return null

          return (
            <motion.div
              key={region}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="border rounded-lg overflow-hidden"
            >
              <div className="bg-muted/50 px-4 py-2 border-b">
                <h2 className="text-lg font-semibold">{REGION_LABELS[region] || region}</h2>
              </div>
              
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="h-10">
                      <TableHead className="h-10 px-4 text-xs font-semibold">Team</TableHead>
                      <TableHead className="h-10 px-4 text-xs font-semibold w-24"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {regionTeams.map((team, index) => (
                      <motion.tr
                        key={team.team_name}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.01 }}
                        className="hover:bg-muted/50 h-12 border-b"
                      >
                        <TableCell className="px-4 py-3">
                          <div className="flex items-center space-x-3">
                            <Avatar className="h-9 w-9">
                              <AvatarFallback className="bg-primary/10 text-primary font-semibold text-sm">
                                {team.team_name?.charAt(0) || 'T'}
                              </AvatarFallback>
                            </Avatar>
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-sm">{team.team_name}</span>
                              {team.is_inactive && (
                                <Badge variant="destructive" className="text-xs px-1.5 py-0">
                                  Inactive
                                </Badge>
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="px-4 py-3">
                          <Link
                            href={`/teams/${encodeURIComponent(team.team_name)}`}
                            className="text-xs text-primary hover:underline font-medium flex items-center space-x-1"
                          >
                            <span>View Roster</span>
                            <ArrowRight className="h-3 w-3" />
                          </Link>
                        </TableCell>
                      </motion.tr>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </motion.div>
          )
        })}
      </div>

      {teams.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12"
        >
          <p className="text-muted-foreground">No teams found.</p>
        </motion.div>
      )}
    </div>
  )
}
