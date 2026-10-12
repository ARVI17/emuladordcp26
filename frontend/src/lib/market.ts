import {observedDate} from './i18n'
export const marketKindLabels:Record<string,string>={listing:'Anuncio',bid:'Puja',observed_sale:'Venta observada',allowed_range:'Rango permitido'}
export const observedTime=(value:string)=>observedDate(value)
