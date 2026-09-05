import { ArrowLeft, ChevronRight, Eye, EyeOff, Sprout } from "lucide-react"
import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { fetchSession, login } from "../api/auth"
import loginImage from "../assets/login-monstera.png"

function LoginLogo({ inverse = false }: { inverse?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="HerbWire home">
      <span className={`grid h-9 w-9 place-items-center rounded-full ${inverse ? "bg-sage/20 text-sage" : "bg-forest text-sage"}`}><Sprout size={18} /></span>
      <span className={`font-serif text-xl font-semibold tracking-[-.04em] ${inverse ? "text-cream" : "text-deep"}`}>Herb<span className="text-leaf">Wire</span></span>
    </Link>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    const controller = new AbortController()
    fetchSession(controller.signal)
      .then((session) => {
        if (session.authenticated) navigate("/admin", { replace: true })
      })
      .catch(() => undefined)
    return () => controller.abort()
  }, [navigate])

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError("")
    if (!email.trim() || !password) {
      setError("Enter an email address and password.")
      return
    }
    setLoading(true)
    try {
      const session = await login(email, password)
      if (session.authenticated) navigate("/admin", { replace: true })
      else setError("Invalid email or password.")
    } catch {
      setError("Invalid email or password.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center overflow-hidden bg-paper p-2.5 sm:p-5 lg:p-6">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <img src={loginImage} alt="" aria-hidden="true" className="absolute left-1/2 top-1/2 h-[150vh] w-[150vw] max-w-none -translate-x-1/2 -translate-y-1/2 object-cover opacity-[.16] blur-[42px] saturate-[.9]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(244,247,239,.18),transparent_38%),linear-gradient(180deg,rgba(247,244,236,.28),rgba(247,244,236,.78))]" />
        <div className="absolute -left-12 top-10 h-40 w-56 rounded-[2rem] border border-line/35 bg-paper/28 blur-2xl" />
        <div className="absolute right-10 top-14 h-36 w-48 rounded-[2rem] border border-line/30 bg-paper/20 blur-2xl" />
        <div className="absolute bottom-12 left-12 h-44 w-64 rounded-[2.25rem] border border-line/35 bg-paper/24 blur-2xl" />
        <div className="absolute bottom-10 right-8 h-40 w-56 rounded-[2rem] border border-line/30 bg-paper/18 blur-2xl" />
      </div>
      <div className="relative mx-auto grid w-full max-w-[1220px] overflow-hidden rounded-[1.25rem] border border-line bg-paper/94 shadow-[0_24px_90px_rgba(23,63,48,.12)] backdrop-blur-md sm:rounded-[2rem] lg:min-h-[min(680px,calc(100vh-2.5rem))] lg:grid-cols-[.94fr_.9fr]">
        <section className="relative hidden overflow-hidden bg-deep lg:block">
          <img src={loginImage} alt="Monstera leaves in a bright botanical composition" className="absolute inset-0 h-full w-full object-cover object-center opacity-[.9]" />
          <div className="absolute inset-0 bg-gradient-to-t from-deep via-deep/25 to-transparent" />
          <div className="relative flex h-full flex-col p-7 text-cream xl:p-9">
            <LoginLogo inverse />
            <div className="flex-1" />
            <p className="max-w-sm font-serif text-lg leading-relaxed text-cream/75">Shape careful medicinal-plant profiles with provenance, safety checks, and human publication control.</p>
          </div>
        </section>
        <main className="flex items-center justify-center bg-paper/92 p-4 sm:p-7 lg:p-8 xl:p-10">
          <div className="w-full max-w-[28.5rem]">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3 lg:hidden"><LoginLogo /><Link to="/" className="font-sans text-xs text-muted hover:text-leaf">Public site</Link></div>
            <div className="mb-6 hidden lg:block"><LoginLogo /></div>
            <Link to="/" className="mb-4 inline-flex items-center gap-2 font-sans text-xs text-muted hover:text-leaf"><ArrowLeft size={14} /> Return to public site</Link>
            <p className="hw-eyebrow">Local review access</p>
            <h2 className="mt-2 font-serif text-[clamp(2rem,10vw,2.25rem)] font-semibold leading-tight tracking-[-.05em] text-deep">Sign in to the desk</h2>
            <p className="mt-2.5 font-sans text-sm leading-relaxed text-muted">This Milestone 2 desk uses backend-authenticated local development access. Production user management is not implemented yet.</p>
            <form onSubmit={submit} className="mt-5 grid gap-3.5" noValidate>
              <label className="grid gap-2"><span className="font-sans text-xs font-bold uppercase tracking-[.1em] text-forest">Email</span><input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="border border-line bg-paper px-4 py-2.5 font-sans text-sm text-deep outline-none focus:border-leaf" placeholder="you@herbwire.org" autoComplete="email" /></label>
              <label className="grid gap-2"><span className="font-sans text-xs font-bold uppercase tracking-[.1em] text-forest">Password</span><div className="flex border border-line focus-within:border-leaf"><input required type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} className="min-w-0 flex-1 bg-paper px-4 py-2.5 font-sans text-sm text-deep outline-none" placeholder="Enter your password" autoComplete="current-password" /><button type="button" onClick={() => setShowPassword(!showPassword)} className="px-3 text-muted hover:text-leaf" aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label>
              {error ? <p role="alert" className="border border-rust/30 bg-rust/10 p-3 font-sans text-xs leading-relaxed text-rust">{error}</p> : null}
              <button disabled={loading} className="inline-flex items-center justify-center gap-2 bg-forest px-4 py-3 font-sans text-xs font-bold uppercase tracking-[.12em] text-cream hover:bg-leaf disabled:opacity-60">
                {loading ? "Checking access..." : "Enter editorial desk"}
                <ChevronRight size={15} />
              </button>
            </form>
            <div className="mt-4 border border-line bg-sage/15 p-4"><p className="font-sans text-[10px] font-bold uppercase tracking-[.12em] text-leaf">Development-only</p><p className="mt-2 font-sans text-xs text-muted">Access is validated by the FastAPI backend and stored only in an HttpOnly session cookie.</p></div>
          </div>
        </main>
      </div>
    </div>
  )
}
