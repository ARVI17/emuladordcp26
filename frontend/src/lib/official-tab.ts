let officialTab:Window|null=null
export function openOfficialTab(){
 if(officialTab&&!officialTab.closed){officialTab.focus();return}
 const tab=window.open('about:blank','_blank')
 if(!tab)return
 tab.opener=null
 tab.location.replace('https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/')
 officialTab=tab
}
