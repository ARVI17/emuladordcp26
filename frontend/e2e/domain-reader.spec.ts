import {test,expect} from '@playwright/test'
import {createHash,randomUUID} from 'node:crypto'

const canonical=(v:any):string=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v!==null&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v)
const hash=(v:any)=>createHash('sha256').update(canonical(v)).digest('hex')

test('revisión tipada muestra cero observado y requisitos pendientes sin crear cartas',async({page},info)=>{
 await page.goto('/#/cuenta')
 await page.getByLabel('Nombre para un nuevo contexto de lectura').fill('DOM UI sintético '+randomUUID())
 await page.getByRole('button',{name:'Iniciar lectura asistida en otro contexto'}).click()
 await expect(page.getByRole('heading',{name:'Lectura visual asistida',exact:true})).toBeVisible()
 const session=await (await page.request.post('/api/app/session')).json()
 const headers={'X-CSRF-Token':session.csrf_token,'X-App-Entry':String(session.entry_id)}
 const extension_id='a'.repeat(32)
 const pair=await (await page.request.post('/api/reader/pairings',{headers,data:{extension_id,confirmation:'EMPAREJAR LECTOR'}})).json()
 const transport={'X-Reader-Extension':extension_id,Host:'localhost:8090'}
 const claimed=await page.request.post('/api/reader/claim',{headers:transport,data:{pairing_id:pair.pairing_id,code:pair.code}})
 expect(claimed.ok(),await claimed.text()).toBe(true)
 const grant=await claimed.json()
 const send=async(payload:any)=>{
  const event:any={schema_version:2,reader_version:'bounded-region-2',event_id:randomUUID(),observation_id:randomUUID(),context_binding:grant.context_binding,stream_id:randomUUID(),document_ref:randomUUID(),sequence:1,observed_at:new Date().toISOString(),source_updated_at:null,source_kind:'synthetic_dom',
   profile:{profile_id:randomUUID(),revision:1,definition_hash:'a'.repeat(64),structure_hash:'b'.repeat(64),origin:'http://localhost:8090',route:'/reader-sample.html',language:'es',edition:'FC27',omissions:{}},
   scope:{page:payload.domain,filters:'',location:'unknown',visible_count:1,virtualized:null,global_complete:false},fragment_index:0,fragment_count:1,manifest:[hash(payload)],payload}
  event.payload_hash=hash(event)
  const response=await page.request.post('/api/reader/events',{headers:{...transport,Authorization:'Bearer '+grant.credential},data:event})
  expect(response.ok(),await response.text()).toBe(true)
 }
 await send({domain:'account',club_name:'Club sintético de interfaz',balance:0})
 await page.getByRole('button',{name:'Actualizar lotes recibidos'}).click()
 await page.getByRole('button',{name:'Cabecera · 1 registros'}).click()
 await expect(page.getByText('Club observado: Club sintético de interfaz · monedas: 0')).toBeVisible()
 await page.getByRole('heading',{name:'Observaciones por dominio'}).locator('..').screenshot({path:info.outputPath('domain-account.png')})
 const admit=page.getByRole('button',{name:'Admitir observación revisada'})
 await expect(admit).toBeDisabled()
 await page.getByLabel('Revisé esta región y corresponde al club de este contexto').check()
 await admit.click()
 await expect(page.getByText(/Lecturas guardadas:/)).toBeVisible()
 await send({domain:'dcp',records:[{title:'DCP sintético de interfaz',requirement_text:'Exactamente 11 jugadores. Media mínima 80.',progress_current:null,progress_target:null}]})
 await page.getByRole('button',{name:'Actualizar lotes recibidos'}).click()
 await page.getByRole('button',{name:'DCP · 1 registros'}).click()
 await expect(page.getByText('Exactamente 11 jugadores. Media mínima 80.',{exact:true})).toBeVisible()
 await page.getByLabel('Revisé esta región y corresponde al club de este contexto').check()
 await admit.click()
 await page.getByRole('button',{name:/Revisar todos los requisitos de la lectura/}).click()
 await expect(page.getByRole('heading',{name:'Revisar requisitos DCP'})).toBeVisible()
 expect((await (await page.request.get('/api/players',{headers})).json()).total).toBe(0)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.getByRole('heading',{name:'Observaciones por dominio'}).locator('..').screenshot({path:info.outputPath('domain-reader.png')})
})
