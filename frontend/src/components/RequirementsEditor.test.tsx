import {useState} from 'react'
import {fireEvent,screen} from '@testing-library/react'
import {expect,it} from 'vitest'
import {RequirementsEditor,RequirementTags} from './RequirementsEditor'
import {renderClub} from '../test/helpers'
function Editor(){const [value,setValue]=useState<Record<string,unknown>>({kind:'traditional',squad_size:11,max_leagues:3,min_clubs:2,max_clubs:2});return <form><RequirementsEditor value={value} onChange={setValue}/><RequirementTags requirements={value}/></form>}
it('conserva máximos y cantidades exactas y permite corregir los valores detectados',()=>{
  renderClub(<Editor/>)
  expect(screen.getByText('Ligas máximas: 3')).toBeInTheDocument()
  expect(screen.getByText('Clubes mínimos: 2')).toBeInTheDocument()
  expect(screen.getByText('Clubes máximos: 2')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Ligas, clubes, nacionalidades y otros requisitos'))
  fireEvent.change(screen.getByLabelText('Ligas máximas'),{target:{value:'4'}})
  expect(screen.getByText('Ligas máximas: 4')).toBeInTheDocument()
})
it('aplica JSON válido y bloquea el envío si el JSON es inválido',()=>{
  renderClub(<Editor/>)
  fireEvent.click(screen.getByText('Ligas, clubes, nacionalidades y otros requisitos'))
  const input=screen.getByLabelText('Requisitos completos (JSON)') as HTMLTextAreaElement
  fireEvent.change(input,{target:{value:'{"kind":"traditional","squad_size":11,"max_leagues":1}'}})
  expect(screen.getByText('Ligas máximas: 1')).toBeInTheDocument()
  expect(input.checkValidity()).toBe(true)
  fireEvent.change(input,{target:{value:'{"max_leagues":'}})
  expect(input.checkValidity()).toBe(false)
  expect(screen.getByRole('alert')).toBeInTheDocument()
})
