import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';

const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const screenshotDir = new URL('../../docs/screenshots/', import.meta.url);
const userData = 'D:\\AirtelSync\\tmp\\edge-capture-flow';
const browser = spawn(edge, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-port=9222', `--user-data-dir=${userData}`, 'about:blank',
], { stdio: 'ignore', windowsHide: true });

let socket;
let commandId = 0;
const pending = new Map();
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function waitForTarget() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const targets = await (await fetch('http://127.0.0.1:9222/json/list')).json();
      const page = targets.find(target => target.type === 'page');
      if (page) return page;
    } catch { /* Edge is still starting */ }
    await sleep(250);
  }
  throw new Error('Edge DevTools endpoint did not start.');
}

function send(method, params = {}) {
  const id = ++commandId;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Timed out: ${method}`)); }, 12000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const response = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
  return response.result?.value;
}

async function screenshot(name) {
  const response = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(new URL(name, screenshotDir), Buffer.from(response.data, 'base64'));
}

try {
  await mkdir(screenshotDir, { recursive: true });
  const page = await waitForTarget();
  socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const task = pending.get(message.id);
    pending.delete(message.id);
    clearTimeout(task.timer);
    message.error ? task.reject(new Error(message.error.message)) : task.resolve(message.result);
  };

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:5173/' });
  let landingReady = false;
  for (let attempt = 0; attempt < 60 && !landingReady; attempt += 1) {
    landingReady = await evaluate("!!document.querySelector('.hero-actions .button')");
    if (!landingReady) await sleep(150);
  }
  if (!landingReady) throw new Error('Landing page did not render.');
  await sleep(250);
  await screenshot('landing-desktop.png');

  await evaluate("document.querySelector('.hero-actions .button').click()");
  await sleep(250);
  await screenshot('advisor-desktop.png');

  await evaluate(`(() => {
    const input = document.querySelector('#businessType');
    const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setValue.call(input, 'Neighbourhood bakery');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  await evaluate("[...document.querySelectorAll('button')].find(button => button.textContent.includes('Continue')).click()");
  await sleep(180);
  await evaluate(`(() => {
    const inputs = document.querySelectorAll('.field-row input');
    const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setValue.call(inputs[0], '4'); inputs[0].dispatchEvent(new Event('input', { bubbles: true })); inputs[0].dispatchEvent(new Event('change', { bubbles: true }));
    setValue.call(inputs[1], '1'); inputs[1].dispatchEvent(new Event('input', { bubbles: true })); inputs[1].dispatchEvent(new Event('change', { bubbles: true }));
    const city = [...document.querySelectorAll('input')].find(input => input.placeholder === 'e.g. Jaipur');
    setValue.call(city, 'Jaipur'); city.dispatchEvent(new Event('input', { bubbles: true })); city.dispatchEvent(new Event('change', { bubbles: true }));
    const state = [...document.querySelectorAll('input')].find(input => input.placeholder === 'e.g. Rajasthan');
    setValue.call(state, 'Rajasthan'); state.dispatchEvent(new Event('input', { bubbles: true })); state.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  await evaluate("[...document.querySelectorAll('button')].find(button => button.textContent.includes('Continue')).click()");
  await sleep(180);
  await evaluate("document.querySelectorAll('.need-option')[0].click(); document.querySelectorAll('.need-option')[5].click()");
  await evaluate("[...document.querySelectorAll('button')].find(button => button.textContent.includes('Continue')).click()");
  await sleep(180);
  await evaluate("[...document.querySelectorAll('button')].find(button => button.textContent.includes('See my recommendations')).click()");
  await sleep(1200);
  const desktopResult = await evaluate("({ title: document.querySelector('#results-title')?.innerText, bodyWidth: document.documentElement.scrollWidth, viewport: innerWidth, selected: [...document.querySelectorAll('.product-title h3')].map(item => item.innerText) })");
  if (!desktopResult.title || desktopResult.selected.length === 0) throw new Error(`Recommendation flow did not finish: ${JSON.stringify(desktopResult)}`);
  await screenshot('recommendation-desktop.png');

  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await sleep(200);
  const mobileResult = await evaluate("({ bodyWidth: document.documentElement.scrollWidth, viewport: innerWidth, title: document.querySelector('#results-title')?.innerText })");
  await screenshot('recommendation-mobile.png');
  if (mobileResult.bodyWidth > mobileResult.viewport) throw new Error(`Horizontal overflow at mobile width: ${JSON.stringify(mobileResult)}`);
  await evaluate("[...document.querySelectorAll('button')].find(button => button.textContent.includes('Edit your answers')).click()");
  await sleep(180);
  const revisitedBusiness = await evaluate("document.querySelector('#businessType')?.value");
  if (revisitedBusiness !== 'Neighbourhood bakery') throw new Error(`Editing did not preserve the business type: ${revisitedBusiness}`);
  await evaluate("[...document.querySelectorAll('button')].find(button => button.textContent.includes('Continue')).click()");
  await sleep(180);
  const revisitedProfile = await evaluate("({ businessType: document.querySelectorAll('.snapshot-row strong')[0]?.textContent, city: [...document.querySelectorAll('input')].find(input => input.placeholder === 'e.g. Jaipur')?.value, state: [...document.querySelectorAll('input')].find(input => input.placeholder === 'e.g. Rajasthan')?.value })");
  if (revisitedProfile.city !== 'Jaipur' || revisitedProfile.state !== 'Rajasthan') throw new Error(`Editing did not preserve the original location: ${JSON.stringify(revisitedProfile)}`);
  await screenshot('advisor-mobile.png');
  const advisorMobile = await evaluate("({ bodyWidth: document.documentElement.scrollWidth, viewport: innerWidth })");
  if (advisorMobile.bodyWidth > advisorMobile.viewport) throw new Error(`Horizontal overflow in advisor at mobile width: ${JSON.stringify(advisorMobile)}`);
  await evaluate("[...document.querySelectorAll('button')].find(button => button.textContent.includes('Exit')).click()");
  await sleep(180);
  await screenshot('landing-mobile.png');
  const landingMobile = await evaluate("({ bodyWidth: document.documentElement.scrollWidth, viewport: innerWidth, navButton: document.querySelector('.menu-toggle')?.getAttribute('aria-label') })");
  if (landingMobile.bodyWidth > landingMobile.viewport) throw new Error(`Horizontal overflow on mobile landing: ${JSON.stringify(landingMobile)}`);
  await evaluate("document.querySelector('.menu-toggle').click()");
  const menuOpen = await evaluate("document.querySelector('.menu-toggle')?.getAttribute('aria-expanded') === 'true' && !!document.querySelector('.site-nav nav.mobile-open')");
  if (!menuOpen) throw new Error('Mobile navigation menu did not open.');
  console.log(JSON.stringify({ desktop: desktopResult, mobileResults: mobileResult, revisitedProfile, mobileAdvisor: advisorMobile, mobileLanding: landingMobile, mobileMenuOpens: menuOpen, screenshots: ['landing-desktop.png', 'landing-mobile.png', 'advisor-desktop.png', 'advisor-mobile.png', 'recommendation-desktop.png', 'recommendation-mobile.png'] }, null, 2));
} finally {
  socket?.close();
  browser.kill();
}
