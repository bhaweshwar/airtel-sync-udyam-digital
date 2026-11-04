import { useState } from 'react';
import { copy } from '../copy';
import type { BusinessProfile, CatalogueProduct, EligibilityItem, Need, RecommendationResponse } from '../types';
import { Icon, type IconName } from './Icon';

interface RecommendationViewProps {
  profile: BusinessProfile;
  result: RecommendationResponse;
  catalogue: CatalogueProduct[];
  loadingCatalogue: boolean;
  onEdit: () => void;
  onRestart: () => void;
}

const money = (value: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);

export function RecommendationView({ profile, result, catalogue, loadingCatalogue, onEdit, onRestart }: RecommendationViewProps) {
  const [expanded, setExpanded] = useState(true);
  const [showExcluded, setShowExcluded] = useState(false);
  const option = result.recommendations[0];
  const productFor = (id: string) => catalogue.find(product => product.productId === id);
  const setFor = (items: EligibilityItem[], id: string) => items.find(item => item.productId === id)?.status ?? 'ELIGIBLE';
  const needs = profile.currentRequirements.map(need => copy.needs.find(option => option.id === need as Need)?.title).filter(Boolean);

  return <main className="results-page">
    <header className="results-nav"><button className="brand" type="button" onClick={onRestart} aria-label="Return to home"><span className="brand-mark">u<span>.</span></span><span className="brand-name">udyam<span>digital</span></span></button><div className="results-nav-right"><span className="results-step">YOUR BUSINESS PLAN <i>·</i> 01</span><button className="text-button" type="button" onClick={onRestart}>Start over</button></div></header>
    <div className="results-layout">
      <section className="results-main" aria-labelledby="results-title">
        <button className="back-link" type="button" onClick={onEdit}><Icon name="arrow" size={16} className="back-arrow" /> Edit your answers</button>
        <p className="overline">YOUR RECOMMENDATION</p>
        <h1 id="results-title">A clearer way<br />to <span>move forward.</span></h1>
        <p className="results-intro">{result.summary}</p>

        {option ? <article className="recommendation-card">
          <div className="recommendation-top"><div><span className="recommended-label"><Icon name="spark" size={14} /> A considered starting point</span><h2>{option.bundleName}</h2><p>Based on your business and the priorities you shared.</p></div><span className={`eligibility-pill ${option.eligibility.status.toLowerCase().replace('_', '-')}`}>{option.eligibility.status === 'ELIGIBLE' ? 'Ready to explore' : option.eligibility.status.replace('_', ' ')}</span></div>
          <div className="pricing-highlight"><div><span className="price-caption">ESTIMATED MONTHLY RANGE</span><strong>{money(option.pricing.monthlyMinimum)} <i>–</i> {money(option.pricing.monthlyMaximum)}<small> / month</small></strong><p>Recommended estimate <b>{money(option.pricing.defaultMonthlyPrice)} / month</b></p></div><div className="setup-price"><span>ONE-TIME SETUP</span><strong>{money(option.pricing.oneTimeSetupTotal)}</strong></div></div>
          <div className="terms-row"><div><span className="term-icon"><Icon name="lock" size={16} /></span><span><small>Minimum term</small><b>{option.pricing.minimumContractMonths} months</b></span></div><div><span className="term-icon"><Icon name="arrow" size={16} /></span><span><small>Typical installation</small><b>Up to {option.pricing.typicalInstallationDays} days</b></span></div><div><span className="term-icon"><Icon name="check" size={16} /></span><span><small>Product eligibility</small><b>{option.eligibility.status === 'ELIGIBLE' ? 'All selected products eligible' : option.eligibility.status.replace('_', ' ')}</b></span></div></div>
          <button className="expand-button" type="button" aria-expanded={expanded} onClick={() => setExpanded(value => !value)}><span>{expanded ? 'Hide' : 'See'} recommended services <span className="count-badge">{option.pricing.lines.length}</span></span><span className={`chevron ${expanded ? 'open' : ''}`}><Icon name="arrow" size={16} /></span></button>
          {expanded && <div className="product-list">{option.pricing.lines.map((line, index) => {
            const product = productFor(line.productId);
            const status = setFor(option.eligibility.products, line.productId);
            return <article className="product-row" key={line.productId}><span className="product-icon"><Icon name={(product?.category.toLowerCase().includes('connect') ? 'wifi' : product?.category.toLowerCase().includes('cloud') ? 'cloud' : 'spark') as IconName} size={19} /></span><div className="product-copy"><div className="product-title"><h3>{line.productName}</h3><span className={`product-status ${status.toLowerCase().replace('_', '-')}`}>{status === 'ELIGIBLE' ? 'Eligible' : status.replace('_', ' ')}</span></div><p>{product?.description ?? (loadingCatalogue ? 'Loading product details…' : `${line.unit} · quantity ${line.quantity}`)}</p><span className="product-why"><Icon name="check" size={14} />{option.explanations[index] ?? 'Included in your recommended bundle.'}</span></div><div className="product-price"><b>{money(line.extendedDefaultMonthly)}</b><small>/ month</small><span>{line.unit} · qty {line.quantity}</span></div></article>;
          })}</div>}
          <div className="pricing-disclosure"><Icon name="lock" size={15} /><span>Estimate based on catalogue pricing. Setup is charged once per selected product. Final availability and pricing may vary.</span></div>
        </article> : <div className="empty-recommendation"><span className="empty-icon"><Icon name="spark" size={23} /></span><h2>We need to take another look.</h2><p>{result.summary}</p><p>Some products may need additional eligibility checks. Adjust your answers to explore another combination.</p><button className="button button-primary" onClick={onEdit} type="button">Review my answers <Icon name="arrow" /></button></div>}

        {result.excludedProducts.length > 0 && <section className="excluded-section"><button className="excluded-toggle" type="button" aria-expanded={showExcluded} onClick={() => setShowExcluded(open => !open)}><span>Products needing another check <i>{result.excludedProducts.length}</i></span><span className={`chevron ${showExcluded ? 'open' : ''}`}><Icon name="arrow" size={16} /></span></button>{showExcluded && <div className="excluded-list">{result.excludedProducts.map(item => <article key={item.productId}><div><b>{productFor(item.productId)?.productName ?? item.productId}</b><span className={`product-status ${item.status.toLowerCase().replace('_', '-')}`}>{item.status.replace('_', ' ')}</span></div><p>{item.issues.map(issue => issue.message).join(' ')}</p></article>)}</div>}</section>}
        <div className="results-disclaimer">This recommendation is based on the answers you provided and the available product catalogue. It is not an order or service confirmation.</div>
      </section>
      <aside className="results-aside"><div className="aside-heading"><span className="aside-icon"><Icon name="spark" size={17} /></span><div><b>Your business snapshot</b><span><button type="button" onClick={onEdit}>Edit answers <Icon name="arrow" size={12} /></button></span></div></div><div className="snapshot-content"><div className="snapshot-row"><span>Business</span><strong>{profile.businessType}</strong><small>{copy.segments.find(item => item.id === profile.segment)?.title}</small></div><div className="snapshot-row"><span>Team & locations</span><strong>{profile.employeeCount} {profile.employeeCount === 1 ? 'employee' : 'employees'}</strong><small>{profile.siteCount} {profile.siteCount === 1 ? 'location' : 'locations'}</small></div><div className="snapshot-row"><span>Based in</span><strong>{profile.city}, {profile.state}</strong><small>City tier {profile.cityTier}</small></div><div className="snapshot-row"><span>Your priorities</span><div className="snapshot-tags">{needs.map(need => <span key={need}>{need}</span>)}</div></div></div><div className="aside-footer"><Icon name="lock" size={15} /><span>Prices and eligibility come from the product catalogue.</span></div><button className="button button-outline aside-edit" type="button" onClick={onEdit}>Change my answers <Icon name="arrow" size={17} /></button></aside>
    </div>
  </main>;
}
