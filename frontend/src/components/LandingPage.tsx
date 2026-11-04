import { useState } from 'react';
import { copy } from '../copy';
import { Icon, type IconName } from './Icon';

interface LandingPageProps { onStart: (need?: string) => void }

export function LandingPage({ onStart }: LandingPageProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigateTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  const jumpTo = (id: string) => { setMobileMenuOpen(false); navigateTo(id); };

  return <div className="landing">
    <div className="topline"><span>Thoughtful technology for the people who build India.</span><a href="#how-it-works" onClick={event => { event.preventDefault(); navigateTo('how-it-works'); }}>How it works <Icon name="arrow" size={15} /></a></div>
    <header className="site-nav">
      <a className="brand" href="#top" onClick={event => { event.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); }} aria-label="Udyam Digital home">
        <span className="brand-mark" aria-hidden="true">u<span>.</span></span><span className="brand-name">udyam<span>digital</span></span>
      </a>
      <nav className={mobileMenuOpen ? 'mobile-open' : ''} aria-label="Main navigation"><a href="#solutions" onClick={event => { event.preventDefault(); jumpTo('solutions'); }}>Explore solutions</a><a href="#how-it-works" onClick={event => { event.preventDefault(); jumpTo('how-it-works'); }}>How it works</a></nav>
      <button className="menu-toggle" type="button" aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'} aria-expanded={mobileMenuOpen} onClick={() => setMobileMenuOpen(open => !open)}><Icon name={mobileMenuOpen ? 'close' : 'menu'} /></button>
      <button className="nav-cta" onClick={() => onStart()} type="button">Get started <Icon name="arrow" size={16} /></button>
    </header>

    <main id="top">
      <section className="hero wrap">
        <div className="hero-copy">
          <p className="overline"><span className="live-dot" /> {copy.landing.heroTag}</p>
          <h1>{copy.landing.heroClaim[0]}<br /><span>{copy.landing.heroClaim[1]}</span></h1>
          <p className="hero-intro">{copy.intro}</p>
          <div className="hero-actions"><button className="button button-primary" onClick={() => onStart()} type="button">{copy.start} <Icon name="arrow" /></button><span className="time-note"><Icon name="lock" size={16} /> Takes about 2 minutes</span></div>
          <div className="hero-proof"><div className="proof-avatars" aria-hidden="true"><span>R</span><span>M</span><span>S</span></div><p>Built around the way<br /><strong>small businesses work.</strong></p><span className="proof-divider" /><p className="proof-rating"><span>★★★★★</span><br />A more considered start</p></div>
        </div>
        <div className="hero-art" aria-label="Illustration of connected digital services">
          <div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" />
          <div className="art-stamp"><span>YOUR BUSINESS,</span><strong>IN SYNC</strong><Icon name="arrowUp" size={17} /></div>
          <div className="art-core"><span className="core-mark">u<span>.</span></span><span>One clear<br />way forward</span></div>
          <div className="service-tile tile-connect"><span className="tile-icon"><Icon name="wifi" /></span><span><b>Stay connected</b><small>Reliable internet</small></span><i><Icon name="check" size={15} /></i></div>
          <div className="service-tile tile-grow"><span className="tile-icon tile-icon-dark"><Icon name="spark" /></span><span><b>Find your fit</b><small>Made for your needs</small></span></div>
          <div className="service-tile tile-secure"><span className="tile-icon tile-icon-cream"><Icon name="shield" /></span><span><b>Work confidently</b><small>Security & support</small></span></div>
          <span className="art-note note-top">A little less complexity.</span><span className="art-note note-bottom">A little more possibility.</span>
        </div>
      </section>

      <section className="category-band" id="solutions">
        <div className="wrap"><div className="section-heading"><div><p className="overline">{copy.landing.categoryEyebrow}</p><h2>{copy.landing.categoryHeading}</h2></div><p>{copy.landing.categoryIntro}</p></div>
          <div className="category-grid">{copy.landing.categories.map(item => <button className="category-card" type="button" key={item.title} onClick={() => onStart(item.need)}><span className="category-icon"><Icon name={item.icon as IconName} /></span><strong>{item.title}</strong><span>{item.subtitle}</span><i><Icon name="arrow" size={17} /></i></button>)}</div>
        </div>
      </section>

      <section className="how-section wrap" id="how-it-works"><div className="how-top"><p className="overline">{copy.landing.howEyebrow}</p><h2>{copy.landing.howHeading[0]}<br />{copy.landing.howHeading[1]}</h2><p>{copy.landing.howIntro}</p></div><div className="how-list">{copy.trust.map(item => <article className="how-item" key={item.number}><span>{item.number}</span><div><h3>{item.title}</h3><p>{item.detail}</p></div><Icon name="arrow" size={18} /></article>)}</div></section>
    </main>
    <footer className="site-footer"><div className="wrap footer-inner"><a className="brand brand-footer" href="#top" onClick={event => { event.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); }}><span className="brand-mark" aria-hidden="true">u<span>.</span></span><span className="brand-name">udyam<span>digital</span></span></a><span>{copy.landing.footer}</span><span className="footer-disclosure">{copy.landing.disclosure}</span></div></footer>
  </div>;
}
