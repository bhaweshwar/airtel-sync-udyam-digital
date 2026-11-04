import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, getAdvisorConversation, getAdvisorRecommendation, getCatalogue, getRecommendations, sendAdvisorMessage, startAdvisorConversation } from '../src/api.ts';
import type { BusinessProfile } from '../src/types.ts';

const profile: BusinessProfile = {
  segment: 'MICRO_RETAIL_AND_SERVICES', businessType: 'Bakery', employeeCount: 4,
  siteCount: 1, city: 'Jaipur', cityTier: 2, state: 'Rajasthan',
  gstinStatus: 'NOT_PROVIDED', currentRequirements: ['RELIABLE_INTERNET', 'POS_BILLING'],
  industryActivity: 'Fresh bread and cakes',
};

test('recommendation client posts the Phase 3 profile contract without client prices', async () => {
  const originalFetch = globalThis.fetch;
  let receivedUrl = '';
  let receivedInit: RequestInit | undefined;
  globalThis.fetch = async (input, init) => {
    receivedUrl = String(input);
    receivedInit = init;
    return new Response(JSON.stringify({ summary: 'ok', recommendations: [], excludedProducts: [] }), { status: 200 });
  };
  try {
    const result = await getRecommendations(profile);
    assert.equal(receivedUrl, '/api/v1/recommendations');
    assert.equal(receivedInit?.method, 'POST');
    assert.equal((receivedInit?.headers as Record<string, string>)['Content-Type'], 'application/json');
    assert.deepEqual(JSON.parse(String(receivedInit?.body)), profile);
    assert.deepEqual(result.recommendations, []);
  } finally { globalThis.fetch = originalFetch; }
});

test('catalogue client reads catalogue product names and details', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify([{ productId: 'P01', productName: 'Biz Fibre 100', description: 'Internet access', category: 'CONNECTIVITY', unit: 'per site' }]), { status: 200 });
  try {
    const products = await getCatalogue();
    assert.equal(products[0]?.productName, 'Biz Fibre 100');
    assert.equal(products[0]?.description, 'Internet access');
  } finally { globalThis.fetch = originalFetch; }
});

test('API error envelope is shown to the customer', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ code: 'INVALID_REQUEST', message: 'Choose a supported tier.' }), { status: 400 });
  try {
    await assert.rejects(getRecommendations(profile), error => error instanceof ApiError && error.status === 400 && error.message === 'Choose a supported tier.');
  } finally { globalThis.fetch = originalFetch; }
});

test('network failures become clear recovery guidance', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { throw new TypeError('offline'); };
  try {
    await assert.rejects(getRecommendations(profile), /Check that the local API is running/);
  } finally { globalThis.fetch = originalFetch; }
});

test('advisor starts a server-owned session and submits only the customer message', async () => {
  const originalFetch = globalThis.fetch;
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const session = { conversationId: 'session-1', messages: [], profile: {}, missingFields: [], followUpQuestions: [], status: 'DISCOVERY' };
  globalThis.fetch = async (input, init) => { calls.push({ url: String(input), init }); return new Response(JSON.stringify(session), { status: 200 }); };
  try {
    await startAdvisorConversation('CCTV');
    await sendAdvisorMessage('session-1', 'I run a bakery.');
    assert.equal(calls[0]?.url, '/api/v1/advisor/conversations');
    assert.deepEqual(JSON.parse(String(calls[0]?.init?.body)), { initialNeed: 'CCTV' });
    assert.equal(calls[1]?.url, '/api/v1/advisor/conversations/session-1/messages');
    assert.deepEqual(JSON.parse(String(calls[1]?.init?.body)), { message: 'I run a bakery.' });
  } finally { globalThis.fetch = originalFetch; }
});

test('advisor session and recommendation can be retrieved and recoverable errors remain visible', async () => {
  const originalFetch = globalThis.fetch;
  const calls: string[] = [];
  globalThis.fetch = async input => { calls.push(String(input)); return new Response(JSON.stringify({ conversationId: 'session-1' }), { status: 200 }); };
  try {
    await getAdvisorConversation('session-1');
    await getAdvisorRecommendation('session-1');
    assert.deepEqual(calls, ['/api/v1/advisor/conversations/session-1', '/api/v1/advisor/conversations/session-1/recommendation']);
  } finally { globalThis.fetch = originalFetch; }

  globalThis.fetch = async () => new Response(JSON.stringify({ code: 'ADVISOR_API_KEY_MISSING', message: 'Add GEMINI_API_KEY and retry.' }), { status: 503 });
  try {
    await assert.rejects(sendAdvisorMessage('session-1', 'Hello'), error => error instanceof ApiError && error.status === 503 && error.message.includes('GEMINI_API_KEY'));
  } finally { globalThis.fetch = originalFetch; }
});
