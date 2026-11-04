import test from 'node:test';
import assert from 'node:assert/strict';
import { blankProfile } from '../src/profile.ts';
import { validateStep } from '../src/validation.ts';

test('advisor validates required business type without requiring optional values', () => {
  const profile = blankProfile();
  assert.equal(validateStep(0, profile), 'Add the kind of business you run to continue.');
  profile.businessType = 'Neighbourhood bakery';
  assert.equal(validateStep(0, profile), null);
});

test('advisor validates city, state, team and location counts', () => {
  const profile = blankProfile();
  profile.businessType = 'Bakery';
  assert.equal(validateStep(1, profile), 'Enter the city where your business is based.');
  profile.city = 'Jaipur';
  assert.equal(validateStep(1, profile), 'Enter your state.');
  profile.state = 'Rajasthan';
  profile.employeeCount = -1;
  assert.equal(validateStep(1, profile), 'Enter a valid number of employees.');
  profile.employeeCount = 4;
  profile.siteCount = 0;
  assert.equal(validateStep(1, profile), 'Your business must have at least one location.');
  profile.siteCount = 2;
  profile.cityTier = 4;
  assert.equal(validateStep(1, profile), 'Choose a city tier to continue.');
  profile.cityTier = 2;
  assert.equal(validateStep(1, profile), null);
});

test('advisor requires at least one business priority', () => {
  const profile = blankProfile();
  assert.equal(validateStep(2, profile), 'Choose at least one area where you would like support.');
  profile.currentRequirements = ['RELIABLE_INTERNET'];
  assert.equal(validateStep(2, profile), null);
});

test('advisor accepts the optional final GSTIN step', () => {
  assert.equal(validateStep(3, blankProfile()), null);
});
