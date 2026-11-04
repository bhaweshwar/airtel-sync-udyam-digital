import { useState } from 'react';
import { copy } from '../copy';
import { blankProfile } from '../profile';
import type { BusinessProfile, GstinStatus, Need, Segment } from '../types';
import { validateStep } from '../validation';
import { Icon, type IconName } from './Icon';

interface AdvisorFlowProps {
  initialNeed?: string;
  initialProfile?: BusinessProfile;
  onComplete: (profile: BusinessProfile) => void;
  onCancel: () => void;
}

export function AdvisorFlow({ initialNeed, initialProfile, onComplete, onCancel }: AdvisorFlowProps) {
  const [profile, setProfile] = useState(() => initialProfile ? { ...initialProfile } : ({ ...blankProfile(), currentRequirements: initialNeed ? [initialNeed as Need] : [] }));
  const [step, setStep] = useState(0);
  const [error, setError] = useState('');
  const [businessTypeError, setBusinessTypeError] = useState(false);

  const update = <K extends keyof BusinessProfile>(key: K, value: BusinessProfile[K]) => {
    setProfile(current => ({ ...current, [key]: value }));
    setError('');
    if (key === 'businessType') setBusinessTypeError(false);
  };
  const toggleNeed = (need: Need) => update('currentRequirements', profile.currentRequirements.includes(need)
    ? profile.currentRequirements.filter(item => item !== need)
    : [...profile.currentRequirements, need]);
  const next = () => {
    const issue = validateStep(step, profile);
    if (issue) { setError(issue); setBusinessTypeError(step === 0); return; }
    setError('');
    if (step === copy.steps.length - 1) onComplete({ ...profile, businessType: profile.businessType.trim(), city: profile.city.trim(), state: profile.state.trim(), industryActivity: profile.industryActivity.trim() });
    else setStep(current => current + 1);
  };

  const activeStepTitle = copy.advisor.titles[step];

  return <main className="advisor-page">
    <header className="advisor-nav"><button className="brand" type="button" onClick={onCancel} aria-label="Return to home"><span className="brand-mark">u<span>.</span></span><span className="brand-name">udyam<span>digital</span></span></button><div className="advisor-nav-right"><span><Icon name="lock" size={15} /> Your answers stay in this session</span><button className="text-button" type="button" onClick={onCancel}>Exit <Icon name="close" size={16} /></button></div></header>
    <div className="advisor-layout">
      <section className="advisor-main" aria-labelledby="advisor-title">
        <button className="back-link" type="button" onClick={() => step ? setStep(step - 1) : onCancel()}><Icon name="arrow" size={16} className="back-arrow" /> {step ? 'Previous question' : 'Back to overview'}</button>
        <div className="step-meta"><span>BUSINESS ADVISOR</span><span>STEP {step + 1} <i>/</i> {copy.steps.length}</span></div>
        <div className="progress-track" aria-label={`Step ${step + 1} of ${copy.steps.length}`}><span style={{ width: `${((step + 1) / copy.steps.length) * 100}%` }} /></div>
        <p className="advisor-greeting"><span className="advisor-spark"><Icon name="spark" size={15} /></span> Let’s find your fit</p>
        <h1 id="advisor-title" key={step} className="step-title">{activeStepTitle}</h1>
        <p className="step-description">{copy.advisor.descriptions[step]}</p>

        <div className="question-content" key={`content-${step}`}>
          {step === 0 && <>
            <div className="field-label">Choose the closest fit</div>
            <div className="option-grid segment-grid">{copy.segments.map(option => <button type="button" key={option.id} className={`choice-card ${profile.segment === option.id ? 'selected' : ''}`} aria-pressed={profile.segment === option.id} onClick={() => update('segment', option.id as Segment)}><span className="choice-icon"><Icon name={option.icon as IconName} /></span><span className="choice-copy"><b>{option.title}</b><small>{option.detail}</small></span><span className="radio-mark"><Icon name="check" size={13} /></span></button>)}</div>
            <label className="field-label" htmlFor="businessType">{copy.advisor.businessTypeLabel} <span>{copy.advisor.businessTypeHint}</span></label>
            <input className={`text-input ${businessTypeError ? 'input-error' : ''}`} id="businessType" value={profile.businessType} onChange={event => update('businessType', event.target.value)} placeholder={copy.advisor.businessTypePlaceholder} maxLength={100} />
          </>}

          {step === 1 && <>
            <div className="field-row">
              <label className="form-field">{copy.advisor.teamLabel}<input className="text-input" type="number" min="0" max="100000" value={profile.employeeCount} onChange={event => update('employeeCount', Number(event.target.value))} /></label>
              <label className="form-field">{copy.advisor.locationsLabel}<input className="text-input" type="number" min="1" max="10000" value={profile.siteCount} onChange={event => update('siteCount', Number(event.target.value))} /></label>
            </div>
            <div className="field-row location-fields">
              <label className="form-field">{copy.advisor.cityLabel}<input className="text-input" autoComplete="address-level2" value={profile.city} onChange={event => update('city', event.target.value)} placeholder="e.g. Jaipur" maxLength={80} /></label>
              <label className="form-field">{copy.advisor.stateLabel}<input className="text-input" autoComplete="address-level1" value={profile.state} onChange={event => update('state', event.target.value)} placeholder="e.g. Rajasthan" maxLength={80} /></label>
            </div>
            <fieldset className="tier-field"><legend className="field-label">{copy.advisor.tierLabel} <span>{copy.advisor.tierHint}</span></legend><div className="tier-options">{[1, 2, 3].map(tier => <button key={tier} type="button" className={`tier-option ${profile.cityTier === tier ? 'selected' : ''}`} aria-pressed={profile.cityTier === tier} onClick={() => update('cityTier', tier)}><b>Tier {tier}</b><span>{['Major cities', 'Growing cities', 'Other cities'][tier - 1]}</span></button>)}</div></fieldset>
          </>}

          {step === 2 && <>
            <div className="field-label">{copy.advisor.needsLabel}</div>
            <div className="need-grid">{copy.needs.map(need => <button type="button" key={need.id} className={`need-option ${profile.currentRequirements.includes(need.id as Need) ? 'selected' : ''}`} aria-pressed={profile.currentRequirements.includes(need.id as Need)} onClick={() => toggleNeed(need.id as Need)}><span className="need-icon"><Icon name={need.icon as IconName} size={19} /></span><span className="need-copy"><b>{need.title}</b><small>{need.detail}</small></span><span className="checkbox-mark"><Icon name="check" size={13} /></span></button>)}</div>
            <label className="form-field context-field">{copy.advisor.contextLabel} <span>{copy.advisor.contextHint}</span><textarea className="text-input textarea" value={profile.industryActivity} onChange={event => update('industryActivity', event.target.value)} placeholder={copy.advisor.contextPlaceholder} maxLength={240} rows={3} /></label>
          </>}

          {step === 3 && <>
            <div className="gstin-note"><span className="note-icon"><Icon name="lock" /></span><div><b>{copy.advisor.gstinIntro}</b><p>{copy.advisor.gstinDescription}</p></div></div>
            <fieldset className="gstin-options"><legend className="field-label">{copy.advisor.gstinQuestion}</legend>{([
              ['NOT_PROVIDED', copy.advisor.gstinOptions[0]], ['ACTIVE', copy.advisor.gstinOptions[1]], ['SUSPENDED', copy.advisor.gstinOptions[2]], ['CANCELLED', copy.advisor.gstinOptions[3]],
            ] as [GstinStatus, string][]).map(([value, label]) => <button type="button" key={value} className={`gstin-option ${profile.gstinStatus === value ? 'selected' : ''}`} aria-pressed={profile.gstinStatus === value} onClick={() => update('gstinStatus', value)}><span className="radio-mark"><Icon name="check" size={13} /></span>{label}</button>)}</fieldset>
            <div className="privacy-footnote"><Icon name="lock" size={16} /> We only use these details to prepare a recommendation in this session.</div>
          </>}
        </div>

        <div className="advisor-actions"><div>{error && <p className="field-error" role="alert">{error}</p>}</div><button className="button button-primary" type="button" onClick={next}>{step === copy.steps.length - 1 ? copy.review : copy.continue}<Icon name="arrow" /></button></div>
      </section>
      <aside className="profile-aside" aria-label="Your business profile">
        <div className="aside-heading"><span className="aside-icon"><Icon name="spark" size={17} /></span><div><b>Your business snapshot</b><span>Just for your recommendation</span></div></div>
        <div className="snapshot-content">
          <div className="snapshot-row"><span>Business</span><strong>{profile.businessType || 'Not added yet'}</strong><small>{copy.segments.find(item => item.id === profile.segment)?.title}</small></div>
          <div className="snapshot-row"><span>Team & locations</span><strong>{profile.employeeCount} {profile.employeeCount === 1 ? 'employee' : 'employees'}</strong><small>{profile.siteCount} {profile.siteCount === 1 ? 'location' : 'locations'}</small></div>
          <div className="snapshot-row"><span>Based in</span><strong>{profile.city || 'Not added yet'}</strong><small>{profile.state || `City tier ${profile.cityTier}`}</small></div>
          <div className="snapshot-row"><span>Priorities</span><div className="snapshot-tags">{profile.currentRequirements.length ? profile.currentRequirements.slice(0, 3).map(need => <span key={need}>{copy.needs.find(item => item.id === need)?.title}</span>) : <small>Choose what you need</small>}{profile.currentRequirements.length > 3 && <span>+{profile.currentRequirements.length - 3} more</span>}</div></div>
        </div>
        <div className="aside-footer"><Icon name="lock" size={15} /><span>Your answers help check product fit. No account needed.</span></div>
      </aside>
    </div>
  </main>;
}
