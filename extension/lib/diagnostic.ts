// Serialized in the isolated world. Output is a closed vocabulary structural
// skeleton: no text, labels, ids, hrefs, images, HTML or arbitrary class names.
export function diagnoseVisible(){
 const visible=(el:Element)=>!!el.getClientRects().length&&el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})
 const prohibited='form,input,textarea,select,iframe,script,style,[contenteditable],canvas,img,[hidden],[aria-hidden="true"]'
 const base={format:'club-lab-skeleton-1',provider_verified:false,profile_verified:false,remote_navigation:false,remote_write:false}
 if(Array.from(document.querySelectorAll('input[type=password],input[type=email],input[autocomplete=one-time-code],input[autocomplete=username],input[autocomplete^="cc-"]')).some(visible))return {...base,code:'sensitive_screen',regions:[]}
 const roles=new Set(['list','listitem','grid','gridcell','row','table','heading','status','progressbar','navigation','tab','tabpanel'])
 const tags=new Set(['section','article','header','div','span','p','h1','h2','h3','h4','ul','ol','li','table','thead','tbody','tr','td','th','button','a','nav','main','strong','small','b','i','label'])
 const tag=(el:Element)=>tags.has(el.tagName.toLowerCase())?el.tagName.toLowerCase():'custom-element'
 const words=new Set(['players','player','items','item','list','listitem','card','cards','rating','position','name','league','club','nationality','header','squad','slots','slot','objective','objectives','sbc','dcp','gallery','requirements','requirement','title','progress','balance','coins'])
 const tokens=(el:Element)=>Array.from(el.classList).filter(c=>words.has(c.toLowerCase())).slice(0,3)
 const selector=(el:Element)=>tag(el)+tokens(el).map(t=>'.'+t).join('')
 const candidates=Array.from(document.querySelectorAll('main > section,main > div,section[role], [role=list],[role=grid],[role=table],header')).filter(el=>!el.closest(prohibited)&&visible(el)).slice(0,12)
 const roots=candidates.filter(el=>!candidates.some(other=>other!==el&&other.contains(el)))
 const regions=roots.map(root=>{
  const queue:{el:Element;parent:number|null;depth:number}[]=[{el:root,parent:null,depth:0}]
  const nodes:{parent:number|null;tag:string;role:string|null;selector:string;field_hints:string[];children:number}[]=[]
  let visited=0,excluded=0,images=0,canvas=0
  while(queue.length&&visited<600&&nodes.length<120){
   const {el,parent,depth}=queue.shift()!;visited++
   if(el.matches(prohibited)||!visible(el)){excluded++;if(el.tagName==='IMG')images++;if(el.tagName==='CANVAS')canvas++;continue}
   const role=el.getAttribute('role'),index=nodes.length
   nodes.push({parent,tag:tag(el),role:role&&roles.has(role)?role:null,selector:selector(el),field_hints:tokens(el).map(t=>t.toLowerCase()),children:Math.min(el.children.length,301)})
   if(depth<5)for(const child of Array.from(el.children).slice(0,301))queue.push({el:child,parent:index,depth:depth+1})
  }
  const repeated=Math.max(0,...nodes.map(n=>n.children))
  return {selector:selector(root),nodes,repeated_children:repeated,visited,excluded,images,canvas,truncated:queue.length>0,
   loading:root.getAttribute('aria-busy')==='true'||!!root.querySelector('[aria-busy=true],[role=progressbar]')}
 })
 return {...base,code:regions.some(r=>r.loading)?'loading':'profile_required',regions,
  limits:{regions:12,nodes_per_region:120,visited_per_region:600},coverage:'visible_candidate_regions_only',global_complete:false,
  language:/^(es|en)(-[a-zA-Z]{2})?$/.test(document.documentElement.lang)?document.documentElement.lang:'unknown'}
}
