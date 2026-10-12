import {test as base,expect,type Page} from '@playwright/test'
export const test=base.extend({
 request:async({playwright,baseURL},use)=>{
  const bootstrap=await playwright.request.newContext({baseURL})
  const session=await (await bootstrap.post('/api/app/session')).json()
  const entered=await bootstrap.post('/api/app/entries',{headers:{'X-CSRF-Token':session.csrf_token},data:{nonce:crypto.randomUUID(),mode:'local'}})
  expect(entered.ok()).toBeTruthy()
  const entry=await entered.json()
  const request=await playwright.request.newContext({baseURL,storageState:await bootstrap.storageState(),extraHTTPHeaders:{'X-CSRF-Token':session.csrf_token,'X-App-Entry':String(entry.entry_id),'X-Catalog-Fixture':'1'}})
  await use(request)
  await request.dispose();await bootstrap.dispose()
 }
})
export {expect}
export async function openLocal(page:Page){
 await page.goto('/')
 await page.getByRole('button',{name:'Abrir registro local',exact:true}).click()
 await expect(page.getByText(/Registro local sin vincular · Simulaciones/)).toBeVisible()
}
