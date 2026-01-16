'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { Trophy, TrendingUp, Users, Calendar, ArrowRight, BarChart3, Sparkles, Clock, Heart } from 'lucide-react'
import { fetchJson } from '@/app/lib/api'

const formatMatchDate = (match) => {
  const raw = match.match_ts_utc || match.match_date
  if (!raw) return 'TBD'
  const date = new Date(raw)
  if (isNaN(date.getTime())) return raw.substring(0, 10)
  // Use local timezone automatically via Date object
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const formatMatchDateTime = (match) => {
  const raw = match.match_ts_utc || match.match_date
  if (!raw) return 'TBD'
  // The timestamps are stored in EST, so add 5 hours to convert to UTC before displaying in local timezone
  const estDate = new Date(raw)
  if (isNaN(estDate.getTime())) return raw
  // Add 5 hours to convert EST to UTC
  const utcDate = new Date(estDate.getTime() + 5 * 60 * 60 * 1000)
  // Display in user's local timezone
  const datePart = utcDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  const timePart = utcDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
  return `${datePart} • ${timePart}`
}

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

const DATE_RANGES = [
  { value: 'all-time', label: 'Since 2024' },
  { value: '2024', label: '2024' },
  { value: '2025', label: '2025' },
  { value: 'last-6-months', label: 'Last 6 Months' },
  { value: 'last-3-months', label: 'Last 3 Months' },
]

export default function HomePage() {
  const [upcomingMatches, setUpcomingMatches] = useState([])
  const [allMatches, setAllMatches] = useState([])
  const [showAll, setShowAll] = useState(false)
  const [matchesLoading, setMatchesLoading] = useState(true)
  const [elo, setElo] = useState({ teams: [], players: [] })
  const [eloLoading, setEloLoading] = useState(true)
  const [dateRange, setDateRange] = useState('all-time')

  useEffect(() => {
    async function fetchUpcomingMatches() {
      try {
        // Try database first (faster, more reliable)
        const dbData = await fetchJson('/api/upcoming-matches')
        if (dbData && dbData.length > 0) {
          setAllMatches(dbData)
          setUpcomingMatches(dbData.slice(0, 8))
          setMatchesLoading(false)
          return
        }
      } catch (error) {
        console.error('Failed to fetch database matches:', error)
      }
      
      // Fallback to live scrape if database is empty
      try {
        const data = await fetchJson('/api/vct-upcoming-matches')
        if (data && data.length > 0) {
          setAllMatches(data)
          setUpcomingMatches(data.slice(0, 8))
        }
      } catch (error) {
        console.error('Failed to fetch live upcoming matches:', error)
      } finally {
        setMatchesLoading(false)
      }
    }
    fetchUpcomingMatches()
  }, [])

  const displayedMatches = showAll ? allMatches : upcomingMatches

  useEffect(() => {
    async function fetchElo() {
      setEloLoading(true)
      try {
        const url = `/api/elo?topTeams=5&topPlayers=5&dateRange=${encodeURIComponent(dateRange)}`
        const data = await fetchJson(url)
        setElo({ teams: data.teams || [], players: data.players || [] })
      } catch (error) {
        console.error('Failed to fetch Elo data:', error)
      } finally {
        setEloLoading(false)
      }
    }
    fetchElo()
  }, [dateRange])

  const LogoMark = () => (
    <div className="relative inline-flex items-center justify-center">
      <div className="absolute inset-0 rounded-full bg-emerald-400/30 blur-2xl" />
      <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl overflow-hidden shadow-[0_0_35px_rgba(16,185,129,0.45)]">
        <img 
          src="/vctpulselogo.png" 
          alt="VCT Pulse Logo" 
          className="h-16 w-16 object-contain"
        />
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
                VCT Pulse
              </span>
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="mb-8 text-lg text-emerald-100/70 sm:text-xl"
            >
              Real-time VCT match tracking, Elo rankings, and performance analytics.
              Your pulse on the Valorant Champions Tour.
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

      {/* Upcoming Matches Section */}
      <section className="container py-16">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="mb-8 flex items-center justify-between"
        >
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-white">Upcoming Matches</h2>
            <p className="mt-1 text-sm text-white/60">Next scheduled matches in Valorant esports</p>
          </div>
          <Link
            href="/matches"
            className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-200 transition hover:text-emerald-100"
          >
            View All
            <ArrowRight className="h-4 w-4" />
          </Link>
        </motion.div>

        {matchesLoading ? (
          <div className="flex items-center justify-center py-12">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              className="h-6 w-6 rounded-full border-2 border-emerald-300/70 border-t-transparent"
            />
          </div>
        ) : displayedMatches.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl border border-white/10 bg-white/5 p-12 text-center"
          >
            <Calendar className="mx-auto h-12 w-12 text-white/30" />
            <p className="mt-4 text-white/60">No upcoming matches scheduled</p>
          </motion.div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {displayedMatches.map((match, index) => (
              <motion.div
                key={match.match_id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -2 }}
              >
                <Link
                  href={`/matches/${match.match_id}`}
                  className="group block rounded-2xl border border-white/10 bg-white/5 p-6 shadow-[0_0_30px_rgba(0,0,0,0.35)] backdrop-blur transition hover:border-emerald-300/40 hover:bg-white/10"
                >
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs text-white/60">
                      <Clock className="h-3.5 w-3.5" />
                      <span>{match.date_text || match.time_text || formatMatchDateTime(match)}</span>
                    </div>
                    {match.event_logo && (
                      <img
                        src={match.event_logo}
                        alt={match.event_name}
                        className="h-4 w-4 object-contain opacity-60"
                      />
                    )}
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      {match.team_a_logo ? (
                        <img
                          src={match.team_a_logo}
                          alt={match.team_a}
                          className="h-5 w-5 rounded object-contain"
                        />
                      ) : (
                        <div className="h-5 w-5 rounded bg-white/10" />
                      )}
                      <span className={`text-sm font-medium ${match.team_a === 'TBD' ? 'text-white/60 italic' : 'text-white'}`}>
                        {match.team_a}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-2 text-xs text-white/40">
                      <div className="h-px flex-1 bg-white/10" />
                      <span>vs</span>
                      <div className="h-px flex-1 bg-white/10" />
                    </div>
                    
                    <div className="flex items-center gap-3">
                      {match.team_b_logo ? (
                        <img
                          src={match.team_b_logo}
                          alt={match.team_b}
                          className="h-5 w-5 rounded object-contain"
                        />
                      ) : (
                        <div className="h-5 w-5 rounded bg-white/10" />
                      )}
                      <span className={`text-sm font-medium ${match.team_b === 'TBD' ? 'text-white/60 italic' : 'text-white'}`}>
                        {match.team_b}
                      </span>
                    </div>
                  </div>

                  {match.tournament && (
                    <div className="mt-4 pt-4 border-t border-white/5">
                      <p className="text-xs text-white/50 truncate">
                        {match.tournament}
                      </p>
                    </div>
                  )}
                </Link>
              </motion.div>
              ))}
            </div>
            {allMatches.length > 8 && (
              <div className="mt-6 flex justify-center">
                <button
                  onClick={() => setShowAll(!showAll)}
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-white/80 transition hover:border-white/30 hover:bg-white/10"
                >
                  {showAll ? 'Show Less' : `View More (${allMatches.length - 8} more)`}
                  <ArrowRight className={`h-4 w-4 transition-transform ${showAll ? 'rotate-90' : ''}`} />
                </button>
              </div>
            )}
          </>
        )}
      </section>

      {/* Elo Spotlight */}
      <section className="container py-8 md:py-16">
        <div className="mb-6 flex items-center justify-center">
          <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-1 py-1">
            {DATE_RANGES.map((range) => {
              const isActive = dateRange === range.value
              return (
                <button
                  key={range.value}
                  type="button"
                  onClick={() => setDateRange(range.value)}
                  className={`rounded-full px-3 py-1 text-xs sm:text-sm font-medium transition ${
                    isActive
                      ? 'bg-emerald-400/80 text-black shadow-[0_0_18px_rgba(16,185,129,0.45)]'
                      : 'bg-transparent text-white/70 hover:bg-white/10'
                  }`}
                >
                  {range.label}
                </button>
              )
            })}
          </div>
        </div>
        <div className="grid gap-8 lg:grid-cols-2 items-stretch">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="flex h-full flex-col rounded-3xl border border-emerald-400/20 bg-gradient-to-br from-emerald-500/10 via-white/5 to-transparent p-6 shadow-[0_0_45px_rgba(16,185,129,0.15)] backdrop-blur"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-emerald-200/70">Leaderboard</p>
                <h2 className="mt-2 text-2xl font-semibold">Top Elo Teams</h2>
              </div>
              <Trophy className="h-6 w-6 text-emerald-200/80" />
            </div>
            <div className="mt-6 flex-1 space-y-3 min-h-[280px]">
              {(eloLoading ? Array.from({ length: 5 }) : elo.teams).map((team, index) => (
                <motion.div
                  key={eloLoading ? `team-${index}` : team.team}
                  initial={{ opacity: 0, y: 10, filter: 'blur(8px)' }}
                  whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-2 h-[56px]"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className="text-sm font-semibold text-emerald-200/80 w-8 flex-shrink-0">
                      #{index + 1}
                    </span>
                    {!eloLoading && team.logo_url ? (
                      <img
                        src={team.logo_url}
                        alt={`${team.team} logo`}
                        className="h-5 w-5 bg-white/5 object-contain flex-shrink-0"
                      />
                    ) : (
                      <div className="h-5 w-5 flex-shrink-0" />
                    )}
                    <span className="text-sm font-semibold text-white truncate">
                      {eloLoading ? 'Loading...' : team.team}
                    </span>
                  </div>
                  <span className="text-sm text-emerald-100/80 flex-shrink-0 ml-4">
                    {eloLoading ? '--' : team.rating?.toFixed(1)} Elo
                  </span>
                </motion.div>
              ))}
            </div>
            <Link
              href="/rankings"
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
            className="flex h-full flex-col rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 via-white/5 to-transparent p-6 shadow-[0_0_45px_rgba(0,0,0,0.4)] backdrop-blur w-full"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-white/50">Leaderboard</p>
                <h2 className="mt-2 text-2xl font-semibold">Top Elo Players</h2>
              </div>
              <TrendingUp className="h-6 w-6 text-white/70" />
            </div>
            <div className="mt-6 flex-1 space-y-3 min-h-[280px]">
              {(eloLoading ? Array.from({ length: 5 }) : elo.players).map((player, index) => (
                <motion.div
                  key={eloLoading ? `player-${index}` : player.player}
                  initial={{ opacity: 0, y: 10, filter: 'blur(8px)' }}
                  whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-2 h-[56px]"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className="text-sm font-semibold text-white/70 w-8 flex-shrink-0">#{index + 1}</span>
                    {!eloLoading && player.team_logo ? (
                      <img
                        src={player.team_logo}
                        alt={`${player.team} logo`}
                        className="h-5 w-5 bg-white/5 object-contain flex-shrink-0"
                      />
                    ) : (
                      <div className="h-5 w-5 flex-shrink-0" />
                    )}
                    <div className="flex flex-col justify-center min-w-0 flex-1">
                      <p className="text-sm font-semibold text-white leading-tight">
                        {eloLoading ? 'Loading...' : player.player}
                      </p>
                      <p className="text-xs text-white/50 leading-tight">
                        {eloLoading ? '---' : player.team || 'Free Agent'}
                      </p>
                    </div>
                  </div>
                  <span className="text-sm text-white/80 flex-shrink-0 ml-4">
                    {eloLoading ? '--' : player.rating?.toFixed(1)} Elo
                  </span>
                </motion.div>
              ))}
            </div>
            <Link
              href="/rankings"
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
