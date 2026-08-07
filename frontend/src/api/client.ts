export const API_URL = import.meta.env.VITE_API_URL || '/api'

export class ApiError extends Error {
  status: number
  constructor(message:string, status:number){ super(message); this.status = status }
}

export async function api<T>(path:string, options:RequestInit = {}):Promise<T>{
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type','application/json')
  const response = await fetch(`${API_URL}${path}`, {...options, headers})
  if (!response.ok) {
    let detail = `Error ${response.status}`
    try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : body.detail?.message || detail } catch { /* respuesta no JSON */ }
    throw new ApiError(detail, response.status)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const money = (value:number) => new Intl.NumberFormat('es-CO').format(value)
export const shortDate = (value:string|null) => value ? new Intl.DateTimeFormat('es-CO',{day:'2-digit',month:'short'}).format(new Date(value)) : 'Sin vencimiento'
