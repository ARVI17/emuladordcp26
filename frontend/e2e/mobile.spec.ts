import {test,expect,openLocal,go} from './fixtures'

test('el panel y la navegación de FC 27 caben en una pantalla móvil',async({page})=>{
  await openLocal(page)
  await expect(page.getByRole('heading',{name:'Club Lab FC27'})).toBeVisible()
  await expect(page.getByLabel('Temporada activa')).toHaveCount(0)
  await go(page,'Mi club')
  await expect(page.getByRole('heading',{name:'Mi club',exact:true})).toBeVisible()
  const widths=await page.evaluate(()=>({viewport:window.innerWidth,document:document.documentElement.scrollWidth}))
  expect(widths.document).toBeLessThanOrEqual(widths.viewport)
})

test('Companion conserva la revisión y la entrega manual cuando ADB no está conectado',async({page})=>{
  await page.route('**/emulator/status',route=>route.fulfill({json:{enabled:false,available:false,devices:[],config:{},message:'ADB desactivado para esta prueba'}}))
  await openLocal(page)
  await go(page,'Emulador')
  await expect(page.getByRole('heading',{name:'Conexión con Companion'})).toBeVisible()
  await expect(page.getByRole('heading',{name:'Leer mi inventario'})).toBeVisible()
  await expect(page.getByText(/no realiza compras, ventas, inicio de sesión ni la pulsación final/i)).toBeVisible()
  await expect(page.getByRole('button',{name:'Conectar',exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'Nueva lectura'})).toBeDisabled()
})

// Este recorrido crea datos locales: CI debe proporcionar una base desechable.
test('FC27: analiza un club, guarda un once completo y registra su Galería',async({page,request},testInfo)=>{
  test.skip(process.env.PLAYWRIGHT_DISPOSABLE_DB!=='1','Configura PLAYWRIGHT_DISPOSABLE_DB=1 con una base exclusiva de pruebas.')
  test.setTimeout(60000)
  const previous=await request.get('/api/profile')
  expect(previous.ok()).toBeTruthy()
  const original=await previous.json()
  const edition=await request.patch('/api/profile',{data:{game_version:'FC27'}})
  expect(edition.ok()).toBeTruthy()
  const run=`E2E ${Date.now()}`
  const formationResponse=await request.get('/api/squads/formations')
  expect(formationResponse.ok()).toBeTruthy()
  const definitions=await formationResponse.json()
  const positions:string[]=definitions.items.find((item:{id:string})=>item.id==='4-3-3').slots.map((slot:{position:string})=>slot.position)
  expect(positions).toHaveLength(11)
  const names=['Alba','Bruno','Carlos','Diego','Elena','Fabio','Gabriel','Hugo','Irene','Jorge','Karla']
  const created:number[]=[]
  let workflowFailed=false
  try{
    const history=await request.post('/api/gallery/record-inventory',{data:{}})
    expect(history.ok()).toBeTruthy()
    for(const [index,position] of positions.entries()){
      const response=await request.post('/api/players',{data:{game_version:'FC27',name:`${run} ${names[index]}`,rating:95,position,league:'Liga de prueba',club:'Club E2E',nationality:'Colombia',card_type:'Oro',card_id:`${run}-${index}`,price:100,chemistry:3,data_reviewed:true,data_source:'e2e',gallery_score:100,attributes:position==='POR'?{diving:95,handling:95,kicking:95,reflexes:95,speed:95,positioning:95}:{pace:95,shooting:95,passing:95,dribbling:95,defending:95,physical:95}}})
      expect(response.ok(),await response.text()).toBeTruthy()
      created.push((await response.json()).id)
    }
    await openLocal(page)
    await expect(page.getByRole('heading',{name:'Club Lab FC27'})).toBeVisible()
    await go(page,'Análisis')
    await expect(page.getByRole('heading',{name:'Análisis de mi club'})).toBeVisible()
    await page.getByRole('button',{name:/^Armar un /}).click()
    await expect(page.getByRole('heading',{name:'Armar mi equipo'})).toBeVisible()
    await test.step('Seleccionar la formación y proponer un once completo',async()=>{
      const formation=page.getByRole('combobox',{name:'Formación',exact:true})
      await expect(formation).toBeVisible()
      await formation.selectOption('4-3-3')
      await expect(formation).toHaveValue('4-3-3')
      await page.getByRole('button',{name:'Proponer once y suplentes'}).click()
      await expect(page.getByRole('heading',{name:'Tu once propuesto'})).toBeVisible()
      await expect(page.locator('.pitch-player')).toHaveCount(11)
    await page.screenshot({path:testInfo.outputPath('squad.png'),fullPage:true})
    })
    const squadName=`Plantilla ${run}`
    await page.getByLabel('Nombre de la plantilla').fill(squadName)
    const saved=page.waitForResponse(response=>response.url().endsWith('/api/squads')&&response.request().method()==='POST')
    await page.getByRole('button',{name:'Guardar plantilla',exact:true}).click()
    expect((await saved).ok()).toBeTruthy()
    await expect(page.getByRole('heading',{name:squadName,exact:true})).toBeVisible()
    await go(page,'Galería')
    await expect(page.getByRole('heading',{name:'Galería local'})).toBeVisible()
    const registered=page.waitForResponse(response=>response.url().endsWith('/api/gallery/record-inventory')&&response.request().method()==='POST')
    await page.getByRole('button',{name:'Registrar mi colección'}).click()
    expect((await registered).ok()).toBeTruthy()
    await expect(page.getByRole('heading',{name:`${run} ${names[0]}`,exact:true})).toBeVisible()
    await page.screenshot({path:testInfo.outputPath('gallery.png'),fullPage:true})
    const widths=await page.evaluate(()=>({viewport:window.innerWidth,document:document.documentElement.scrollWidth}))
    expect(widths.document).toBeLessThanOrEqual(widths.viewport)
    expect(created).toHaveLength(11)
  }catch(error){
    workflowFailed=true
    throw error
  }finally{
    // Conservar el fallo original si Playwright ya cerró el contexto por timeout.
    // La plantilla y su Galería forman parte de la base de pruebas desechable.
    try{
      const restored=await request.patch('/api/profile',{data:{game_version:original.game_version}})
      expect(restored.ok()).toBeTruthy()
    }catch(error){
      if(!workflowFailed)throw error
    }
  }
})
