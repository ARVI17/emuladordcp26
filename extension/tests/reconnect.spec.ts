import {chromium,expect,test,type Page} from '@playwright/test'
import http from 'node:http'
import path from 'node:path'

function discover(page:Page) {
 return page.evaluate(()=>new Promise<number>(resolve=>{
  const nonce=crypto.randomUUID()
  let replies=0
  const receive=(event:MessageEvent)=>{
   if(event.source===window&&event.origin===location.origin&&event.data?.nonce===nonce&&event.data?.kind==='hello')replies++
  }
  window.addEventListener('message',receive)
  window.postMessage({channel:'club-lab-auto-v1',kind:'discover',nonce},location.origin)
  setTimeout(()=>{window.removeEventListener('message',receive);resolve(replies)},250)
 }))
}

test('volver a una pestaña abierta de Club Lab recupera el lector sin recargarla',async()=>{
 const server=http.createServer((_,res)=>res.end('<title>Mi cuenta · Club Lab FC27</title><h1>Club de prueba</h1>'))
 await new Promise<void>(done=>server.listen(0,'127.0.0.1',done))
 const base='http://127.0.0.1:'+(server.address() as import('node:net').AddressInfo).port
 const extension=path.resolve('.output/chrome-mv3')
 const context=await chromium.launchPersistentContext('',{channel:'chromium',args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]})
 try{
  const page=await context.newPage()
  await page.goto(base)
  await expect.poll(()=>discover(page)).toBe(1)
  const other=await context.newPage()
  await other.bringToFront()
  const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker')
  // Deliberately disconnect only our own bridge in this disposable Chromium.
  await worker.evaluate(async url=>{
   const [tab]=await chrome.tabs.query({url:url+'/'})
   await chrome.scripting.executeScript({target:{tabId:tab!.id!},func:()=>{
    (globalThis as typeof globalThis & {disconnectClubLabBridge?:()=>void}).disconnectClubLabBridge?.()
   }})
  },base)
  expect(await discover(page)).toBe(0)
  const before=await page.evaluate(()=>performance.timeOrigin)
  await page.bringToFront()
  await expect.poll(()=>discover(page),{timeout:20000}).toBe(1)
  expect(await page.evaluate(()=>performance.timeOrigin)).toBe(before)
 }finally{
  await context.close()
  await new Promise<void>(done=>server.close(()=>done()))
 }
})
