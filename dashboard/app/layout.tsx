'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { ConstantsProvider } from '@/lib/context/ConstantsContext'
import './globals.css'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        refetchOnWindowFocus: false,
      },
    },
  }))

  return (
    <html lang="en">
      <head>
        <title>Paraform Dashboard</title>
      </head>
      <body>
        <QueryClientProvider client={queryClient}>
          <ConstantsProvider>
            {children}
          </ConstantsProvider>
        </QueryClientProvider>
      </body>
    </html>
  )
}
