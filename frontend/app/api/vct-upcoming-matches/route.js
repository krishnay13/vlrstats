// frontend/app/api/vct-upcoming-matches/route.js

import { NextResponse } from 'next/server'
import * as cheerio from 'cheerio'

async function fetchHTML(url) {
  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': 'https://www.vlr.gg/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
  }

  const response = await fetch(url, { headers })
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`)
  }
  return await response.text()
}

function parseDateRange(dateStr) {
  // Parse dates like "Jan 15—Feb 16" or "Jan 15, 2026 - Feb 16, 2026"
  const now = new Date()
  const currentYear = now.getFullYear()
  
  // Try to extract dates
  const dateMatch = dateStr.match(/(\w{3})\s+(\d{1,2})(?:,?\s+(\d{4}))?(?:\s*[—–-]\s*)?(\w{3})?\s+(\d{1,2})?(?:,?\s+(\d{4}))?/)
  if (!dateMatch) return null
  
  const [, startMonth, startDay, startYear, endMonth, endDay, endYear] = dateMatch
  
  const monthMap = {
    'Jan': 0, 'Feb': 1, 'Mar': 2, 'Apr': 3, 'May': 4, 'Jun': 5,
    'Jul': 6, 'Aug': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dec': 11
  }
  
  const year = endYear || startYear || currentYear
  const startMonthNum = monthMap[startMonth]
  const endMonthNum = endMonth ? monthMap[endMonth] : startMonthNum
  
  if (startMonthNum === undefined) return null
  
  const startDate = new Date(year, startMonthNum, parseInt(startDay))
  const endDate = endDay ? new Date(year, endMonthNum, parseInt(endDay)) : startDate
  
  return { startDate, endDate }
}

function isUpcoming(startDate, endDate) {
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  
  // Event is upcoming if it hasn't ended yet
  return endDate >= now
}

async function scrapeEventMatches(eventUrl, eventName, eventLogo) {
  try {
    // Build matches URL - try different patterns
    const eventIdMatch = eventUrl.match(/\/event\/(\d+)/)
    if (!eventIdMatch) return []
    
    const eventId = eventIdMatch[1]
    let matchesUrl = `${eventUrl}/matches/?series_id=all`
    
    // Try to get the actual matches URL from the event page
    try {
      const eventHtml = await fetchHTML(eventUrl)
      const $event = cheerio.load(eventHtml)
      const matchesLink = $event('a[href*="/event/matches/"]').first().attr('href')
      if (matchesLink) {
        matchesUrl = matchesLink.startsWith('http') ? matchesLink : `https://www.vlr.gg${matchesLink}`
        if (!matchesUrl.includes('series_id')) {
          matchesUrl += matchesUrl.includes('?') ? '&series_id=all' : '?series_id=all'
        }
      }
    } catch (e) {
      // Fallback to constructed URL
    }
    
    const html = await fetchHTML(matchesUrl)
    const $ = cheerio.load(html)
    
    const matches = []
    const seenMatchIds = new Set()
    
    // Find all links that look like match links
    $('a[href*="/match/"], a[href*="/"]').each((i, elem) => {
      const $elem = $(elem)
      const href = $elem.attr('href')
      
      if (!href) return
      
      // Extract match ID from URL like /123456/match-name or /123456/
      const matchIdMatch = href.match(/\/(\d{4,})\//)
      if (!matchIdMatch) return
      
      const matchId = parseInt(matchIdMatch[1])
      if (isNaN(matchId) || matchId < 1000 || seenMatchIds.has(matchId)) return
      
      // Skip if it's clearly not a match (event, team, player pages)
      if (href.includes('/event/') || href.includes('/team/') || href.includes('/player/')) return
      
      // Find the parent container to extract match info
      const $container = $elem.closest('.wf-card, .match-item, [class*="match"]').length 
        ? $elem.closest('.wf-card, .match-item, [class*="match"]')
        : $elem.parent().parent()
      
      // Extract teams - try multiple selectors
      let team1 = $container.find('.team-name, .match-item-vs-team-name, [class*="team"]').first().text().trim()
      let team2 = $container.find('.team-name, .match-item-vs-team-name, [class*="team"]').last().text().trim()
      
      // If not found, try from link text or nearby text
      if (!team1 || !team2) {
        const linkText = $elem.text().trim()
        const vsMatch = linkText.match(/(.+?)\s+vs\.?\s+(.+)/i)
        if (vsMatch) {
          team1 = vsMatch[1].trim()
          team2 = vsMatch[2].trim()
        }
      }
      
      // Extract date/time
      const dateText = $container.find('.match-item-date, .mod-date, [class*="date"]').text().trim()
      const timeText = $container.find('.match-item-time, .mod-time, [class*="time"]').text().trim()
      
      // Check if match is upcoming (not completed) - look for "Upcoming" text or absence of scores
      const containerText = $container.text()
      const isCompleted = containerText.match(/\d+\s*[:\-]\s*\d+/) && 
                         !containerText.toLowerCase().includes('upcoming') &&
                         !containerText.toLowerCase().includes('tbd')
      const isUpcomingMatch = !isCompleted && (dateText || timeText || containerText.toLowerCase().includes('upcoming'))
      
      if (isUpcomingMatch && team1 && team2 && team1 !== team2) {
        seenMatchIds.add(matchId)
        matches.push({
          match_id: matchId,
          team_a: team1,
          team_b: team2,
          event_name: eventName,
          event_logo: eventLogo,
          date_text: dateText,
          time_text: timeText,
          event_url: eventUrl,
        })
      }
    })
    
    return matches
  } catch (error) {
    console.error(`Error scraping matches for ${eventName}:`, error)
    return []
  }
}

export async function GET() {
  try {
    const eventsUrl = 'https://www.vlr.gg/events/?tier=60'
    const html = await fetchHTML(eventsUrl)
    const $ = cheerio.load(html)
    
    const upcomingEvents = []
    
    // Find all event items - VLR.gg uses specific classes
    $('.event-item, [class*="event-item"]').each((i, elem) => {
      const $elem = $(elem)
      
      // Extract event name - try multiple selectors
      let eventName = $elem.find('.event-item-title, h3, h2, .event-name, [class*="title"]').first().text().trim()
      
      // If not found, try from link text
      if (!eventName) {
        const link = $elem.find('a').first()
        eventName = link.text().trim()
      }
      
      if (!eventName || (!eventName.toLowerCase().includes('vct') && !eventName.toLowerCase().includes('champions tour'))) return
      
      // Extract event URL
      const eventLink = $elem.find('a').first().attr('href')
      if (!eventLink) return
      
      const eventUrl = eventLink.startsWith('http') ? eventLink : `https://www.vlr.gg${eventLink}`
      
      // Extract dates - VLR.gg uses mod-dates class
      let dateText = $elem.find('.mod-dates, .event-item-dates, [class*="date"]').text().trim()
      
      // If not found, look in the entire element
      if (!dateText) {
        const fullText = $elem.text()
        const dateMatch = fullText.match(/(\w{3}\s+\d{1,2}[—–-]\w{3}\s+\d{1,2}|\w{3}\s+\d{1,2},?\s+\d{4}\s*[—–-]\s*\w{3}\s+\d{1,2},?\s+\d{4})/i)
        if (dateMatch) dateText = dateMatch[0]
      }
      
      if (!dateText) return
      
      const dateRange = parseDateRange(dateText)
      if (!dateRange) return
      
      // Check if event is upcoming
      if (!isUpcoming(dateRange.startDate, dateRange.endDate)) return
      
      // Extract logo
      const logoImg = $elem.find('img').first()
      let eventLogo = logoImg.attr('src') || logoImg.attr('data-src')
      if (eventLogo && !eventLogo.startsWith('http')) {
        eventLogo = `https://www.vlr.gg${eventLogo}`
      }
      
      upcomingEvents.push({
        name: eventName,
        url: eventUrl,
        startDate: dateRange.startDate,
        endDate: dateRange.endDate,
        logo: eventLogo,
      })
    })
    
    // Sort events by start date
    upcomingEvents.sort((a, b) => a.startDate - b.startDate)
    
    // Scrape matches from upcoming events (limit to first 3 events to avoid timeout)
    const allMatches = []
    for (const event of upcomingEvents.slice(0, 3)) {
      const matches = await scrapeEventMatches(event.url, event.name, event.logo)
      allMatches.push(...matches)
      
      // Stop if we have enough matches
      if (allMatches.length >= 10) break
    }
    
    // Sort matches by date and return top 5
    const sortedMatches = allMatches.slice(0, 5)
    
    return NextResponse.json(sortedMatches)
  } catch (error) {
    console.error('Error fetching VCT upcoming matches:', error)
    return NextResponse.json({ error: 'Failed to fetch upcoming matches' }, { status: 500 })
  }
}
