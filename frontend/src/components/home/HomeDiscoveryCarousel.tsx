import { ArrowLeft, ArrowRight, ArrowUpRight, ImageOff } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import type { ApiPublicDiscoveryArticle } from "../../api/discoveries"


const AUTOPLAY_MS = 6000

function articleDate(article: ApiPublicDiscoveryArticle) {
  const value = article.sources[0]?.publication_date ?? article.published_at
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })
}

export function HomeDiscoveryCarousel({ items }: { items: ApiPublicDiscoveryArticle[] }) {
  const [index,setIndex]=useState(0),[timerKey,setTimerKey]=useState(0),[hovered,setHovered]=useState(false),[focused,setFocused]=useState(false)
  const [hidden,setHidden]=useState(document.visibilityState==="hidden"),[reducedMotion,setReducedMotion]=useState(false)
  const [failedImages,setFailedImages]=useState<Set<string>>(()=>new Set())
  const touchStart=useRef<number|null>(null), count=items.length
  useEffect(()=>{if(typeof window.matchMedia!=="function")return;const media=window.matchMedia("(prefers-reduced-motion: reduce)");const update=()=>setReducedMotion(media.matches);update();media.addEventListener("change",update);return()=>media.removeEventListener("change",update)},[])
  useEffect(()=>{const update=()=>setHidden(document.visibilityState==="hidden");document.addEventListener("visibilitychange",update);return()=>document.removeEventListener("visibilitychange",update)},[])
  useEffect(()=>{if(count<2||hovered||focused||hidden||reducedMotion)return;const timer=window.setTimeout(()=>setIndex(value=>(value+1)%count),AUTOPLAY_MS);return()=>window.clearTimeout(timer)},[count,focused,hidden,hovered,index,reducedMotion,timerKey])
  if(!count)return null
  const article=items[index],image=article.hero_image?.local_path
  function move(step:number){setIndex(value=>(value+step+count)%count);setTimerKey(value=>value+1)}
  return <section aria-roledescription="carousel" aria-label="Latest published discoveries" className="hw-container py-6 md:py-8"
    onMouseEnter={()=>setHovered(true)} onMouseLeave={()=>setHovered(false)} onFocusCapture={()=>setFocused(true)}
    onBlurCapture={event=>{if(!event.currentTarget.contains(event.relatedTarget))setFocused(false)}}
    onTouchStart={event=>{touchStart.current=event.touches[0]?.clientX??null}} onTouchEnd={event=>{if(touchStart.current===null)return;const delta=(event.changedTouches[0]?.clientX??touchStart.current)-touchStart.current;if(Math.abs(delta)>45)move(delta>0?-1:1);touchStart.current=null}}>
    <div className="grid items-center gap-6 border-b border-line pb-6 md:grid-cols-[minmax(0,.95fr)_minmax(0,1.05fr)] md:gap-8 lg:gap-10">

    <div className="min-w-0 py-2">
        <p className="hw-eyebrow">{article.article_type??article.category}</p>
        <h1 className="mt-3 min-h-[4.4em] line-clamp-4 break-words font-serif text-[clamp(1.6rem,2.6vw,2.5rem)] font-semibold leading-[1.1] tracking-[-.035em] text-deep">
  <Link
    className="transition hover:text-leaf"
    to={`/discoveries/${article.slug}`}
    title={article.headline}
  >
    {article.headline}
  </Link>
</h1>

        <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 font-sans text-[11px] text-muted"><span>{articleDate(article)}</span>{article.evidence_strength?<span>{article.evidence_strength} evidence</span>:null}<Link to={`/discoveries/${article.slug}`} className="inline-flex items-center gap-1 font-bold text-leaf hw-link">Read discovery <ArrowUpRight size={14}/></Link></div>
      </div>
      <Link to={`/discoveries/${article.slug}`} className="group block min-w-0" aria-label={`Read discovery: ${article.headline}`}>
        <div className="relative aspect-video w-full overflow-hidden rounded-tr-[3rem] bg-sage/20 md:rounded-tr-[4rem]">{image&&!failedImages.has(article.slug)?<img src={image} alt={article.hero_image.alt_text||"Discovery editorial cover"} className="absolute inset-0 h-full w-full object-cover transition duration-500 group-hover:scale-[1.02] motion-reduce:transition-none motion-reduce:group-hover:scale-100" onError={()=>setFailedImages(values=>new Set(values).add(article.slug))}/>:<div className="grid h-full place-items-center text-center text-muted"><div><ImageOff className="mx-auto" size={30}/><p className="mt-3 font-sans text-xs uppercase tracking-[.12em]">Image temporarily unavailable</p></div></div>}</div>
      </Link>
    </div>
    <div className="flex items-center gap-4 pt-5"><span className="min-w-12 font-sans text-[11px] font-bold text-forest">{String(index+1).padStart(2,"0")} / {String(count).padStart(2,"0")}</span><div className="h-px flex-1 bg-line" aria-hidden="true"><div className="h-px bg-leaf transition-[width] duration-300" style={{width:`${((index+1)/count)*100}%`}}/></div><button type="button" onClick={()=>move(-1)} aria-label="Show previous discovery" className="grid h-11 w-11 place-items-center rounded-full border border-line text-leaf transition hover:border-leaf hover:bg-sage/20"><ArrowLeft size={18}/></button><button type="button" onClick={()=>move(1)} aria-label="Show next discovery" className="grid h-11 w-11 place-items-center rounded-full border border-line text-leaf transition hover:border-leaf hover:bg-sage/20"><ArrowRight size={18}/></button></div>
    <p className="sr-only" aria-live="polite" aria-atomic="true">Slide {index+1} of {count}: {article.headline}</p>
  </section>
}
