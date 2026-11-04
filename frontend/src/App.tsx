import { useState } from 'react';
import { getCatalogue, getRecommendations } from './api';
import type { BusinessProfile, CatalogueProduct, RecommendationResponse } from './types';
import { AdvisorFlow } from './components/AdvisorFlow';
import { LandingPage } from './components/LandingPage';
import { RecommendationView } from './components/RecommendationView';
import { Icon } from './components/Icon';

type Screen = 'home' | 'advisor' | 'loading' | 'results' | 'error';

export default function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [initialNeed, setInitialNeed] = useState<string | undefined>();
  const [result, setResult] = useState<RecommendationResponse | null>(null);
  const [catalogue, setCatalogue] = useState<CatalogueProduct[]>([]);
  const [loadingCatalogue, setLoadingCatalogue] = useState(false);
  const [error, setError] = useState('');

  const start = (need?: string) => {
    setInitialNeed(need);
    setScreen('advisor');
    window.scrollTo({ top: 0 });
  };

  const recommend = async (nextProfile: BusinessProfile) => {
    setProfile(nextProfile);
    setError('');
    setScreen('loading');
    window.scrollTo({ top: 0 });
    try {
      const recommendation = await getRecommendations(nextProfile);
      setResult(recommendation);
      setScreen('results');
      setLoadingCatalogue(true);
      getCatalogue().then(setCatalogue).catch(() => setCatalogue([])).finally(() => setLoadingCatalogue(false));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Something went wrong. Please try again.');
      setScreen('error');
    }
  };

  const edit = () => { setScreen('advisor'); window.scrollTo({ top: 0 }); };
  const restart = () => {
    setProfile(null); setResult(null); setError(''); setCatalogue([]); setInitialNeed(undefined); setScreen('home'); window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (screen === 'home') return <LandingPage onStart={start} />;
  if (screen === 'advisor') return <AdvisorFlow initialNeed={initialNeed} initialProfile={profile ?? undefined} onComplete={recommend} onCancel={restart} />;
  if (screen === 'loading') return <main className="loading-screen"><div className="loading-brand"><span className="brand-mark">u<span>.</span></span><span className="brand-name">udyam<span>digital</span></span></div><div className="loading-content"><span className="loader-mark"><Icon name="spark" size={29} /></span><span className="loading-kicker">A MOMENT, PLEASE</span><h1>Finding your<br /><span>business fit.</span></h1><p>We’re checking your answers against the product catalogue and putting together a considered starting point.</p><div className="skeleton-line" /><div className="skeleton-line short" /></div></main>;
  if (screen === 'error') return <main className="error-screen"><div className="error-card"><div className="error-icon"><Icon name="spark" size={24} /></div><p className="overline">A SMALL PAUSE</p><h1>We couldn’t reach<br />your recommendation.</h1><p>{error}</p><div className="error-actions"><button className="button button-primary" type="button" onClick={() => profile && void recommend(profile)}>Try again <Icon name="arrow" /></button><button className="button button-outline" type="button" onClick={edit}>Edit answers</button></div><button className="text-button error-home" type="button" onClick={restart}>Return to home</button></div></main>;
  if (screen === 'results' && profile && result) return <RecommendationView profile={profile} result={result} catalogue={catalogue} loadingCatalogue={loadingCatalogue} onEdit={edit} onRestart={restart} />;
  return <LandingPage onStart={start} />;
}
