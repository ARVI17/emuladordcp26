// Self-contained function serialized by chrome.scripting. Never reads storage,
// input values, URLs from elements, HTML, cookies or event listeners; never clicks.
export function inspectRegion(privacyPattern:string) {
  const sensitive=new RegExp(privacyPattern,'i')
  const skip='form,input,textarea,select,option,script,style,noscript,iframe,[contenteditable]:not([contenteditable="false"]),[hidden],[aria-hidden="true"]'
  const visible=(el:Element)=>Array.from(el.getClientRects()).some(r=>r.width>0&&r.height>0)&&el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})&&!el.closest('[hidden],[aria-hidden="true"]')
  if(Array.from(document.querySelectorAll('input[type="password"],input[type="email"],input[autocomplete="one-time-code"],input[autocomplete="username"],input[autocomplete^="cc-"],[role="dialog"],[role="alert"],h1,h2,[role="heading"]')).some(el=>visible(el)&&(el.tagName==='INPUT'||sensitive.test((el.textContent||'').slice(0,1000)))))return {blocked:'Acceso, verificación, pago o alerta sensible: reconocimiento detenido.'}
  const selection=window.getSelection()
  if(!selection?.rangeCount||selection.isCollapsed)return {blocked:'Selecciona un encabezado, una carta o un requisito visible y vuelve a reconocer.'}
  const root=selection.getRangeAt(0).commonAncestorContainer
  const selected=root instanceof Element?root:root.parentElement
  if(!selected||selected.closest(skip)||!visible(selected))return {blocked:'La selección no es una región permitida.'}
  let element:Element=selected
  // At most two enclosing containers. Never traverse the entire document/body.
  for(let n=0;n<2;n++){
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
  const candidate=(el:Element)=>el.tagName.toLowerCase()+classes(el).map(c=>'.'+CSS.escape(c)).join('')
  const allowedRoles=new Set(['list','listitem','grid','gridcell','row','table','columnheader','heading','button','link','navigation','status','progressbar','tab','tabpanel','img'])
  const nodes:{parent:number|null;tag:string;selector:string;matches:number;role:string|null;label:string|null;text:string|null;medium:string;busy:boolean;declared_rows:number|null}[]=[]
  const pending:{el:Element;parent:number|null;depth:number}[]=[{el:element,parent:null,depth:0}]
  let visited=0,cut=false,bytes=0
  while(pending.length&&visited<4000&&nodes.length<1200){
    const item=pending.shift()!;visited++
    const el=item.el
    if(el.matches(skip)){omitted.excluded_subtrees++;continue}
    if(!visible(el)){omitted.hidden_subtrees++;continue}
    const role=el.getAttribute('role'),sel=candidate(el)
    const id=nodes.length
    const count=el.getAttribute('aria-rowcount')
    if(el.tagName==='IMG')omitted.images++
    if(el.tagName==='CANVAS')omitted.canvas++
    if(el.shadowRoot||el.localName.includes('-'))omitted.shadow_roots++
    // Mixed text is not silently concatenated across controls or private children.
    if(el.children.length&&Array.from(el.childNodes).some(n=>n.nodeType===Node.TEXT_NODE&&n.textContent?.trim()))omitted.mixed_text_nodes++
    nodes.push({parent:item.parent,tag:el.tagName.toLowerCase(),selector:sel,
      matches:element.querySelectorAll(sel).length+(element.matches(sel)?1:0),
      role:role&&allowedRoles.has(role)?role:null,label:clean(el.getAttribute('aria-label')),
      text:el.children.length===0&&!['IMG','CANVAS'].includes(el.tagName)?clean(el.textContent):null,
      medium:el.tagName==='CANVAS'?'canvas':el.tagName==='IMG'?'image':el.shadowRoot?'open_shadow_unread':el.localName.includes('-')?'custom_element_shadow_unknown':'dom',
      busy:el.getAttribute('aria-busy')==='true',declared_rows:count&&/^\d{1,6}$/.test(count)?Number(count):null})
    bytes+=new TextEncoder().encode(JSON.stringify(nodes[nodes.length-1])).length
    if(bytes>480000){nodes.pop();cut=true;break}
    if(item.depth<7){
      for(const child of Array.from(el.children).slice(0,300))pending.push({el:child,parent:id,depth:item.depth+1})
      if(el.children.length>300)cut=true
    }else if(el.children.length)cut=true
  }
  const nav=nodes.filter(n=>['button','a'].includes(n.tag)||['button','link','tab'].includes(n.role||''))
    .slice(0,12).map(n=>({selector:n.selector,label:n.label||n.text,matches:n.matches,approved:false,context:'selected_region'}))
  return {nodes,root_selector:candidate(element),navigation_candidates:nav,
    coverage:{kind:'selected_region_only',truncated:cut||pending.length>0,visited_nodes:visited,visible_nodes:nodes.length,
      loading:nodes.some(n=>n.busy||n.role==='progressbar'),omitted,
      partial:cut||pending.length>0||Object.values(omitted).some(n=>n>0),
      virtualized:null,filters:null,page:null,terminal_observed:false,global_complete:false},
    language:/^[a-z]{2,3}(?:-[a-z0-9]{2,8}){0,2}$/i.test(document.documentElement.lang)&&document.documentElement.lang.length<=16?document.documentElement.lang:'unknown',
    limitations:['Selectores candidatos: no acreditan identidad ni seguridad de una acción.','Imágenes, canvas y shadow DOM no se extraen.','Revisa posibles datos personales; el filtro no es infalible.']}
}
