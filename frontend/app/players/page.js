'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Users } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function PlayersPage() {
  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchPlayers() {
      try {
        const res = await fetch('/api/players', { cache: 'no-store' })
        if (!res.ok) throw new Error('Failed to fetch players')
        const data = await res.json()
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
            className="h-6 w-6 border-3 border-primary border-t-transparent rounded-full"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="container py-4 max-w-7xl">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <h1 className="text-2xl font-bold tracking-tight mb-1">Players</h1>
        <p className="text-sm text-muted-foreground">
          Browse all Valorant esports players and their teams
        </p>
      </motion.div>

      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="h-10">
              <TableHead className="h-10 px-4 text-xs font-semibold">Player</TableHead>
              <TableHead className="h-10 px-4 text-xs font-semibold">Team</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {players.map((player, index) => (
              <motion.tr
                key={player.player_name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.01 }}
                className="hover:bg-muted/50 h-12 border-b"
              >
                <TableCell className="px-4 py-3">
                  <div className="flex items-center space-x-3">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback className="bg-primary/10 text-primary font-semibold text-sm">
                        {player.player_name?.charAt(0) || 'P'}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-sm">{player.player_name}</span>
                      {player.is_inactive && (
                        <Badge variant="destructive" className="text-xs px-1.5 py-0">
                          Inactive
                        </Badge>
                      )}
                    </div>
                  </div>
                </TableCell>
                <TableCell className="px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <Users className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">{player.team_name || 'Free Agent'}</span>
                  </div>
                </TableCell>
              </motion.tr>
            ))}
          </TableBody>
        </Table>
      </div>

      {players.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12"
        >
          <p className="text-muted-foreground">No players found.</p>
        </motion.div>
      )}
    </div>
  )
}
