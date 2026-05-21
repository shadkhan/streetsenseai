import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: {
    default: 'StreetSense AI',
    template: '%s · StreetSense AI',
  },
  description: 'Cross-Authority Roadworks Intelligence Platform — corridor risk scoring, D-TRO integration, underground asset strike risk and AI-powered permit analytics.',
  icons: {
    icon: [
      { url: '/icon.svg', type: 'image/svg+xml' },
      { url: '/favicon.ico', sizes: '32x32' },
    ],
    shortcut: '/favicon.ico',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        className={`${inter.variable} ${jetbrainsMono.variable}`}
      >
        <body className="bg-surface-page text-ink antialiased">
          <Providers>{children}</Providers>
        </body>
      </html>
    </ClerkProvider>
  )
}
