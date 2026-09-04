import type { ReactNode, RefObject } from "react"

export function ReviewWorkspaceShell({ children, label }: { children: ReactNode; label: string }) {
  return <section aria-label={label} data-review-workspace="shared" className="grid items-stretch gap-5 lg:grid-cols-[.72fr_1.28fr]">{children}</section>
}

export function ReviewPagerNav({ current, pages, label, onPage, headingRef }: { current: number; pages: readonly {title:string}[]; label: string; onPage: (page:number)=>void; headingRef?: RefObject<HTMLHeadingElement | null> }) {
  const active=pages[current-1]
  return <div data-review-detail-pager="shared"><nav aria-label={label} className={`mb-4 grid gap-2 ${pages.length>4?"grid-cols-2 sm:grid-cols-5":"sm:grid-cols-2 xl:grid-cols-4"}`}>{pages.map((page,index)=><button key={page.title} type="button" aria-current={current===index+1?"page":undefined} onClick={()=>onPage(index+1)} className={`min-h-10 border px-3 py-2 text-left font-sans text-[10px] font-bold uppercase tracking-[.06em] ${current===index+1?"border-forest bg-forest text-cream":"border-line bg-paper text-muted hover:border-leaf"}`}>{index+1}. {page.title}</button>)}</nav><div className="flex flex-wrap items-baseline justify-between gap-2 border-y border-line py-3"><h3 ref={headingRef} tabIndex={-1} className="font-serif text-2xl font-semibold text-deep outline-none">{active.title}</h3><p aria-live="polite" className="font-sans text-xs text-muted">Page {current} of {pages.length}</p></div></div>
}

export function ReviewPagerFooter({ current, pages, onPage }: { current:number; pages:number; onPage:(page:number)=>void }) {
  return <div className="mt-auto flex items-center justify-between border-t border-line pt-3"><button type="button" aria-label="Previous detail page" onClick={()=>onPage(current-1)} disabled={current===1} className="border border-line px-3 py-2 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest disabled:opacity-35">Previous</button><span className="font-sans text-xs text-muted">Detail navigation</span><button type="button" aria-label="Next detail page" onClick={()=>onPage(current+1)} disabled={current===pages} className="border border-line px-3 py-2 font-sans text-[10px] font-bold uppercase tracking-[.1em] text-forest disabled:opacity-35">Next</button></div>
}
