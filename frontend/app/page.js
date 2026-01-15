'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { Trophy, TrendingUp, Users, Calendar, ArrowRight, BarChart3, Sparkles } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

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
  const [elo, setElo] = useState({ teams: [], players: [] })
  const [eloLoading, setEloLoading] = useState(true)

  useEffect(() => {
    async function fetchStats() {
      try {
        const data = await fetchJson('/api/stats')
        setStats(data)
      } catch (error) {
        console.error('Failed to fetch stats:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  useEffect(() => {
    async function fetchElo() {
      try {
        const data = await fetchJson('/api/elo?topTeams=6&topPlayers=6')
        setElo({ teams: data.teams || [], players: data.players || [] })
      } catch (error) {
        console.error('Failed to fetch Elo data:', error)
      } finally {
        setEloLoading(false)
      }
    }
    fetchElo()
  }, [])

  const LogoMark = () => (
    <div className="relative inline-flex items-center justify-center">
      <div className="absolute inset-0 rounded-full bg-emerald-400/30 blur-2xl" />
      <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-300/40 bg-emerald-500/10 text-emerald-200 shadow-[0_0_35px_rgba(16,185,129,0.45)]">
        <Sparkles className="h-8 w-8" />
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-[#060708] text-white">
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-emerald-400/10 bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.18),_rgba(6,7,8,0.85)_45%,_rgba(6,7,8,1)_75%)]">
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
              <LogoMark />
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mb-6 text-4xl font-semibold tracking-tight sm:text-6xl md:text-7xl"
            >
              <span className="bg-gradient-to-r from-emerald-200 via-emerald-100 to-teal-200 bg-clip-text text-transparent">
                VLR Pulse
              </span>
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="mb-8 text-lg text-emerald-100/70 sm:text-xl"
            >
              Precision Elo signals, match insights, and performance context for Valorant esports.
              Built to feel like a sleek overlay of the scene.
            </motion.p>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="flex flex-col items-center justify-center gap-4 sm:flex-row"
            >
              <Link
                href="/matches"
                className="group inline-flex items-center gap-2 rounded-full border border-emerald-300/40 bg-emerald-500/10 px-6 py-3 text-sm font-semibold text-emerald-50 shadow-[0_0_35px_rgba(16,185,129,0.35)] transition hover:border-emerald-200/70 hover:bg-emerald-400/20"
              >
                Explore Matches
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                href="/teams"
                className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-white/80 transition hover:border-white/30 hover:bg-white/10"
              >
                View Teams
              </Link>
            </motion.div>
          </motion.div>
        </div>
        
        {/* Animated background elements */}
        <div className="absolute inset-0 -z-0">
          <div className="absolute left-1/4 top-1/4 h-72 w-72 rounded-full bg-emerald-400/25 blur-3xl" />
          <div className="absolute right-1/4 bottom-1/4 h-96 w-96 rounded-full bg-teal-400/15 blur-3xl" />
          <div className="absolute left-1/2 top-0 h-px w-[480px] -translate-x-1/2 bg-gradient-to-r from-transparent via-emerald-200/60 to-transparent" />
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
                <div className="group rounded-2xl border border-white/10 bg-white/5 p-6 shadow-[0_0_30px_rgba(0,0,0,0.35)] backdrop-blur transition hover:border-emerald-300/40 hover:bg-white/10">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-white/70">{statConfig.label}</p>
                    <Icon className={`h-4 w-4 ${statConfig.color}`} />
                  </div>
                  <motion.div
                    key={value}
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="mt-4 text-3xl font-semibold text-white"
                  >
                    {value}
                  </motion.div>
                </div>
              </motion.div>
            )
          })}
        </motion.div>
      </section>

      {/* Elo Spotlight */}
      <section className="container py-8 md:py-16">
        <div className="grid gap-8 lg:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="rounded-3xl border border-emerald-400/20 bg-gradient-to-br from-emerald-500/10 via-white/5 to-transparent p-6 shadow-[0_0_45px_rgba(16,185,129,0.15)] backdrop-blur"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-emerald-200/70">Leaderboard</p>
                <h2 className="mt-2 text-2xl font-semibold">Top Elo Teams</h2>
              </div>
              <Trophy className="h-6 w-6 text-emerald-200/80" />
            </div>
            <div className="mt-6 space-y-3">
              {(eloLoading ? Array.from({ length: 6 }) : elo.teams).map((team, index) => (
                <motion.div
                  key={eloLoading ? `team-${index}` : team.team}
                  initial={{ opacity: 0, y: 10, filter: 'blur(8px)' }}
                  whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold text-emerald-200/80">#{index + 1}</span>
                    <span className="text-sm font-semibold text-white">
                      {eloLoading ? 'Loading...' : team.team}
                    </span>
                  </div>
                  <span className="text-sm text-emerald-100/80">
                    {eloLoading ? '--' : team.rating?.toFixed(1)} Elo
                  </span>
                </motion.div>
              ))}
            </div>
            <Link
              href="/teams"
              className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-emerald-200 transition hover:text-emerald-100"
            >
              Full Team Rankings
              <ArrowRight className="h-4 w-4" />
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 via-white/5 to-transparent p-6 shadow-[0_0_45px_rgba(0,0,0,0.4)] backdrop-blur"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-white/50">Leaderboard</p>
                <h2 className="mt-2 text-2xl font-semibold">Top Elo Players</h2>
              </div>
              <TrendingUp className="h-6 w-6 text-white/70" />
            </div>
            <div className="mt-6 space-y-3">
              {(eloLoading ? Array.from({ length: 6 }) : elo.players).map((player, index) => (
                <motion.div
                  key={eloLoading ? `player-${index}` : player.player}
                  initial={{ opacity: 0, y: 10, filter: 'blur(8px)' }}
                  whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold text-white/70">#{index + 1}</span>
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {eloLoading ? 'Loading...' : player.player}
                      </p>
                      <p className="text-xs text-white/50">
                        {eloLoading ? '---' : player.team || 'Free Agent'}
                      </p>
                    </div>
                  </div>
                  <span className="text-sm text-white/80">
                    {eloLoading ? '--' : player.rating?.toFixed(1)} Elo
                  </span>
                </motion.div>
              ))}
            </div>
            <Link
              href="/players"
              className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-white/80 transition hover:text-white"
            >
              Full Player Rankings
              <ArrowRight className="h-4 w-4" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container py-16">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-12 text-center"
        >
          <h2 className="mb-4 text-3xl font-semibold tracking-tight text-white">Explore The Signal</h2>
          <p className="text-white/60">
            Everything you need to analyze Valorant esports data.
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
                <div className="group relative h-full overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-6 transition hover:border-emerald-300/30 hover:bg-white/10">
                  <div className={`absolute inset-0 bg-gradient-to-br ${feature.color} opacity-0 transition-opacity group-hover:opacity-10`} />
                  <div className="relative">
                    <div className={`mb-4 inline-flex rounded-2xl bg-gradient-to-br ${feature.color} p-3 shadow-[0_0_25px_rgba(0,0,0,0.25)]`}>
                      <Icon className="h-6 w-6 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
                    <p className="mt-2 text-sm text-white/60">{feature.description}</p>
                    <Link href={feature.href} className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-emerald-200 transition hover:text-emerald-100">
                      Learn More
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </Link>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
