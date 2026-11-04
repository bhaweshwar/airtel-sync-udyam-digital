// Browser smoke test for the real advisor UI. Requires Vite and Spring Boot running.
// With no Gemini key it verifies the safe recoverable error path; it never fabricates a model response.
import { spawn } from 'node:child_process';

const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const userData = 'D:\\AirtelSync\\tmp\\edge-advisor-smoke';
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

async function waitFor(selector, attempts = 60) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (await evaluate(`!!document.querySelector(${JSON.stringify(selector)})`)) return true;
    await sleep(150);
  }
  return false;
}

try {
  const page = await waitForTarget();
  socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const task = pending.get(message.id);
    pending.delete(message.id); clearTimeout(task.timer);
    message.error ? task.reject(new Error(message.error.message)) : task.resolve(message.result);
  };

  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:5173/' });
  if (!await waitFor('.hero-actions .button')) throw new Error('Landing page did not render.');
  await evaluate("document.querySelector('.hero-actions .button').click()");
  if (!await waitFor('.chat-intro')) throw new Error('Conversational advisor did not open.');

  await evaluate(`(() => {
    const input = document.querySelector('#advisor-message');
    const setValue = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    setValue.call(input, 'I run a small shop in Jaipur.');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    document.querySelector('.chat-composer').requestSubmit();
  })()`);
  if (!await waitFor('.chat-error')) throw new Error('Expected a clear provider-unavailable state.');
  const errorState = await evaluate(`({
    message: document.querySelector('.chat-error').innerText,
    draft: document.querySelector('#advisor-message').value,
    retry: !![...document.querySelectorAll('.chat-error button')].find(button => button.innerText.includes('Retry')),
    advisorMessages: document.querySelectorAll('.chat-message.advisor').length,
  })`);
  if (!errorState.message.includes('GEMINI_API_KEY')) throw new Error(`Missing-key guidance was not shown: ${JSON.stringify(errorState)}`);
  if (errorState.draft !== 'I run a small shop in Jaipur.' || !errorState.retry) throw new Error(`Retry did not preserve the message: ${JSON.stringify(errorState)}`);
  if (errorState.advisorMessages !== 0) throw new Error('An unavailable provider was presented as an AI response.');

  await evaluate("document.querySelector('.chat-error button').click()");
  if (!await waitFor('.chat-error')) throw new Error('Retry state was not restored.');
  await evaluate("document.querySelector('.chat-profile .aside-edit').click()");
  const correctionDraft = await evaluate("document.querySelector('#advisor-message').value");
  if (!correctionDraft.startsWith('Correction:')) throw new Error('Correction control did not preserve the current session context.');

  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  const mobile = await evaluate("({ bodyWidth: document.documentElement.scrollWidth, viewport: innerWidth })");
  if (mobile.bodyWidth > mobile.viewport) throw new Error(`Horizontal overflow at mobile width: ${JSON.stringify(mobile)}`);
  console.log(JSON.stringify({ landing: 'rendered', advisor: 'rendered', missingKeyError: errorState.message,
    draftRetained: true, retryVisible: errorState.retry, noFakeAssistantMessage: errorState.advisorMessages === 0,
    correctionControl: correctionDraft, mobile }, null, 2));
} finally {
  socket?.close();
  browser.kill();
}
