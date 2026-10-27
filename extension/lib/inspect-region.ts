// Self-contained function serialized by chrome.scripting. Never reads storage,
// input values, URLs from elements, HTML, cookies or event listeners; never clicks.
export function inspectRegion(privacyPattern:string, rootSelector?:string) {
  const sensitive=new RegExp(privacyPattern,'i')
  const skip='form,input,textarea,select,option,script,style,noscript,iframe,[contenteditable]:not([contenteditable="false"]),[hidden],[aria-hidden="true"]'
  const visible=(el:Element)=>Array.from(el.getClientRects()).some(r=>r.width>0&&r.height>0)&&el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})&&!el.closest('[hidden],[aria-hidden="true"]')
  if(Array.from(document.querySelectorAll('input[type="password"],input[type="email"],input[autocomplete="one-time-code"],input[autocomplete="username"],input[autocomplete^="cc-"],[role="dialog"],[role="alert"],h1,h2,[role="heading"]')).some(el=>visible(el)&&(el.tagName==='INPUT'||sensitive.test((el.textContent||'').slice(0,1000)))))return {blocked:'Acceso, verificación, pago o alerta sensible: reconocimiento detenido.'}
  const sampleHost=['localhost','127.0.0.1'].includes(location.hostname)&&location.pathname==='/reader-sample.html'
  if(rootSelector&&(!sampleHost||rootSelector!=='[data-club-lab-sample="1"]'))return {blocked:'Región automática no autorizada.'}
  const selection=window.getSelection()
  if(!rootSelector&&(!selection?.rangeCount||selection.isCollapsed))return {blocked:'Selecciona un encabezado, una carta o un requisito visible y vuelve a reconocer.'}
  const roots=rootSelector?Array.from(document.querySelectorAll(rootSelector)):[]
  if(rootSelector&&roots.length!==1)return {blocked:'La muestra requiere una única región declarada.'}
  const root=rootSelector?roots[0]!:selection!.getRangeAt(0).commonAncestorContainer
  const selected=root instanceof Element?root:root.parentElement
  if(!selected||selected.closest(skip)||!visible(selected))return {blocked:'La selección no es una región permitida.'}
  let element:Element=selected
  // At most two enclosing containers. Never traverse the entire document/body.
  for(let n=0;!rootSelector&&n<2;n++){
    const parent:Element|null=element.parentElement
    if(!parent||['BODY','HTML','MAIN'].includes(parent.tagName)||parent.matches(skip))break
    if(element.matches('section,article,[role="list"],[role="grid"],[role="table"]'))break
    element=parent
  }
  if(['BODY','HTML'].includes(element.tagName))return {blocked:'Selecciona una región más pequeña; no se inspecciona la página completa.'}
  const omitted={sensitive_fields:0,long_fields:0,excluded_subtrees:0,hidden_subtrees:0,images:0,canvas:0,shadow_roots:0,mixed_text_nodes:0}
  const clean=(v:string|null)=>{
    const t=(v||'').trim().replace(/\s+/g,' ')
    if(!t)return null
    if(sensitive.test(t)){omitted.sensitive_fields++;return null}
    if(t.length>5000){omitted.long_fields++;return null}
    return t
  }
  const classes=(el:Element)=>Array.from(el.classList).filter(c=>/^[a-z][a-z_-]{1,40}$/i.test(c)&&!sensitive.test(c)).slice(0,3)
  const candidate=(el:Element)=>{
    const field=el.getAttribute('data-field')
    if(sampleHost&&field&&/^[a-z_]{1,30}$/.test(field))return el.tagName.toLowerCase()+'[data-field="'+field+'"]'
    if(sampleHost&&el.hasAttribute('data-card'))return el.tagName.toLowerCase()+'[data-card]'
    return el.tagName.toLowerCase()+classes(el).map(c=>'.'+CSS.escape(c)).join('')
  }
  const allowedRoles=new Set(['list','listitem','grid','gridcell','row','table','columnheader','heading','button','link','navigation','status','progressbar','tab','tabpanel','img'])
  const nodes:{parent:number|null;tag:string;selector:string;matches:number;role:string|null;label:string|null;text:string|null;medium:string;busy:boolean;declared_rows:number|null}[]=[]
  const matchCounts=new Map<string,number>()
  const pending:{el:Element;parent:number|null;depth:number}[]=[{el:element,parent:null,depth:0}]
  let visited=0,cut=false,bytes=0
  while(pending.length&&visited<8000&&nodes.length<4000){
    const item=pending.shift()!;visited++
    const el=item.el
    if(el.matches(skip)){omitted.excluded_subtrees++;continue}
    if(!visible(el)){omitted.hidden_subtrees++;continue}
    const role=el.getAttribute('role'),sel=candidate(el)
    if(!matchCounts.has(sel))matchCounts.set(sel,element.querySelectorAll(sel).length+(element.matches(sel)?1:0))
    const id=nodes.length
    const count=el.getAttribute('aria-rowcount')
    if(el.tagName==='IMG')omitted.images++
    if(el.tagName==='CANVAS')omitted.canvas++
    if(el.shadowRoot||el.localName.includes('-'))omitted.shadow_roots++
    // Mixed text is not silently concatenated across controls or private children.
    if(el.children.length&&Array.from(el.childNodes).some(n=>n.nodeType===Node.TEXT_NODE&&n.textContent?.trim()))omitted.mixed_text_nodes++
    nodes.push({parent:item.parent,tag:el.tagName.toLowerCase(),selector:sel,
      matches:matchCounts.get(sel)!,
      role:role&&allowedRoles.has(role)?role:null,label:clean(el.getAttribute('aria-label')),
      text:el.children.length===0&&!['IMG','CANVAS'].includes(el.tagName)?clean(el.textContent):null,
      medium:el.tagName==='CANVAS'?'canvas':el.tagName==='IMG'?'image':el.shadowRoot?'open_shadow_unread':el.localName.includes('-')?'custom_element_shadow_unknown':'dom',
      busy:el.getAttribute('aria-busy')==='true',declared_rows:count&&/^\d{1,6}$/.test(count)?Number(count):null})
    bytes+=new TextEncoder().encode(JSON.stringify(nodes[nodes.length-1])).length
    if(bytes>950000){nodes.pop();cut=true;break}
    if(item.depth<7){
      for(const child of Array.from(el.children).slice(0,300))pending.push({el:child,parent:id,depth:item.depth+1})
      if(el.children.length>300)cut=true
    }else if(el.children.length)cut=true
  }
  const nav=nodes.filter(n=>['button','a'].includes(n.tag)||['button','link','tab'].includes(n.role||''))
    .slice(0,12).map(n=>({selector:n.selector,label:n.label||n.text,matches:n.matches,approved:false,context:'selected_region'}))
  const sample=sampleHost&&rootSelector?{view:clean(element.getAttribute('data-view')),source:clean(element.getAttribute('data-source')),edition:clean(element.getAttribute('data-edition')),page:clean(element.getAttribute('data-page')),filters:clean(element.getAttribute('data-filters')),context:clean(element.getAttribute('data-context-label')),virtualized:element.hasAttribute('data-virtualized')?element.getAttribute('data-virtualized')==='true':null}:undefined
  return {nodes,root_selector:candidate(element),navigation_candidates:nav,sample,
    coverage:{kind:'selected_region_only',truncated:cut||pending.length>0,visited_nodes:visited,visible_nodes:nodes.length,
      loading:nodes.some(n=>n.busy||n.role==='progressbar'),omitted,
      partial:cut||pending.length>0||Object.values(omitted).some(n=>n>0),
      virtualized:null,filters:null,page:null,terminal_observed:false,global_complete:false},
    language:/^[a-z]{2,3}(?:-[a-z0-9]{2,8}){0,2}$/i.test(document.documentElement.lang)&&document.documentElement.lang.length<=16?document.documentElement.lang:'unknown',
    limitations:['Selectores candidatos: no acreditan identidad ni seguridad de una acción.','Imágenes, canvas y shadow DOM no se extraen.','Revisa posibles datos personales; el filtro no es infalible.']}
}
