// Browser speech helpers: Web Speech API recognition (mic) and speechSynthesis (speaker). WS2 owns this file.
// Recognition isn't in TypeScript's DOM lib yet, so the few members we use are typed here.
import type { Language } from "../../api/types";

interface RecognitionResult { isFinal: boolean; 0: { transcript: string } }
interface RecognitionEvent { resultIndex: number; results: ArrayLike<RecognitionResult> }
export interface Recognition {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: RecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start(): void;
  stop(): void;
}
type RecognitionCtor = new () => Recognition;

function ctor(): RecognitionCtor | undefined {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition || w.webkitSpeechRecognition;
}

export const speechSupported = typeof window !== "undefined" && !!ctor();
export const ttsSupported = typeof window !== "undefined" && "speechSynthesis" in window;

export const speechLang = (lang: Language) => (lang === "hi" ? "hi-IN" : "en-IN");

/** Start listening. onInterim gets the running transcript; onFinal fires once with the final text. */
export function listen(lang: Language, onInterim: (t: string) => void, onFinal: (t: string) => void, onEnd: () => void): Recognition | null {
  const Ctor = ctor();
  if (!Ctor) return null;
  const rec = new Ctor();
  rec.lang = speechLang(lang);
  rec.interimResults = true;
  rec.continuous = false;
  rec.onresult = (e) => {
    let text = "";
    let final = false;
    for (let i = 0; i < e.results.length; i++) {
      text += e.results[i][0].transcript;
      if (e.results[i].isFinal) final = true;
    }
    if (final) onFinal(text.trim());
    else onInterim(text);
  };
  rec.onend = onEnd;
  rec.onerror = onEnd;
  try { rec.start(); } catch { return null; }
  return rec;
}

export function speak(text: string, lang: Language) {
  if (!ttsSupported) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/•/g, ""));
    u.lang = speechLang(lang);
    window.speechSynthesis.speak(u);
  } catch { /* speech blocked: ignore */ }
}

export function stopSpeaking() {
  if (ttsSupported) try { window.speechSynthesis.cancel(); } catch { /* ignore */ }
}
