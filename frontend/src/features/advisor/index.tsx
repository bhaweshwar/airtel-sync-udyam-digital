// Advisor chat + voice input. WS2 owns this folder.
// The server decides products and prices (rules engine); this page shows the conversation and a compact quote card.
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import type { AdvisorReply, Quote } from "../../api/types";
import { useT } from "../../i18n";
import { useJourney } from "../../state/journey";
import { Banner, Button, Card, Chip, Money, PageTitle, Pill, cx } from "../../ui";
import { listen, speak, speechSupported, stopSpeaking, ttsSupported, type Recognition } from "./speech";

interface Bubble { from: "user" | "bot"; text: string }
interface ChatState { bubbles: Bubble[]; quick: string[]; last?: AdvisorReply }

const STORAGE_KEY = "udyam.advisor.chat";

function loadChat(): ChatState | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ChatState) : null;
  } catch { return null; }
}

function saveChat(state: ChatState) {
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* storage blocked: keep in memory */ }
}

function clearChat() {
  try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
}

function QuotePreview({ quote, onOpen }: { quote: Quote; onOpen: () => void }) {
  const { t, lt } = useT();
  return (
    <Card className="border-brand-100">
      <div className="flex items-baseline justify-between gap-2">
        <p className="font-semibold">{t("advisor.quoteTitle")}</p>
        <span className="text-sm text-muted">{t("advisor.items", { n: quote.items.length })}</span>
      </div>
      <p className="mt-1 text-2xl font-bold"><Money amount={quote.monthly_total_inr} suffix={t("common.perMonth")} /></p>
      <p className="text-sm text-muted">
        {t("common.plusGst")}
        {quote.one_time_total_inr > 0 && <> · <Money amount={quote.one_time_total_inr} /> {t("common.oneTime")}</>}
      </p>
      <ul className="mt-3 space-y-1.5 text-sm">
        {quote.items.map((i) => (
          <li key={i.product_id}>
            <span className="font-medium">{i.name}</span>{i.quantity > 1 && <span className="text-muted"> × {i.quantity}</span>}
            <span className="block text-muted">{lt(i.reason)}</span>
          </li>
        ))}
      </ul>
      {quote.notices.map((n, k) => <div key={k} className="mt-2"><Banner tone="warn">{lt(n)}</Banner></div>)}
      <Button full className="mt-3" onClick={onOpen}>{t("advisor.seeQuote")}</Button>
    </Card>
  );
}

export function AdvisorPage() {
  const { t, lang } = useT();
  const navigate = useNavigate();
  const { journey, update } = useJourney();
  const greeting = (): ChatState => ({
    bubbles: [{ from: "bot", text: t("advisor.greeting") }],
    quick: [t("advisor.qr.shop"), t("advisor.qr.clinic"), t("advisor.qr.office"), t("advisor.qr.chain"), t("advisor.qr.factory")],
  });
  const [chat, setChat] = useState<ChatState>(() => (journey.advisorSessionId && loadChat()) || greeting());
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const [speaker, setSpeaker] = useState(false);
  const [handoffDone, setHandoffDone] = useState(false);
  const recRef = useRef<Recognition | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const sessionId = chat.last?.session_id ?? journey.advisorSessionId;

  // Re-greet in the new language if the owner switches language before saying anything.
  useEffect(() => {
    setChat((c) => (c.last ? c : greeting()));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  useEffect(() => { saveChat(chat); }, [chat]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [chat.bubbles.length, busy]);
  useEffect(() => () => { recRef.current?.stop(); stopSpeaking(); }, []);

  async function send(text: string) {
    const clean = text.trim();
    if (!clean || busy) return;
    setInput("");
    setError(null);
    setBusy(true);
    setChat((c) => ({ ...c, bubbles: [...c.bubbles, { from: "user", text: clean }], quick: [] }));
    try {
      const reply = await api.advisorMessage({ session_id: sessionId ?? null, text: clean, language: lang });
      setChat((c) => ({ bubbles: [...c.bubbles, { from: "bot", text: reply.reply_text }], quick: reply.quick_replies, last: reply }));
      update({ advisorSessionId: reply.session_id, profile: reply.profile, ...(reply.quote ? { quote: reply.quote } : {}) });
      if (speaker) speak(reply.reply_text, reply.profile.language);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
      setChat((c) => ({ ...c, quick: c.last?.quick_replies ?? c.quick }));
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  function toggleMic() {
    if (listening) {
      recRef.current?.stop();
      return;
    }
    stopSpeaking();
    const rec = listen(lang, (interim) => setInput(interim), (final) => { setInput(final); void send(final); },
      () => { setListening(false); recRef.current = null; });
    if (rec) { recRef.current = rec; setListening(true); }
  }

  async function talkToPerson() {
    if (!sessionId) {
      await send(t("advisor.talkToPerson"));
      return;
    }
    try {
      const res = await api.handoff({ session_id: sessionId, reason: "Owner tapped “Talk to a person” in the advisor" });
      const text = lang === "hi" ? res.message.hi || res.message.en : res.message.en;
      setChat((c) => ({ ...c, bubbles: [...c.bubbles, { from: "bot", text }], quick: [] }));
      setHandoffDone(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    }
  }

  function openQuote() {
    const last = chat.last;
    if (!last?.quote) return;
    update({ quote: last.quote, profile: last.profile, advisorSessionId: last.session_id });
    navigate("/quote");
  }

  function restart() {
    recRef.current?.stop();
    stopSpeaking();
    clearChat();
    update({ advisorSessionId: undefined, quote: undefined, profile: undefined });
    setHandoffDone(false);
    setChat(greeting());
  }

  const last = chat.last;
  const handoff = handoffDone || last?.stage === "handoff";

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <PageTitle title={t("advisor.title")} subtitle={t("advisor.subtitle")} />
        <div className="flex shrink-0 items-center gap-1 pt-1">
          {last?.mode === "rules" && <span title={t("advisor.offlineHint")}><Pill tone="neutral">{t("advisor.offline")}</Pill></span>}
          {ttsSupported && (
            <button type="button" onClick={() => { setSpeaker((s) => !s); stopSpeaking(); }} aria-pressed={speaker}
              aria-label={speaker ? t("advisor.speakerOn") : t("advisor.speakerOff")} title={speaker ? t("advisor.speakerOn") : t("advisor.speakerOff")}
              className={cx("flex h-9 w-9 items-center justify-center rounded-lg border text-lg", speaker ? "border-brand-600 bg-brand-50" : "border-line bg-white")}>
              <span aria-hidden="true">{speaker ? "🔊" : "🔈"}</span>
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2" role="log" aria-live="polite">
        {chat.bubbles.map((b, i) => (
          <div key={i} className={cx("flex", b.from === "user" ? "justify-end" : "justify-start")}>
            <p className={cx("max-w-[85%] whitespace-pre-line rounded-2xl px-3.5 py-2.5 text-[0.95rem] leading-snug",
              b.from === "user" ? "rounded-br-md bg-brand-600 text-white" : "rounded-bl-md border border-line bg-white text-ink")}>
              <span className="sr-only">{b.from === "user" ? t("advisor.you") : t("advisor.bot")}: </span>{b.text}
            </p>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start" role="status" aria-label={t("advisor.typing")}>
            <span className="flex gap-1 rounded-2xl rounded-bl-md border border-line bg-white px-4 py-3.5">
              {[0, 150, 300].map((d) => <span key={d} className="h-2 w-2 animate-bounce rounded-full bg-muted" style={{ animationDelay: `${d}ms` }} />)}
            </span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {last?.quote && last.stage === "recommended" && <QuotePreview quote={last.quote} onOpen={openQuote} />}

      {chat.quick.length > 0 && !busy && (
        <div className="flex flex-wrap gap-2">
          {chat.quick.map((q) => <Chip key={q} onClick={() => void send(q)}>{q}</Chip>)}
        </div>
      )}

      {error && <Banner tone="bad">{error}</Banner>}

      <form onSubmit={onSubmit} className="sticky bottom-2 flex items-center gap-2 rounded-2xl border border-line bg-white p-1.5 shadow-sm">
        {speechSupported && (
          <button type="button" onClick={toggleMic} aria-pressed={listening} aria-label={listening ? t("advisor.micStop") : t("advisor.mic")}
            className={cx("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-lg",
              listening ? "animate-pulse bg-bad text-white" : "bg-brand-50 text-brand-700")}>
            <span aria-hidden="true">🎤</span>
          </button>
        )}
        <input value={input} onChange={(e) => setInput(e.target.value)} disabled={busy} maxLength={2000}
          placeholder={listening ? t("advisor.listening") : t("advisor.placeholder")} aria-label={t("advisor.placeholder")}
          className="min-w-0 flex-1 bg-transparent px-2 py-2 text-base outline-none" />
        <Button type="submit" size="sm" disabled={busy || !input.trim()}>{t("advisor.send")}</Button>
      </form>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button variant="ghost" size="sm" onClick={() => void talkToPerson()} disabled={busy || handoff}>
          {handoff ? t("advisor.handoffSent") : t("advisor.talkToPerson")}
        </Button>
        {last && <Button variant="ghost" size="sm" onClick={restart}>{t("advisor.restart")}</Button>}
      </div>
    </div>
  );
}
