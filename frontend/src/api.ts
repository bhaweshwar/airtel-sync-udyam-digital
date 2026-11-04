import type { BusinessProfile, CatalogueProduct, RecommendationResponse } from './types';
import { copy } from './copy.ts';

export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { headers: { Accept: 'application/json' } });
  } catch {
    throw new ApiError(copy.api.network);
  }
  if (!response.ok) {
    let message = `${copy.api.requestError} (${response.status}).`;
    try {
      const body = await response.json() as { message?: string };
      if (body.message) message = body.message;
    } catch { /* keep the safe fallback message */ }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(copy.api.network);
  }
  if (!response.ok) {
    let message = `${copy.api.requestError} (${response.status}).`;
    try {
      const error = await response.json() as { message?: string };
      if (error.message) message = error.message;
    } catch { /* keep the safe fallback message */ }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export function getCatalogue() {
  return request<CatalogueProduct[]>('/api/v1/catalogue/products');
}

export function getRecommendations(profile: BusinessProfile) {
  return post<RecommendationResponse>('/api/v1/recommendations', profile);
}
