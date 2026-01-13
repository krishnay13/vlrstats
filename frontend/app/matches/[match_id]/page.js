'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowLeft, Trophy, MapPin, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

// Helper function to clean map names
function cleanMapName(mapName) {
  if (!mapName) return mapName
  return mapName.replace(/^\d+/, '')
}

// Helper function to group stats by team
function groupStatsByTeam(stats, team1Name, team2Name) {
  const team1Stats = stats.filter(stat => stat.team_name === team1Name)
  const team2Stats = stats.filter(stat => stat.team_name === team2Name)
  const unknownStats = stats.filter(stat => !stat.team_name || (stat.team_name !== team1Name && stat.team_name !== team2Name))
  return { team1Stats, team2Stats, unknownStats }
}

export default function MatchDetailsPage() {
  const params = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedMapId, setSelectedMapId] = useState(null)

  useEffect(() => {
    async function fetchMatchDetails() {
      try {
        const res = await fetch(`/api/matches/${params.match_id}`, { cache: 'no-store' })
        if (!res.ok) {
          if (res.status === 404) {
            setError('Match not found')
            return
          }
          throw new Error('Failed to fetch match details')
        }
        const matchData = await res.json()
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

  if (error || !data) {
    return (
      <div className="container py-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Error</CardTitle>
            <CardDescription className="text-sm">{error || 'Match not found'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild size="sm">
              <Link href="/matches">
                <ArrowLeft className="mr-2 h-3 w-3" />
                Back to Matches
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { match, maps, playerStats } = data
  const winner = match.team1_score > match.team2_score ? 1 : match.team2_score > match.team1_score ? 2 : null
  const selectedMap = maps.find(m => (m.map_id || m.id) === selectedMapId) || (maps.length > 0 ? maps[0] : null)

  return (
    <div className="container py-4 max-w-7xl">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <Button asChild variant="ghost" size="sm" className="mb-3">
          <Link href="/matches">
            <ArrowLeft className="mr-2 h-3 w-3" />
            Back to Matches
          </Link>
        </Button>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-1">
              {match.team1_name} vs {match.team2_name}
            </h1>
            <p className="text-sm text-muted-foreground">Match #{match.match_id}</p>
          </div>
          {winner && (
            <Badge variant={winner === 1 ? "default" : "secondary"} className="text-sm px-3 py-1">
              <Trophy className="h-3 w-3 mr-1" />
              {winner === 1 ? match.team1_name : match.team2_name} Wins
            </Badge>
          )}
        </div>
      </motion.div>

      {/* Score Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-4"
      >
        <Card className="border">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Final Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2 }}
                className={`text-center p-4 rounded-lg ${winner === 1 ? 'bg-primary/10 border border-primary' : 'bg-muted/50'}`}
              >
                <div className={`text-3xl font-bold mb-1 ${winner === 1 ? 'text-primary' : ''}`}>
                  {match.team1_score}
                </div>
                <div className="text-sm font-semibold">{match.team1_name}</div>
              </motion.div>
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3 }}
                className={`text-center p-4 rounded-lg ${winner === 2 ? 'bg-primary/10 border border-primary' : 'bg-muted/50'}`}
              >
                <div className={`text-3xl font-bold mb-1 ${winner === 2 ? 'text-primary' : ''}`}>
                  {match.team2_score}
                </div>
                <div className="text-sm font-semibold">{match.team2_name}</div>
              </motion.div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <Tabs defaultValue="maps" className="space-y-3">
        <TabsList className="h-9">
          <TabsTrigger value="maps" className="text-sm">
            <MapPin className="mr-1.5 h-3.5 w-3.5" />
            Maps ({maps.length})
          </TabsTrigger>
          <TabsTrigger value="totals" className="text-sm">
            <TrendingUp className="mr-1.5 h-3.5 w-3.5" />
            Match Totals
          </TabsTrigger>
        </TabsList>

        <TabsContent value="maps" className="space-y-3">
          {maps.length > 0 && (
            <>
              <div className="flex items-center space-x-3 mb-3">
                <label className="text-sm font-medium">Select Map:</label>
                <Select 
                  value={selectedMapId?.toString() || ''} 
                  onValueChange={(value) => setSelectedMapId(parseInt(value))}
                >
                  <SelectTrigger className="w-[250px]">
                    <SelectValue placeholder="Select a map" />
                  </SelectTrigger>
                  <SelectContent>
                    {maps.map((map) => {
                      const cleanName = cleanMapName(map.map_name || map.map)
                      const mapId = map.map_id || map.id
                      if (!mapId) {
                        console.warn('Map missing id:', map)
                        return null
                      }
                      return (
                        <SelectItem key={mapId} value={mapId.toString()}>
                          {cleanName} ({map.team1_score || map.team_a_score || 0}-{map.team2_score || map.team_b_score || 0})
                        </SelectItem>
                      )
                    }).filter(Boolean)}
                  </SelectContent>
                </Select>
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
              >
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-lg">{cleanName}</CardTitle>
                        <CardDescription className="text-xs">
                          {map.team1_name || match.team1_name} {team1Score} - {team2Score} {map.team2_name || match.team2_name}
                        </CardDescription>
                      </div>
                      {mapWinner && (
                        <Badge variant={mapWinner === 1 ? "default" : "secondary"} className="text-xs">
                          {mapWinner === 1 ? (map.team1_name || match.team1_name) : (map.team2_name || match.team2_name)} Wins
                        </Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Team 1 Stats */}
                    {team1Stats.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2 text-primary">{map.team1_name || match.team1_name}</h4>
                        <div className="border rounded-md overflow-hidden">
                          <Table>
                            <TableHeader>
                              <TableRow className="h-9">
                                <TableHead className="h-9 px-3 text-xs">Player</TableHead>
                                <TableHead className="h-9 px-3 text-xs">K</TableHead>
                                <TableHead className="h-9 px-3 text-xs">D</TableHead>
                                <TableHead className="h-9 px-3 text-xs">A</TableHead>
                                <TableHead className="h-9 px-3 text-xs">ACS</TableHead>
                                <TableHead className="h-9 px-3 text-xs">Rating</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {team1Stats.map((stat, statIndex) => (
                                <motion.tr
                                  key={stat.stat_id}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: statIndex * 0.02 }}
                                  className="hover:bg-muted/50 h-9"
                                >
                                  <TableCell className="px-3 py-2 text-sm font-medium">{stat.player_name}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.kills}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.deaths}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.assists}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.acs}</TableCell>
                                  <TableCell className="px-3 py-2">
                                    <Badge variant={stat.rating >= 1.0 ? "default" : "secondary"} className="text-xs px-1.5 py-0">
                                      {stat.rating?.toFixed(2) || 'N/A'}
                                    </Badge>
                                  </TableCell>
                                </motion.tr>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}

                    {/* Team 2 Stats */}
                    {team2Stats.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2 text-secondary-foreground">{map.team2_name || match.team2_name}</h4>
                        <div className="border rounded-md overflow-hidden">
                          <Table>
                            <TableHeader>
                              <TableRow className="h-9">
                                <TableHead className="h-9 px-3 text-xs">Player</TableHead>
                                <TableHead className="h-9 px-3 text-xs">K</TableHead>
                                <TableHead className="h-9 px-3 text-xs">D</TableHead>
                                <TableHead className="h-9 px-3 text-xs">A</TableHead>
                                <TableHead className="h-9 px-3 text-xs">ACS</TableHead>
                                <TableHead className="h-9 px-3 text-xs">Rating</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {team2Stats.map((stat, statIndex) => (
                                <motion.tr
                                  key={stat.stat_id}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: statIndex * 0.02 }}
                                  className="hover:bg-muted/50 h-9"
                                >
                                  <TableCell className="px-3 py-2 text-sm font-medium">{stat.player_name}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.kills}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.deaths}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.assists}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.acs}</TableCell>
                                  <TableCell className="px-3 py-2">
                                    <Badge variant={stat.rating >= 1.0 ? "default" : "secondary"} className="text-xs px-1.5 py-0">
                                      {stat.rating?.toFixed(2) || 'N/A'}
                                    </Badge>
                                  </TableCell>
                                </motion.tr>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}

                    {/* Unknown/Unmatched Stats */}
                    {unknownStats.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2 text-muted-foreground">Other</h4>
                        <div className="border rounded-md overflow-hidden">
                          <Table>
                            <TableHeader>
                              <TableRow className="h-9">
                                <TableHead className="h-9 px-3 text-xs">Player</TableHead>
                                <TableHead className="h-9 px-3 text-xs">K</TableHead>
                                <TableHead className="h-9 px-3 text-xs">D</TableHead>
                                <TableHead className="h-9 px-3 text-xs">A</TableHead>
                                <TableHead className="h-9 px-3 text-xs">ACS</TableHead>
                                <TableHead className="h-9 px-3 text-xs">Rating</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {unknownStats.map((stat, statIndex) => (
                                <motion.tr
                                  key={stat.stat_id}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: statIndex * 0.02 }}
                                  className="hover:bg-muted/50 h-9"
                                >
                                  <TableCell className="px-3 py-2 text-sm font-medium">{stat.player_name}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.kills}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.deaths}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.assists}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.acs}</TableCell>
                                  <TableCell className="px-3 py-2">
                                    <Badge variant={stat.rating >= 1.0 ? "default" : "secondary"} className="text-xs px-1.5 py-0">
                                      {stat.rating?.toFixed(2) || 'N/A'}
                                    </Badge>
                                  </TableCell>
                                </motion.tr>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            )
          })()}
            </>
          )}
          
          {maps.length === 0 && (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                No maps available for this match.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="totals">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Match Totals</CardTitle>
              <CardDescription className="text-xs">Overall player statistics for the entire match</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {(() => {
                const { team1Stats, team2Stats, unknownStats } = groupStatsByTeam(
                  playerStats,
                  match.team1_name,
                  match.team2_name
                )

                return (
                  <>
                    {/* Team 1 Stats */}
                    {team1Stats.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2 text-primary">{match.team1_name}</h4>
                        <div className="border rounded-md overflow-hidden">
                          <Table>
                            <TableHeader>
                              <TableRow className="h-9">
                                <TableHead className="h-9 px-3 text-xs">Player</TableHead>
                                <TableHead className="h-9 px-3 text-xs">K</TableHead>
                                <TableHead className="h-9 px-3 text-xs">D</TableHead>
                                <TableHead className="h-9 px-3 text-xs">A</TableHead>
                                <TableHead className="h-9 px-3 text-xs">ACS</TableHead>
                                <TableHead className="h-9 px-3 text-xs">Rating</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {team1Stats.map((stat, index) => (
                                <motion.tr
                                  key={stat.stat_id}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: index * 0.02 }}
                                  className="hover:bg-muted/50 h-9"
                                >
                                  <TableCell className="px-3 py-2 text-sm font-medium">{stat.player_name}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.kills}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.deaths}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.assists}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.acs}</TableCell>
                                  <TableCell className="px-3 py-2">
                                    <Badge variant={stat.rating >= 1.0 ? "default" : "secondary"} className="text-xs px-1.5 py-0">
                                      {stat.rating?.toFixed(2) || 'N/A'}
                                    </Badge>
                                  </TableCell>
                                </motion.tr>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}

                    {/* Team 2 Stats */}
                    {team2Stats.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2 text-secondary-foreground">{match.team2_name}</h4>
                        <div className="border rounded-md overflow-hidden">
                          <Table>
                            <TableHeader>
                              <TableRow className="h-9">
                                <TableHead className="h-9 px-3 text-xs">Player</TableHead>
                                <TableHead className="h-9 px-3 text-xs">K</TableHead>
                                <TableHead className="h-9 px-3 text-xs">D</TableHead>
                                <TableHead className="h-9 px-3 text-xs">A</TableHead>
                                <TableHead className="h-9 px-3 text-xs">ACS</TableHead>
                                <TableHead className="h-9 px-3 text-xs">Rating</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {team2Stats.map((stat, index) => (
                                <motion.tr
                                  key={stat.stat_id}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: index * 0.02 }}
                                  className="hover:bg-muted/50 h-9"
                                >
                                  <TableCell className="px-3 py-2 text-sm font-medium">{stat.player_name}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.kills}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.deaths}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.assists}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.acs}</TableCell>
                                  <TableCell className="px-3 py-2">
                                    <Badge variant={stat.rating >= 1.0 ? "default" : "secondary"} className="text-xs px-1.5 py-0">
                                      {stat.rating?.toFixed(2) || 'N/A'}
                                    </Badge>
                                  </TableCell>
                                </motion.tr>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}

                    {/* Unknown Stats */}
                    {unknownStats.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold mb-2 text-muted-foreground">Other</h4>
                        <div className="border rounded-md overflow-hidden">
                          <Table>
                            <TableHeader>
                              <TableRow className="h-9">
                                <TableHead className="h-9 px-3 text-xs">Player</TableHead>
                                <TableHead className="h-9 px-3 text-xs">K</TableHead>
                                <TableHead className="h-9 px-3 text-xs">D</TableHead>
                                <TableHead className="h-9 px-3 text-xs">A</TableHead>
                                <TableHead className="h-9 px-3 text-xs">ACS</TableHead>
                                <TableHead className="h-9 px-3 text-xs">Rating</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {unknownStats.map((stat, index) => (
                                <motion.tr
                                  key={stat.stat_id}
                                  initial={{ opacity: 0, x: -10 }}
                                  animate={{ opacity: 1, x: 0 }}
                                  transition={{ delay: index * 0.02 }}
                                  className="hover:bg-muted/50 h-9"
                                >
                                  <TableCell className="px-3 py-2 text-sm font-medium">{stat.player_name}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.kills}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.deaths}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.assists}</TableCell>
                                  <TableCell className="px-3 py-2 text-sm">{stat.acs}</TableCell>
                                  <TableCell className="px-3 py-2">
                                    <Badge variant={stat.rating >= 1.0 ? "default" : "secondary"} className="text-xs px-1.5 py-0">
                                      {stat.rating?.toFixed(2) || 'N/A'}
                                    </Badge>
                                  </TableCell>
                                </motion.tr>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}
                  </>
                )
              })()}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
