import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, getCatalogue, getRecommendations } from '../src/api.ts';
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
