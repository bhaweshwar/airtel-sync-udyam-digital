import type { BusinessProfile } from './types';
import { copy } from './copy.ts';

export function validateStep(step: number, profile: BusinessProfile): string | null {
  if (step === 0 && !profile.businessType.trim()) return copy.advisor.validation.businessType;
  if (step === 1) {
    if (!profile.city.trim()) return copy.advisor.validation.city;
    if (!profile.state.trim()) return copy.advisor.validation.state;
    if (profile.employeeCount < 0 || !Number.isInteger(profile.employeeCount)) return copy.advisor.validation.employees;
    if (profile.siteCount < 1 || !Number.isInteger(profile.siteCount)) return copy.advisor.validation.locations;
    if (![1, 2, 3].includes(profile.cityTier)) return copy.advisor.validation.tier;
  }
  if (step === 2 && profile.currentRequirements.length === 0) return copy.advisor.validation.needs;
  return null;
}
