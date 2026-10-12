import { test, expect } from '@playwright/test'
test('la navegación móvil y el panel principal son visibles',async({page})=>{
  await page.goto('/')
  await expect(page.getByRole('heading',{name:'FC 26 Club Lab'})).toBeVisible()
  await expect(page.getByRole('navigation',{name:'Navegación principal'})).toBeVisible()
  await expect(page.getByRole('button',{name:/Club/})).toBeVisible()
})

test('el emulador muestra estado seguro y conserva la entrega manual',async({page})=>{
  await page.goto('/')
  await page.getByRole('button',{name:/Emulador/}).click()
  await expect(page.getByRole('heading',{name:'Conexión con Companion'})).toBeVisible()
  await expect(page.getByRole('heading',{name:'Sincronizar mi club real'})).toBeVisible()
  await expect(page.getByText(/no realiza compras, ventas, inicio de sesión ni la pulsación final/i)).toBeVisible()
  await expect(page.getByRole('button',{name:/Conectar|ADB ya conectado/})).toBeVisible()
  await expect(page.getByRole('button',{name:'Nueva lectura'})).toBeDisabled()
})

test('las lecturas grandes cargan solo veinte cartas y no se sondean solas',async({page})=>{
  let summaryRequests=0
  const candidates=Array.from({length:20},(_,index)=>({candidate_id:index+1,name:`Jugador ${index+1}`,rating:80,position:'MC',source_page:1,confidence:{name:.99,rating:.99,position:.99}}))
  await page.route('**/api/emulator/scans',async route=>{
    summaryRequests+=1
    await route.fulfill({json:[{id:7,status:'review',device_serial:'emulator-5554',screen_size:[1080,2400],captured_pages:50,candidate_count:1000,imported_count:0,last_error:null,confirmation_phrase:'IMPORTAR 7',archive_demo_phrase:'REEMPLAZAR DEMO 7',images_saved:false,requires_review:true,created_at:'2026-08-08T00:00:00Z',imported_at:null}]})
  })
  await page.route('**/api/emulator/scans/7/candidates?*',async route=>{
    const offset=Number(new URL(route.request().url()).searchParams.get('offset')||0)
    await route.fulfill({json:{scan_id:7,items:candidates.map(item=>({...item,candidate_id:item.candidate_id+offset})),total:1000,offset,limit:20}})
  })
  await page.goto('/')
  await page.getByRole('button',{name:/Emulador/}).click()
  await expect(page.getByText('50 páginas · 1000 candidatos pendientes')).toBeVisible()
  await expect(page.locator('.scan-candidate')).toHaveCount(20)
  await page.waitForTimeout(5500)
  expect(summaryRequests).toBe(1)
  await page.getByRole('button',{name:'Siguiente',exact:true}).click()
  await expect(page.getByText('Página 2 de 50')).toBeVisible()
  await expect(page.locator('.scan-candidate')).toHaveCount(20)
})

test('Companion se actualiza solamente cuando el usuario pulsa el botón',async({page})=>{
  let observations=0
  const candidates=Array.from({length:20},(_,index)=>({candidate_id:index+1,name:`Visible ${index+1}`,rating:82,position:'MC',source_page:1,confidence:{name:.99,rating:.99,position:.99}}))
  const scan={id:8,status:'review',device_serial:'emulator-5554',screen_size:[1080,2400],captured_pages:1,candidate_count:20,imported_count:0,last_error:null,confirmation_phrase:'IMPORTAR 8',archive_demo_phrase:'REEMPLAZAR DEMO 8',images_saved:false,requires_review:true,created_at:'2026-08-08T00:00:00Z',imported_at:null}
  await page.route('**/api/emulator/status',route=>route.fulfill({json:{enabled:true,available:true,devices:[{serial:'emulator-5554',state:'device',details:'test'}],config:{serial:'emulator-5554',address:'host.docker.internal:5555',calibration:null},message:null}}))
  await page.route('**/api/emulator/scans',route=>route.fulfill({json:[scan]}))
  await page.route('**/api/emulator/scans/8/candidates?*',route=>route.fulfill({json:{scan_id:8,items:candidates,total:20,offset:0,limit:20}}))
  await page.route('**/api/emulator/scans/8/observe',async route=>{
    observations+=1
    await route.fulfill({json:{scan:{...scan,captured_pages:2,candidate_count:40},detected:20,duplicate_capture:false,visible_inventory:true,source:'accessibility',message:'Se detectaron 20 cartas nuevas para revisar'}})
  })
  await page.goto('/')
  await page.getByRole('button',{name:/Emulador/}).click()
  await expect(page.getByRole('button',{name:'Actualizar desde Companion'})).toBeEnabled()
  await page.waitForTimeout(3500)
  expect(observations).toBe(0)
  await page.getByRole('button',{name:'Actualizar desde Companion'}).click()
  await expect(page.getByText('Se detectaron 20 cartas nuevas para revisar')).toBeVisible()
  await expect(page.getByText('2 páginas · 40 candidatos pendientes')).toBeVisible()
  expect(observations).toBe(1)
})

test('la carga completa reúne todos los lotes y exige confirmación',async({page})=>{
  let imports=0
  const scan={id:8,status:'review',device_serial:'emulator-5554',screen_size:[1080,2400],captured_pages:12,candidate_count:226,imported_count:0,last_error:null,confirmation_phrase:'IMPORTAR 8',archive_demo_phrase:'REEMPLAZAR DEMO 8',images_saved:false,requires_review:true,created_at:'2026-08-08T00:00:00Z',imported_at:null}
  await page.route('**/api/emulator/status',route=>route.fulfill({json:{enabled:true,available:true,devices:[{serial:'emulator-5554',state:'device',details:'test'}],config:{serial:'emulator-5554',address:'host.docker.internal:5555',calibration:null},message:null}}))
  await page.route('**/api/emulator/scans',route=>route.fulfill({json:[scan,{...scan,id:7,captured_pages:50,candidate_count:1000}]}))
  await page.route('**/api/emulator/scans/8/candidates?*',route=>route.fulfill({json:{scan_id:8,items:[],total:226,offset:0,limit:20}}))
  await page.route('**/api/emulator/scans/bulk-preview',route=>route.fulfill({json:{scan_ids:[7,8],sessions:2,detected:1226,unique_new:1164,duplicates:62,already_registered_or_used:0,incomplete:0,confirmation_phrase:'IMPORTAR TODO EL CLUB',requires_review:true,fields_from_companion:['name','rating','position']}}))
  await page.route('**/api/emulator/scans/bulk-import',async route=>{imports+=1;await route.fulfill({json:{imported:1164,player_ids:[],duplicates_skipped:62,registered_or_used_skipped:0,remaining_review:0,sessions_processed:2}})})
  await page.goto('/')
  await page.getByRole('button',{name:/Emulador/}).click()
  await expect(page.getByRole('heading',{name:'1164 cartas únicas nuevas'})).toBeVisible()
  const confirmation=page.getByPlaceholder('IMPORTAR TODO EL CLUB')
  const submit=page.getByRole('button',{name:'Cargar todo el club sin duplicados'})
  await expect(submit).toBeDisabled()
  await confirmation.fill('IMPORTAR TODO EL CLUB')
  await submit.click()
  await expect(page.getByText(/Carga terminada: 1164 cartas nuevas/)).toBeVisible()
  expect(imports).toBe(1)
})

test('el asistente DCP pregunta, calcula y exige confirmación antes de crear un plan',async({page})=>{
  let analyzePayload:{segment_id:number;preserve_starters:boolean}|null=null
  let planRequests=0
  const players=Array.from({length:11},(_,index)=>({id:index+1,name:`Carta ${index+1}`,rating:84,position:'MC',league:'Liga',club:'Club',nationality:'Colombia',card_type:'Oro',rare:true,special:false,tradable:false,price:0,chemistry:2,protected:false,starter:false,squad_role:'club',usefulness:0,duplicate_untradeable:index<2,deleted:false,created_at:'2026-08-08T00:00:00Z'}))
  await page.route('**/api/challenges',route=>route.fulfill({json:[{id:4,name:'DCP guiado',description:'',reward:'',completed:false,expires_at:null,segments:[{id:10,name:'Plantilla 84',requirements:{squad_size:11,min_rating:84},completed:false}]}]}))
  await page.route('**/api/ai/dcp/analyze',async route=>{
    analyzePayload=route.request().postDataJSON()
    await route.fulfill({json:{challenge:{id:4,name:'DCP guiado'},segment:{id:10,name:'Plantilla 84',requirements:{squad_size:11,min_rating:84},completed:false},solutions:[{player_ids:players.map(player=>player.id),players,total_cost:1200,rating:84,chemistry:22,valid:true,violations:[],uses_protected:false,duplicate_count:2}],inventory_summary:{available:100,duplicates:8,protected:11,starters_excluded:11},policy:{preserve_starters:true,protected_players_allowed:false},assistant:{summary:'Encontré 1 propuesta válida para DCP guiado · Plantilla 84.',question:'¿Cuál propuesta quieres revisar?',next_action:'review_solution'},alternative_with_starters:false,plan_confirmation_phrase:'CREAR PLAN 10',simulation:true,writes_performed:false,final_submission_automated:false}})
  })
  await page.route('**/api/emulator/plans',async route=>{
    planRequests+=1
    await route.fulfill({json:{id:27,name:'DCP guiado',plan_type:'dcp',status:'draft',device_serial:null,segment_id:10,player_ids:players.map(player=>player.id),solution_snapshot:{players:[],validated:true,delivery_requires_manual_confirmation:true},steps:[],progress_step:0,last_error:null,confirmation_phrase:null,final_submission_automated:false,created_at:'2026-08-08T00:00:00Z'}})
  })
  await page.goto('/')
  await page.getByRole('button',{name:/IA/}).click()
  await expect(page.getByRole('heading',{name:'Asistente DCP local'})).toBeVisible()
  await expect(page.getByText('1. ¿Qué DCP quieres calcular?')).toBeVisible()
  await page.getByRole('button',{name:'Analizar mi club'}).click()
  await expect(page.getByText(/Encontré 1 propuesta válida/)).toBeVisible()
  await expect(page.locator('.solution-players span')).toHaveCount(11)
  expect(analyzePayload).toMatchObject({segment_id:10,preserve_starters:true})
  const create=page.getByRole('button',{name:'Crear plan revisable'})
  await expect(create).toBeDisabled()
  expect(planRequests).toBe(0)
  await page.getByPlaceholder('CREAR PLAN 10').fill('CREAR PLAN 10')
  await create.click()
  await expect(page.getByText(/Plan asistido #27 creado/)).toBeVisible()
  expect(planRequests).toBe(1)
  await expect(page.getByRole('button',{name:/entrega/i})).toHaveCount(0)
})
