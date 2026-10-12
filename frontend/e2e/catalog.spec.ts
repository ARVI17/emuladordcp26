import {test,expect,openLocal} from './fixtures'

test('la cuarentena no se muestra como posesión y no hay selector histórico',async({page,request},info)=>{
 const name=`Sin evidencia ${Date.now()}`
 // Disable the isolated fixture witness: this request exercises production admission.
 const result=await request.post('/api/players',{headers:{'X-Catalog-Fixture':'0'},data:{game_version:'FC27',name,rating:99,position:'DC',league:'Manual',club:'Manual',nationality:'Manual',card_id:'variant-without-evidence',data_reviewed:true}})
 expect(result.status()).toBe(202)
 const list=await (await request.get('/api/players?search='+encodeURIComponent(name))).json()
 expect(list.total).toBe(0)
 expect((await request.get('/api/players?game_version=FC26')).status()).toBe(422)
 await openLocal(page)
 await page.getByRole('button',{name:'Mi club',exact:true}).click()
 await expect(page.getByLabel('Temporada activa')).toHaveCount(0)
 await page.getByText(/Cuarentena ·/).click()
 await expect(page.getByText(name,{exact:false})).toBeVisible()
 await expect(page.locator('.player-card').filter({hasText:name})).toHaveCount(0)
 await page.getByText('Catálogo FC27 documentado · no son mis cartas',{exact:true}).click()
 await expect(page.getByText(/No acreditan posesión/)).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await page.screenshot({path:info.outputPath('quarantine.png')})
})
