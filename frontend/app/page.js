'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { Trophy, TrendingUp, Users, Calendar, ArrowRight, BarChart3 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const statsConfig = [
  { label: 'Total Matches', key: 'matches', icon: Calendar, color: 'text-blue-500' },
  { label: 'Active Teams', key: 'teams', icon: Users, color: 'text-green-500' },
  { label: 'Players', key: 'players', icon: Users, color: 'text-purple-500' },
  { label: 'Tournaments', key: 'tournaments', icon: Trophy, color: 'text-yellow-500' },
]

const features = [
  {
    title: 'Match Analytics',
    description: 'Detailed statistics and insights for every match',
    icon: BarChart3,
    href: '/matches',
    color: 'from-blue-500 to-cyan-500',
  },
  {
    title: 'Team Performance',
    description: 'Comprehensive team statistics and rankings',
    icon: Users,
    href: '/teams',
    color: 'from-green-500 to-emerald-500',
  },
  {
    title: 'Player Stats',
    description: 'Individual player performance metrics',
    icon: TrendingUp,
    href: '/players',
    color: 'from-purple-500 to-pink-500',
  },
]

export default function HomePage() {
  const [stats, setStats] = useState({ matches: 0, teams: 0, players: 0, tournaments: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch('/api/stats', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          setStats(data)
        }
      } catch (error) {
        console.error('Failed to fetch stats:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b bg-gradient-to-b from-background to-muted/20">
        <div className="container relative z-10 py-24 md:py-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mx-auto max-w-3xl text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
              className="mb-6 inline-flex items-center justify-center"
            >
              <Trophy className="h-16 w-16 text-primary" />
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mb-6 text-4xl font-bold tracking-tight sm:text-6xl md:text-7xl"
            >
              <span className="bg-gradient-to-r from-primary via-primary/80 to-primary/60 bg-clip-text text-transparent">
                VLR Stats
              </span>
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="mb-8 text-lg text-muted-foreground sm:text-xl"
            >
              Comprehensive statistics and analytics for Valorant esports matches, teams, and players.
              Dive deep into the data that drives competitive Valorant.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="flex flex-col items-center justify-center gap-4 sm:flex-row"
            >
              <Button asChild size="lg" className="group">
                <Link href="/matches">
                  Explore Matches
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href="/teams">View Teams</Link>
              </Button>
            </motion.div>
          </motion.div>
        </div>
        
        {/* Animated background elements */}
        <div className="absolute inset-0 -z-0">
          <div className="absolute left-1/4 top-1/4 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
          <div className="absolute right-1/4 bottom-1/4 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
        </div>
      </section>

      {/* Stats Section */}
      <section className="container py-16">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="grid gap-6 md:grid-cols-2 lg:grid-cols-4"
        >
          {statsConfig.map((statConfig, index) => {
            const Icon = statConfig.icon
            const value = loading ? '...' : stats[statConfig.key]?.toLocaleString() || '0'
            return (
              <motion.div
                key={statConfig.label}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="border-2 transition-all hover:border-primary/50 hover:shadow-lg">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">{statConfig.label}</CardTitle>
                    <Icon className={`h-4 w-4 ${statConfig.color}`} />
                  </CardHeader>
                  <CardContent>
                    <motion.div
                      key={value}
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="text-2xl font-bold"
                    >
                      {value}
                    </motion.div>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="container py-16">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-12 text-center"
        >
          <h2 className="mb-4 text-3xl font-bold tracking-tight">Explore Our Features</h2>
          <p className="text-muted-foreground">
            Everything you need to analyze Valorant esports data
          </p>
        </motion.div>

        <div className="grid gap-8 md:grid-cols-3">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -5 }}
              >
                <Card className="group relative h-full overflow-hidden border-2 transition-all hover:border-primary/50 hover:shadow-xl">
                  <div className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0 transition-opacity group-hover:opacity-5`} />
                  <CardHeader>
                    <div className={`mb-4 inline-flex rounded-lg bg-gradient-to-br ${feature.color} p-3`}>
                      <Icon className="h-6 w-6 text-white" />
                    </div>
                    <CardTitle>{feature.title}</CardTitle>
                    <CardDescription>{feature.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button asChild variant="ghost" className="group/btn">
                      <Link href={feature.href}>
                        Learn More
                        <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
                      </Link>
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
