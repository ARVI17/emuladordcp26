import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { registerSW } from 'virtual:pwa-register'
import App from './App'
import './styles.css'
import './shell.css'

registerSW({ immediate: true })
const client = new QueryClient({ defaultOptions: { queries: { staleTime: 15_000, retry: 1 }, mutations: { retry: 0 } } })
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={client}><App /></QueryClientProvider></React.StrictMode>)
