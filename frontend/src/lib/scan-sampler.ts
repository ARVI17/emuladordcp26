/** Two stable observations, one request in flight, no background recording. */
export class StableFrames {
  private previous?: Uint8ClampedArray
  private accepted?: Uint8ClampedArray
  private repeats = 0
  reset() { this.previous = this.accepted = undefined; this.repeats = 0 }
  inspect(pixels: Uint8ClampedArray): boolean {
    // Local tiles retain small name/rating changes that a global mean would hide.
    const distance = (other?: Uint8ClampedArray) => {
      if(!other||other.length!==pixels.length)return Infinity
      const tiles=new Float64Array(20*12),counts=new Uint16Array(20*12)
      for(let i=0;i<pixels.length;i+=4){
        const pixel=i/4,tile=Math.floor(Math.floor(pixel/160)/8)*20+Math.floor((pixel%160)/8)
        for(let c=0;c<3;c++){tiles[tile]+=Math.abs(pixels[i+c]-other[i+c]);counts[tile]++}
      }
      return Math.max(...tiles.map((sum,i)=>counts[i]?sum/counts[i]:0))
    }
    this.repeats = distance(this.previous) <= 1.5 ? this.repeats + 1 : 0
    this.previous = pixels.slice()
    if (this.repeats < 1 || distance(this.accepted) <= 2) return false
    this.accepted = pixels.slice()
    return true
  }
}

export type Mask = {x:number;y:number;width:number;height:number}
export function drawMasked(video:HTMLVideoElement, canvas:HTMLCanvasElement, masks:Mask[]) {
  drawMaskedSource(video,video.videoWidth,video.videoHeight,canvas,masks)
}
export function drawMaskedSource(source:CanvasImageSource,width:number,height:number,canvas:HTMLCanvasElement,masks:Mask[]) {
  const scale = Math.min(1, 1920/width, 1440/height)
  canvas.width = Math.round(width*scale)
  canvas.height = Math.round(height*scale)
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(source,0,0,canvas.width,canvas.height)
  ctx.fillStyle = '#000'
  masks.forEach(m=>ctx.fillRect(m.x*canvas.width/100,m.y*canvas.height/100,m.width*canvas.width/100,m.height*canvas.height/100))
}

export async function shareVisualSource():Promise<MediaStream> {
  if (!window.isSecureContext || !navigator.mediaDevices?.getDisplayMedia)
    throw new Error('Compartir requiere un navegador de escritorio compatible en localhost. Puedes adjuntar una imagen.')
  const media = await navigator.mediaDevices.getDisplayMedia({video:{displaySurface:'browser'},audio:false})
  media.getAudioTracks().forEach(t=>t.stop())
  if (media.getVideoTracks()[0]?.getSettings().displaySurface === 'monitor') {
    media.getTracks().forEach(t=>t.stop())
    throw new Error('Selecciona solo una pestaña o ventana del club, no el escritorio completo.')
  }
  return media
}
