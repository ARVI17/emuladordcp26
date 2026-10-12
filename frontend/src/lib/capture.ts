/** Browser permission is requested for each share. There is no account authentication. */
export async function shareTab():Promise<MediaStream>{
 if(!navigator.mediaDevices?.getDisplayMedia)throw new Error('Este navegador no permite compartir pestañas. Adjunta una captura como alternativa.')
 const stream=await navigator.mediaDevices.getDisplayMedia({video:{displaySurface:'browser'},audio:false})
 stream.getAudioTracks().forEach(track=>track.stop())
 const source=stream.getVideoTracks()[0]?.getSettings().displaySurface
 if(source&&source!=='browser'){stream.getTracks().forEach(track=>track.stop());throw new Error('Selecciona una pestaña del navegador para limitar lo compartido.')}
 return stream
}
export function stopTracks(stream:MediaStream|null){stream?.getTracks().forEach(track=>track.stop())}
export async function captureFrame(video:HTMLVideoElement):Promise<Blob>{
 if(video.readyState<2||!video.videoWidth)throw new Error('Espera a que aparezca la pestaña compartida.')
 const canvas=document.createElement('canvas'),scale=Math.min(1,2560/video.videoWidth,1440/video.videoHeight)
 canvas.width=Math.round(video.videoWidth*scale);canvas.height=Math.round(video.videoHeight*scale)
 canvas.getContext('2d')!.drawImage(video,0,0,canvas.width,canvas.height)
 return new Promise((resolve,reject)=>canvas.toBlob(blob=>{canvas.width=canvas.height=0;blob?resolve(blob):reject(new Error('No se pudo leer el fotograma.'))},'image/png'))
}
