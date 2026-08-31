import { requestJson } from "./plants"

export type AuthSession = {
  authenticated: boolean
  user: { initials: string; label: string; role: string } | null
}

export function fetchSession(signal?: AbortSignal): Promise<AuthSession> {
  return requestJson<AuthSession>("/api/v1/auth/session", { signal })
}

export function login(email: string, password: string): Promise<AuthSession> {
  return requestJson<AuthSession>("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
}

export function logout(): Promise<AuthSession> {
  return requestJson<AuthSession>("/api/v1/auth/logout", { method: "POST" })
}
