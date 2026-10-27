import {expect,it,vi} from 'vitest'
import {openOfficialTab} from './official-tab'
it('reuses its official window and removes opener before navigation',()=>{
 const tab={closed:false,opener:window,focus:vi.fn(),location:{replace:vi.fn()}}
 const open=vi.spyOn(window,'open').mockReturnValue(tab as unknown as Window)
 openOfficialTab();openOfficialTab()
 expect(open).toHaveBeenCalledTimes(1)
 expect(tab.opener).toBeNull()
 expect(tab.focus).toHaveBeenCalledOnce()
 expect(tab.location.replace).toHaveBeenCalledWith('https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/')
 tab.closed=true;open.mockRestore()
})
