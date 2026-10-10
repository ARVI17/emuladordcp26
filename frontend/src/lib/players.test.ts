import {describe,expect,it} from 'vitest'
import {emptyPlayer,playerSchema} from './players'
import {player} from '../test/helpers'
describe('datos de cartas revisados',()=>{
  it('no inventa la media, la liga o la puntuación de una carta nueva',()=>{
    const draft=emptyPlayer('FC27')
    expect(draft.rating).toBe('');expect(draft.league).toBe('');expect(draft.gallery_score).toBeNull()
    expect(playerSchema.safeParse(draft).success).toBe(false)
    expect(draft.card_type).toBe('Oro')
  })
  it('rechaza una puntuación fraccionaria y un cuarto PlayStyle+ de FC 27',()=>{
    expect(playerSchema.safeParse(player({gallery_score:1.5})).success).toBe(false)
    expect(playerSchema.safeParse(player({playstyles_plus:['A','B','C','D']})).success).toBe(false)
    expect(playerSchema.safeParse(player({gallery_score:0,playstyles_plus:['A','B','C']})).success).toBe(true)
  })
})
