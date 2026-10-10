export function imageCoordinates(rect:{left:number;top:number;width:number;height:number},naturalWidth:number,naturalHeight:number,clientX:number,clientY:number,border=0){
  if(!naturalWidth||!naturalHeight)return null
  const width=rect.width-2*border,height=rect.height-2*border
  const scale=Math.min(width/naturalWidth,height/naturalHeight)
  if(scale<=0)return null
  const left=rect.left+border+(width-naturalWidth*scale)/2,top=rect.top+border+(height-naturalHeight*scale)/2
  const x=(clientX-left)/scale,y=(clientY-top)/scale
  if(x<0||y<0||x>=naturalWidth||y>=naturalHeight)return null
  return {x:Math.min(naturalWidth-1,Math.round(x)),y:Math.min(naturalHeight-1,Math.round(y))}
}
