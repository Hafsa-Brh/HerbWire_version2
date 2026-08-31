import { requestJson } from "./plants"

export type NewsletterSubscription = {
  email: string
  status: "subscribed" | "already_subscribed"
  created_at: string
}

export function subscribeNewsletter(email: string): Promise<NewsletterSubscription> {
  return requestJson<NewsletterSubscription>("/api/v1/newsletter/subscriptions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  })
}
