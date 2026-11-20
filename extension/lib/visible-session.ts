// Chrome serializes this function into the isolated world. It must have no closures.
export function visibleSession(): 'club' | 'login' | 'unknown' {
  if (location.origin !== 'https://www.ea.com' || location.search ||
      !/^\/(?:[a-z]{2}-[a-z]{2}\/)?ea-sports-fc\/ultimate-team\/web-app\/$/.test(location.pathname)) return 'unknown'
  const visible = (element: Element) => element.getClientRects().length > 0 &&
    getComputedStyle(element).visibility === 'visible'
  const matches = (selector: string, labels: RegExp) => Array.from(document.querySelectorAll(selector))
    .some(element => visible(element) && labels.test((element.textContent || '').trim()))
  if (Array.from(document.querySelectorAll('input[type=password]')).some(visible) ||
      matches('button', /^(?:login|log in|sign in|iniciar sesi[oó]n)$/i) ||
      matches('h1,h2,[role=heading]', /^(?:cannot authenticate|signed into another device|no se puede autenticar|sesi[oó]n iniciada en otro dispositivo)$/i)) return 'login'
  const club = Array.from(document.querySelectorAll('.view-navbar-clubinfo-name'))
    .some(element => visible(element) && !!element.textContent?.trim())
  return club ? 'club' : 'unknown'
}
