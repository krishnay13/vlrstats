'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'
import { Sparkles, Users, User, Calendar, Trophy } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/', label: 'Home', icon: Sparkles },
  { href: '/matches', label: 'Matches', icon: Calendar },
  { href: '/teams', label: 'Teams', icon: Users },
  { href: '/players', label: 'Players', icon: User },
  { href: '/rankings', label: 'Rankings', icon: Trophy },
]

export default function Navigation() {
  const pathname = usePathname()

  return (
    <motion.nav
      initial={{ y: -40, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="sticky top-4 z-50 w-full px-4"
    >
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between rounded-full border border-white/10 bg-[#0b0e10]/80 px-6 py-3 shadow-[0_10px_40px_rgba(0,0,0,0.45)] backdrop-blur">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Link href="/" className="flex items-center space-x-3">
            <span className="relative inline-flex h-9 w-9 items-center justify-center">
              <span className="absolute inset-0 rounded-xl bg-emerald-400/30 blur-md" />
              <span className="relative inline-flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-300/40 bg-gradient-to-br from-emerald-500/20 to-teal-500/20">
                <svg className="h-5 w-5 text-emerald-200" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2L4 7v10l8 5 8-5V7l-8-5zm0 2.5l5.5 3.44v6.62L12 18.5l-5.5-3.94V7.94L12 4.5z" />
                  <path d="M12 8L9 10v4l3 2 3-2v-4l-3-2z" opacity="0.7" />
                </svg>
              </span>
            </span>
            <span className="text-lg font-semibold tracking-wide bg-gradient-to-r from-emerald-100 to-teal-200 bg-clip-text text-transparent">
              VCT Stats
            </span>
          </Link>
        </motion.div>

        <div className="flex items-center gap-2">
          {navItems.map((item, index) => {
            const Icon = item.icon
            const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href))
            
            return (
              <motion.div
                key={item.href}
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * (index + 1) }}
              >
                <Link
                  href={item.href}
                  className={cn(
                    "relative flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all",
                    isActive
                      ? "bg-emerald-500/15 text-emerald-100 shadow-[0_0_20px_rgba(16,185,129,0.25)]"
                      : "text-white/70 hover:bg-white/10 hover:text-white"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 rounded-full border border-emerald-300/20"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                </Link>
              </motion.div>
            )
          })}
        </div>
      </div>
    </motion.nav>
  )
}
