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
  await expect(page.getByRole('button',{name:'Conectar'})).toBeVisible()
  await expect(page.getByRole('button',{name:'Nueva lectura'})).toBeDisabled()
})
