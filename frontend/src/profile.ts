import type { BusinessProfile } from './types';

export const blankProfile = (): BusinessProfile => ({
  segment: 'MICRO_RETAIL_AND_SERVICES', businessType: '', employeeCount: 1, siteCount: 1,
  city: '', cityTier: 1, state: '', gstinStatus: 'NOT_PROVIDED', currentRequirements: [], industryActivity: '',
});
