export const sections={
  inicio:{label:'Inicio',icon:'⌂',path:'inicio'},
  plantillas:{label:'Plantillas',icon:'▦',path:'plantillas/principal'},
  recomendadas:{label:'Recomendadas',icon:'▦',path:'plantillas/recomendadas'},
  'plantillas-objetivos':{label:'Para objetivos',icon:'◎',path:'plantillas/objetivos'},
  dcp:{label:'DCP',icon:'◇',path:'dcp'},
  evoluciones:{label:'Evoluciones',icon:'↗',path:'evoluciones'},
  mercado:{label:'Transferibles',icon:'↔',path:'transferibles'},
  tienda:{label:'Tienda',icon:'▱',path:'tienda'},
  club:{label:'Mi club',icon:'♙',path:'club'},
  galeria:{label:'Galería',icon:'▧',path:'galeria'},
  objetivos:{label:'Centro FC',icon:'◎',path:'centro-fc'},
  conexiones:{label:'Mi cuenta',icon:'◉',path:'cuenta'},
  configuracion:{label:'Ajustes',icon:'⚙',path:'ajustes'},
  analisis:{label:'Análisis',icon:'◉',path:'asistente/analisis'},
  fichajes:{label:'Fichajes',icon:'↔',path:'asistente/fichajes'},
  planes:{label:'Planes',icon:'✓',path:'asistente/planes'},
  practica:{label:'Práctica',icon:'⊕',path:'asistente/practica'},
  referencias:{label:'Referencias',icon:'≡',path:'asistente/referencias'},
  ia:{label:'IA local',icon:'✦',path:'asistente/ia'},
  novedades:{label:'Novedades',icon:'✧',path:'asistente/novedades'},
  duplicados:{label:'Duplicados',icon:'⧉',path:'asistente/duplicados'},
  emulador:{label:'Emulador',icon:'▣',path:'asistente/emulador'},
} as const
export type Page=keyof typeof sections
export const primaryPages:Page[]=['inicio','plantillas','dcp','evoluciones','mercado','tienda','club','galeria','objetivos']
export const assistantPages:Page[]=['analisis','fichajes','planes','practica','referencias','ia','novedades','duplicados','emulador']
export function currentPage(hash=window.location.hash):Page{
  const path=hash.replace(/^#\/?/,'').split('?')[0]
  return (Object.keys(sections) as Page[]).find(id=>sections[id].path===path)|| (path in sections?path as Page:'inicio')
}
export function navigate(page:Page){window.location.hash='/'+sections[page].path}
