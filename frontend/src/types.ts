export type Segment =
  | 'MICRO_RETAIL_AND_SERVICES'
  | 'PROFESSIONAL_OFFICES'
  | 'SMALL_MULTI_SITE_BUSINESSES'
  | 'SMALL_MANUFACTURERS';

export type Need =
  | 'RELIABLE_INTERNET'
  | 'BUSINESS_MOBILITY'
  | 'CUSTOMER_MESSAGING'
  | 'CLOUD_PRODUCTIVITY'
  | 'SECURITY'
  | 'POS_BILLING'
  | 'CCTV'
  | 'MULTI_SITE_MANAGEMENT'
  | 'MACHINE_MONITORING'
  | 'FLEET_TRACKING';

export type GstinStatus = 'ACTIVE' | 'CANCELLED' | 'SUSPENDED' | 'NOT_FOUND' | 'NOT_PROVIDED' | 'LOOKUP_FAILED';

export interface BusinessProfile {
  segment: Segment;
  businessType: string;
  employeeCount: number;
  siteCount: number;
  city: string;
  cityTier: number;
  state: string;
  gstinStatus: GstinStatus;
  currentRequirements: Need[];
  industryActivity: string;
}

export interface ProductSelection { productId: string; quantity: number }
export interface EligibilityIssue { code: string; message: string; requirement: string }
export interface EligibilityItem { productId: string; status: 'ELIGIBLE' | 'INELIGIBLE' | 'MANUAL_REVIEW'; issues: EligibilityIssue[] }
export interface PriceLine {
  productId: string;
  productName: string;
  unit: string;
  quantity: number;
  monthlyMinimum: number;
  monthlyMaximum: number;
  defaultUnitMonthlyPrice: number;
  extendedMonthlyMinimum: number;
  extendedMonthlyMaximum: number;
  extendedDefaultMonthly: number;
  oneTimeSetupFee: number;
  setupFeeBasis: string;
}
export interface BundlePrice {
  lines: PriceLine[];
  monthlyMinimum: number;
  monthlyMaximum: number;
  defaultMonthlyPrice: number;
  oneTimeSetupTotal: number;
  minimumContractMonths: number;
  typicalInstallationDays: number;
  installationEstimateBasis: string;
}
export interface BundleRecommendation {
  bundleName: string;
  selections: ProductSelection[];
  eligibility: { status: EligibilityItem['status']; products: EligibilityItem[] };
  pricing: BundlePrice;
  explanations: string[];
}
export interface CatalogueProduct { productId: string; productName: string; description: string; category: string; unit: string }
export interface RecommendationResponse {
  summary: string;
  recommendations: BundleRecommendation[];
  excludedProducts: EligibilityItem[];
}
