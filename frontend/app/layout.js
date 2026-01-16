import './globals.css'
import { Inter } from 'next/font/google'
import Navigation from './components/navigation'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'VCT Pulse - Valorant Esports Analytics',
  description: 'Comprehensive statistics and analytics for Valorant esports matches, teams, and players',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className={`${inter.className} bg-[#060708] text-white`}>
        <Navigation />
        <main className="min-h-screen bg-[#060708] text-white">
          {children}
        </main>
      </body>
    </html>
  );
}
