export const marketKindLabels:Record<string,string>={listing:'Anuncio',bid:'Puja',observed_sale:'Venta observada',allowed_range:'Rango permitido'}
export const observedTime=(value:string)=>new Date(value).toLocaleString('es-CO')
