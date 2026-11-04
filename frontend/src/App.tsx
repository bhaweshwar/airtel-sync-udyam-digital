import { useState } from 'react';
import { getCatalogue } from './api';
import type { AdvisorSessionResponse, BusinessProfile, CatalogueProduct, RecommendationResponse } from './types';
import { AdvisorFlow } from './components/AdvisorFlow';
import { LandingPage } from './components/LandingPage';
import { RecommendationView } from './components/RecommendationView';

type Screen = 'home' | 'advisor' | 'results';

export default function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [conversation, setConversation] = useState<AdvisorSessionResponse | null>(null);
  const [initialNeed, setInitialNeed] = useState<string | undefined>();
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [catalogue, setCatalogue] = useState<CatalogueProduct[]>([]);
  const [loadingCatalogue, setLoadingCatalogue] = useState(false);

  const start = (need?: string) => {
    setInitialNeed(need);
    setScreen('advisor');
    window.scrollTo({ top: 0 });
  };

  const updateConversation = (next: AdvisorSessionResponse) => {
    setConversation(next);
    if (!next.recommendation || !next.profile.segment || !next.profile.businessType || next.profile.employeeCount == null
      || next.profile.siteCount == null || !next.profile.city || next.profile.cityTier == null || !next.profile.state) return;
    setProfile({
      segment: next.profile.segment, businessType: next.profile.businessType, employeeCount: next.profile.employeeCount,
      siteCount: next.profile.siteCount, city: next.profile.city, cityTier: next.profile.cityTier, state: next.profile.state,
      gstinStatus: next.profile.gstinStatus ?? 'NOT_PROVIDED', currentRequirements: next.profile.currentRequirements,
      industryActivity: next.profile.industryActivity ?? '',
    });
    setResult(next.recommendation);
    setScreen('results');
    setLoadingCatalogue(true);
    getCatalogue().then(setCatalogue).catch(() => setCatalogue([])).finally(() => setLoadingCatalogue(false));
  };

  const edit = () => { setScreen('advisor'); window.scrollTo({ top: 0 }); };
  const restart = () => {
    setProfile(null); setResult(null); setConversation(null); setCatalogue([]); setInitialNeed(undefined); setScreen('home'); window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (screen === 'home') return <LandingPage onStart={start} />;
  if (screen === 'advisor') return <AdvisorFlow initialNeed={conversation ? undefined : initialNeed} initialConversation={conversation ?? undefined} onComplete={updateConversation} onUpdate={setConversation} onCancel={restart} />;
  if (screen === 'results' && profile && result) return <RecommendationView profile={profile} result={result} catalogue={catalogue} loadingCatalogue={loadingCatalogue} onEdit={edit} onRestart={restart} advisorExplanation={conversation?.advisorExplanation ?? undefined} productExplanations={conversation?.productExplanations} />;
  return <LandingPage onStart={start} />;
}
