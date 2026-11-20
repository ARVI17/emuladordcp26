import {expect,test} from '@playwright/test'

test('un lector ya vinculado espera a Chrome y conserva la preferencia al reabrir',async({page})=>{
 test.skip(process.env.PLAYWRIGHT_DISPOSABLE_DB!=='1','Requiere el club sintético aislado.')
 await page.goto('/#/cuenta')
 await page.getByLabel('Nombre para un nuevo contexto de lectura').fill('Lector sintético '+Date.now())
 await page.getByRole('button',{name:'Iniciar lectura asistida en otro contexto'}).click()
 const pane=page.getByRole('region',{name:'Actualización automática del club'})
 const activate=pane.getByRole('button',{name:'Activar actualización automática y proteger mi equipo'})
 await expect(activate).toBeDisabled()
 const session=await (await page.request.post('/api/app/session')).json()
 const headers={'X-CSRF-Token':session.csrf_token,'X-App-Entry':String(session.entry_id)}
 const saved=await page.request.post('/api/browser-auto/settings',{headers,data:{
  extension_id:'a'.repeat(32),enabled:false,protect_main:true,confirmation:'ACTIVAR LECTURA LOCAL AUTOMATICA'}})
 expect(saved.ok()).toBe(true)
 await expect(activate).toBeEnabled()
 await activate.click()
 await expect(pane.getByRole('button',{name:'Desactivar actualización automática'})).toBeVisible()
 for(let pass=0;pass<2;pass++){
  await page.reload()
  await expect(pane.getByRole('status')).toContainText('Esperando al lector de Chrome',{timeout:15000})
  await expect(pane.getByText('Aún no hay una lectura automática guardada para este club.')).toBeVisible()
  await expect(pane.getByRole('button',{name:'Actualizar ahora'})).toBeDisabled()
 }
 const after=await (await page.request.post('/api/app/session')).json()
 const status=await (await page.request.get('/api/browser-auto/status',{headers:{
  'X-CSRF-Token':after.csrf_token,'X-App-Entry':String(after.entry_id)}})).json()
 expect(status).toMatchObject({enabled:true,protect_main:true,status:'ready',request_id:null,result:{}})
})
