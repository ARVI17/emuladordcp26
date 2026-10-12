import '@testing-library/jest-dom'
import {cleanup} from '@testing-library/react'
import {afterEach,vi} from 'vitest'
afterEach(()=>{cleanup();vi.restoreAllMocks()})

// jsdom has no dialog lifecycle; real modal/focus behavior is exercised by Playwright.
if(!HTMLDialogElement.prototype.showModal)HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')}
if(!HTMLDialogElement.prototype.close)HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')}
