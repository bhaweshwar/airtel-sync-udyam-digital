import { useEffect, useRef, useState, type FormEvent } from 'react';
import { getAdvisorConversation, sendAdvisorMessage, startAdvisorConversation } from '../api';
import type { AdvisorMessage, AdvisorSessionResponse, Need } from '../types';
import { Icon } from './Icon';

interface AdvisorFlowProps {
  initialNeed?: string;
  initialConversation?: AdvisorSessionResponse;
  onComplete: (conversation: AdvisorSessionResponse) => void;
  onUpdate: (conversation: AdvisorSessionResponse) => void;
  onCancel: () => void;
}

const needNames: Record<Need, string> = {
  RELIABLE_INTERNET: 'Reliable internet', BUSINESS_MOBILITY: 'Business mobility', CUSTOMER_MESSAGING: 'Customer messaging',
  CLOUD_PRODUCTIVITY: 'Cloud & productivity', SECURITY: 'Security', POS_BILLING: 'POS & billing', CCTV: 'CCTV',
  MULTI_SITE_MANAGEMENT: 'Multi-site management', MACHINE_MONITORING: 'Machine monitoring', FLEET_TRACKING: 'Fleet tracking',
};

export function AdvisorFlow({ initialNeed, initialConversation, onComplete, onUpdate, onCancel }: AdvisorFlowProps) {
  const [conversation, setConversation] = useState<AdvisorSessionResponse | null>(initialConversation ?? null);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(!initialConversation);
  const [error, setError] = useState('');
  const [failedMessage, setFailedMessage] = useState('');
  const [reloadAttempt, setReloadAttempt] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    const load = initialConversation
      ? getAdvisorConversation(initialConversation.conversationId)
      : startAdvisorConversation(initialNeed);
    load.then(value => { if (active) { setConversation(value); onUpdate(value); setStarting(false); } })
      .catch(reason => { if (active) { setError(reason instanceof Error ? reason.message : 'The conversation could not be opened.'); setStarting(false); } });
    return () => { active = false; };
  }, [initialConversation?.conversationId, initialNeed, reloadAttempt]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [conversation?.messages.length, loading]);

  const send = async (text: string) => {
    if (!conversation || !text.trim() || loading) return;
    setLoading(true); setError(''); setFailedMessage('');
    try {
      const next = await sendAdvisorMessage(conversation.conversationId, text.trim());
      setConversation(next); onUpdate(next); setDraft('');
      if (next.recommendation) onComplete(next);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The advisor could not respond. Please try again.');
      setFailedMessage(text.trim());
    } finally { setLoading(false); }
  };

  const submit = (event: FormEvent) => { event.preventDefault(); void send(draft); };
  const fillCorrection = () => { setDraft('Correction: '); inputRef.current?.focus(); };
  const profile = conversation?.profile;
  const details = [
    ['Business', profile?.businessType ?? profile?.segment?.replaceAll('_', ' ').toLowerCase() ?? null],
    ['Team', profile?.employeeCount == null ? null : `${profile.employeeCount} ${profile.employeeCount === 1 ? 'person' : 'people'}`],
    ['Locations', profile?.siteCount == null ? null : String(profile.siteCount)],
    ['Based in', profile?.city ? `${profile.city}${profile.state ? `, ${profile.state}` : ''}` : profile?.state ?? null],
    ['Priorities', profile?.currentRequirements.length ? profile.currentRequirements.map(need => needNames[need]).join(', ') : null],
    ['GSTIN status', profile?.gstinStatus && profile.gstinStatus !== 'NOT_PROVIDED' ? `${profile.gstinStatus.toLowerCase()} · self-reported` : null],
  ] as const;

  return <main className="chat-page">
    <header className="advisor-nav"><button className="brand" type="button" onClick={onCancel} aria-label="Return to home"><span className="brand-mark">u<span>.</span></span><span className="brand-name">udyam<span>digital</span></span></button><div className="advisor-nav-right"><span><Icon name="lock" size={15} /> Sensitive identifiers are removed before AI processing</span><button className="text-button" type="button" onClick={onCancel}>Exit <Icon name="close" size={16} /></button></div></header>
    <div className="chat-layout">
      <section className="chat-main" aria-labelledby="chat-title">
        <div className="chat-heading"><p className="overline">YOUR BUSINESS ADVISOR</p><h1 id="chat-title">A conversation that<br /><span>starts with your business.</span></h1><p>Tell us what you do and what would make work easier. Your answers guide a catalogue-based recommendation.</p></div>
        <div className="chat-panel">
          {starting && <div className="chat-state"><span className="typing-indicator"><i /><i /><i /></span><span>Opening your private session…</span></div>}
          {!starting && !conversation && <div className="chat-empty-error" role="alert"><p>{error || 'We could not open this conversation.'}</p><button type="button" className="button button-outline" onClick={() => { setError(''); setStarting(true); setReloadAttempt(value => value + 1); }}>Try again</button></div>}
          {conversation && <>
            {error && !failedMessage && <div className="chat-error" role="alert"><div><b>We couldn’t open this session.</b><span>{error}</span></div><button type="button" className="text-button" onClick={() => { setError(''); setStarting(true); setReloadAttempt(value => value + 1); }}>Retry <Icon name="arrow" size={15} /></button></div>}
            <div className="chat-messages" aria-live="polite" aria-label="Conversation history">
              {!conversation.messages.length && <div className="chat-intro"><span className="intro-spark"><Icon name="spark" size={17} /></span><div><b>Start wherever feels natural.</b><p>For example, tell me what your business does, where it is based, who works there, and what you would like help with. Please don’t include personal ID numbers.</p></div></div>}
              {conversation.messages.map((message: AdvisorMessage, index) => <div className={`chat-message ${message.role === 'user' ? 'customer' : 'advisor'}`} key={`${message.createdAt}-${index}`}><span className="chat-avatar">{message.role === 'user' ? 'You' : <Icon name="spark" size={15} />}</span><div className="chat-bubble"><span className="chat-role">{message.role === 'user' ? 'YOU' : 'BUSINESS ADVISOR'}</span><p>{message.content}</p>{message.role === 'assistant' && index === conversation.messages.length - 1 && conversation.followUpQuestions.length > 0 && <ul className="follow-up-list">{conversation.followUpQuestions.map(question => <li key={question}>{question}</li>)}</ul>}</div></div>)}
              {loading && <div className="chat-message advisor" aria-label="Advisor is responding"><span className="chat-avatar"><Icon name="spark" size={15} /></span><div className="chat-bubble typing-bubble"><span className="chat-role">BUSINESS ADVISOR</span><span className="typing-indicator"><i /><i /><i /></span></div></div>}
              <div ref={endRef} />
            </div>
            {error && <div className="chat-error" role="alert"><div><b>We couldn’t get a response.</b><span>{error}</span></div>{failedMessage && <button type="button" className="text-button" onClick={() => void send(failedMessage)} disabled={loading}>Retry <Icon name="arrow" size={15} /></button>}</div>}
            {conversation.status === 'RECOMMENDATION_READY' && <div className="chat-ready"><Icon name="check" size={16} /><span>Your catalogue-based recommendation is ready.</span><button type="button" onClick={() => onComplete(conversation)}>View recommendation <Icon name="arrow" size={15} /></button></div>}
            <form className="chat-composer" onSubmit={submit}>
              <label className="sr-only" htmlFor="advisor-message">Message your business advisor</label>
              <textarea id="advisor-message" ref={inputRef} value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send(draft); } }} placeholder="Tell us about your business…" maxLength={2000} rows={2} disabled={loading || starting} />
              <div className="composer-bottom"><span>Enter to send · Shift + Enter for a new line</span><button className="button button-primary chat-send" type="submit" disabled={loading || !draft.trim()} aria-label="Send message">Send <Icon name="arrow" size={17} /></button></div>
            </form>
            <p className="chat-privacy"><Icon name="lock" size={14} /> Common personal identifiers are automatically removed before messages reach Gemini. This prototype does not verify GSTIN status.</p>
          </>}
        </div>
      </section>
      <aside className="profile-aside chat-profile" aria-label="Collected business details">
        <div className="aside-heading"><span className="aside-icon"><Icon name="spark" size={17} /></span><div><b>Your business snapshot</b><span>Shared during this conversation</span></div></div>
        <div className="snapshot-content">{details.map(([label, value]) => <div className="snapshot-row" key={label}><span>{label}</span><strong>{value ?? 'Not shared yet'}</strong></div>)}</div>
        {conversation && <div className="chat-missing"><b>{conversation.missingFields.length ? 'Still to learn' : 'Profile details collected'}</b><span>{conversation.missingFields.length ? conversation.missingFields.map(item => item.toLowerCase().replaceAll('_', ' ')).join(' · ') : 'You can add or correct details in the conversation.'}</span></div>}
        <button className="button button-outline aside-edit" type="button" onClick={fillCorrection} disabled={!conversation}>Correct a detail <Icon name="arrow" size={17} /></button>
        <div className="aside-footer"><Icon name="lock" size={15} /><span>Details are kept only in this temporary session.</span></div>
      </aside>
    </div>
  </main>;
}
