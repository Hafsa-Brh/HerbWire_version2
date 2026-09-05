import { Menu, Search, Sprout, X } from "lucide-react"
import type { ReactNode } from "react"
import { useEffect, useRef, useState } from "react"
import { Link, NavLink, useLocation, useNavigate, useSearchParams } from "react-router-dom"

const navItems = [
  { label: "Plants", to: "/plants" },
  { label: "New Discoveries", to: "/discoveries" },
  { label: "Materials & Craft", to: "/materials-and-craft" },
  { label: "The Field Cabinet", to: "/field-cabinet" },
] as const

export function SiteShell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchDraft, setSearchDraft] = useState("")
  const shellRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const [shellHeight, setShellHeight] = useState(0)
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const activeQuery = searchParams.get("q") ?? ""
  const isPlantsPage = location.pathname === "/plants"

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchOpen(isPlantsPage && Boolean(activeQuery))
      setSearchDraft(activeQuery)
      setMenuOpen(false)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [activeQuery, isPlantsPage, location.pathname])

  useEffect(() => {
    const updateHeight = () => setShellHeight(shellRef.current?.offsetHeight ?? 0)
    updateHeight()
    window.addEventListener("resize", updateHeight)
    let observer: ResizeObserver | undefined
    if (typeof ResizeObserver !== "undefined" && shellRef.current) {
      observer = new ResizeObserver(updateHeight)
      observer.observe(shellRef.current)
    }
    return () => {
      window.removeEventListener("resize", updateHeight)
      observer?.disconnect()
    }
  }, [menuOpen, searchOpen])

  useEffect(() => {
    if (searchOpen) searchInputRef.current?.focus()
  }, [searchOpen])

  const submitSearch = () => {
    const trimmed = searchDraft.trim()
    if (trimmed) navigate(`/plants?q=${encodeURIComponent(trimmed)}`)
  }

  const closeSearch = () => {
    setSearchOpen(false)
    setSearchDraft("")
    if (isPlantsPage) navigate("/plants")
  }

  const handleSearchKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault()
      submitSearch()
    }
  }

  return (
    <>
      <div ref={shellRef} className="fixed inset-x-0 top-0 z-40 bg-paper">
        <div className="border-b border-line bg-deep px-3 py-2 text-center font-sans text-[9px] font-semibold uppercase leading-relaxed tracking-[.14em] text-cream sm:px-4 sm:text-[10px] sm:tracking-[.18em]">
          Reviewed medicinal-plant knowledge / safety-qualified and source-led
        </div>
        <header className="border-b border-line bg-paper">
          <div className="hw-container flex h-[82px] items-center justify-between gap-2 sm:h-[92px] sm:gap-6">
            <button aria-label="Open menu" className="flex h-10 w-10 items-center justify-start text-forest md:hidden" onClick={() => setMenuOpen(!menuOpen)}>
              {menuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
            <Link to="/" className="group flex min-w-0 items-center gap-2 sm:gap-3" aria-label="HerbWire home">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-leaf/40 text-leaf transition group-hover:bg-sage/30 sm:h-11 sm:w-11">
                <Sprout size={22} strokeWidth={1.6} />
              </span>
              <span className="min-w-0">
                <span className="block font-serif text-[1.65rem] font-semibold leading-none tracking-[-.055em] text-deep sm:text-[2rem]">
                  Herb<span className="text-leaf">Wire</span>
                </span>
                <span className="mt-1 hidden font-sans text-[9px] font-bold uppercase tracking-[.18em] text-muted min-[390px]:block sm:tracking-[.21em]">Botanical knowledge, honestly grown</span>
              </span>
            </Link>
            <div className="hidden items-center gap-4 md:flex">
              <div className="flex items-center gap-3">
                <div className={`overflow-hidden transition-all duration-300 ease-out ${searchOpen ? "w-[min(24rem,32vw)] opacity-100" : "w-0 opacity-0"}`}>
                  <div className="flex h-11 items-center border-b border-forest/45 bg-transparent px-1">
                    <Search size={18} className="mr-3 shrink-0 text-forest" />
                    <input ref={searchInputRef} value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} onKeyDown={handleSearchKeyDown} className="min-w-0 flex-1 bg-transparent font-sans text-[1rem] text-deep outline-none placeholder:text-muted/75" placeholder="Search plants..." aria-label="Search HerbWire plants" />
                    {searchDraft ? <button type="button" onClick={() => setSearchDraft("")} aria-label="Clear search" className="ml-3 text-muted transition hover:text-leaf"><X size={16} /></button> : null}
                  </div>
                </div>
                {!searchOpen ? <span className="font-serif text-sm italic text-muted">Stories from the green world</span> : null}
                <button aria-label={searchOpen ? "Close search" : "Search HerbWire"} className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-line text-forest transition hover:border-leaf hover:text-leaf" onClick={() => { if (searchOpen && !isPlantsPage) closeSearch(); else setSearchOpen(true) }}>
                  <Search size={18} />
                </button>
              </div>
              <Link to="/login" className="border border-forest px-3 py-2 font-sans text-[10px] font-bold uppercase tracking-[.12em] text-forest transition hover:bg-forest hover:text-cream">Editorial login</Link>
            </div>
            <button aria-label={searchOpen ? "Close search" : "Search HerbWire"} className="grid h-10 w-10 place-items-center text-forest md:hidden" onClick={() => { if (searchOpen && !isPlantsPage) closeSearch(); else setSearchOpen(true) }}>
              <Search size={20} />
            </button>
          </div>
        </header>
        <div className={`${menuOpen ? "block" : "hidden"} border-b border-line bg-paper/95 backdrop-blur md:block`}>
          <nav aria-label="Primary navigation">
            <div className="hw-container flex flex-col gap-0 md:flex-row md:flex-wrap md:items-center md:justify-center md:gap-x-8">
              {navItems.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => `border-b border-line py-3 font-sans text-xs font-semibold transition md:border-0 md:py-4 ${isActive ? "text-leaf" : "text-forest hover:text-leaf"}`}>{item.label}</NavLink>)}
              <Link to="/login" className="border-b border-line py-3 font-sans text-xs font-bold uppercase tracking-[.1em] text-leaf md:hidden">Editorial login</Link>
            </div>
          </nav>
        </div>
        {searchOpen ? (
          <div className="border-b border-line bg-paper px-4 py-4 md:hidden">
            <div className="hw-container">
              <div className="flex items-center border-b border-forest/45 bg-transparent px-1">
                <Search size={18} className="mr-3 shrink-0 text-forest" />
                <input ref={searchInputRef} value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} onKeyDown={handleSearchKeyDown} className="min-w-0 flex-1 bg-transparent py-2 font-sans text-base text-deep outline-none placeholder:text-muted/75" placeholder="Search plants..." aria-label="Search HerbWire plants" />
                {searchDraft ? <button type="button" onClick={() => setSearchDraft("")} aria-label="Clear search" className="ml-3 text-muted transition hover:text-leaf"><X size={16} /></button> : null}
              </div>
            </div>
          </div>
        ) : null}
      </div>
      <div aria-hidden="true" style={{ height: shellHeight || undefined }} />
      {children}
    </>
  )
}

export function Footer() {
  return (
    <footer className="bg-deep text-cream">
      <div className="hw-container grid gap-12 py-14 md:grid-cols-[1.5fr_1fr_1fr] md:py-20">
        <div>
          <div className="font-serif text-3xl tracking-[-.04em]">Herb<span className="text-sage">Wire</span></div>
          <p className="mt-4 max-w-xs font-serif text-lg leading-relaxed text-cream/70">A careful medicinal-plant encyclopedia with transparent provenance, safety context, and human publication control.</p>
        </div>
        <div>
          <p className="hw-eyebrow !text-sage">Explore</p>
          <div className="mt-4 grid gap-2 font-sans text-sm text-cream/75">
            <Link to="/plants" className="hover:text-white">Plants</Link>
            <Link to="/discoveries" className="hover:text-white">New Discoveries</Link>
            <Link to="/materials-and-craft" className="hover:text-white">Materials &amp; Craft</Link>
            <Link to="/field-cabinet" className="hover:text-white">The Field Cabinet</Link>
          </div>
        </div>
        <div>
          <p className="hw-eyebrow !text-sage">Editorial policy</p>
          <p className="mt-4 max-w-xs font-sans text-sm leading-relaxed text-cream/75">No diagnosis, no dosage advice, no automatic publication, and no unsupported cure claims.</p>
        </div>
      </div>
      <div className="border-t border-cream/15">
        <div className="hw-container flex flex-col gap-3 py-5 font-sans text-[10px] uppercase tracking-[.16em] text-cream/45 sm:flex-row sm:justify-between">
          <span>Reviewed medicinal plant archive</span>
          <span>Made for careful botanical publishing</span>
        </div>
      </div>
    </footer>
  )
}
