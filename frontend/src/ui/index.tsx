// Shared UI primitives. Phase 0 owns this file; workstreams compose these and keep feature-specific components
// inside their own src/features/<name>/ folder.
import type { ButtonHTMLAttributes, ReactNode } from "react";

function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

// ---------------------------------------------------------------- Button

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export function Button({ variant = "primary", size = "md", full, className, ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: "sm" | "md" | "lg"; full?: boolean }) {
  const base = "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2.5 text-base", lg: "px-5 py-3.5 text-lg" };
  const variants: Record<ButtonVariant, string> = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-700",
    secondary: "bg-white text-brand-700 border border-brand-100 hover:bg-brand-50",
    ghost: "text-brand-700 hover:bg-brand-50",
    danger: "bg-bad text-white hover:opacity-90",
  };
  return <button className={cx(base, sizes[size], variants[variant], full && "w-full", className)} {...rest} />;
}

// ---------------------------------------------------------------- Card

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("rounded-2xl border border-line bg-white p-4 shadow-sm", className)}>{children}</div>;
}

// ---------------------------------------------------------------- Chip (quick replies, filters)

export function Chip({ children, selected, onClick, disabled }: { children: ReactNode; selected?: boolean; onClick?: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-pressed={selected}
      className={cx("rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors disabled:opacity-50",
        selected ? "border-brand-600 bg-brand-600 text-white" : "border-brand-100 bg-white text-brand-700 hover:bg-brand-50")}>
      {children}
    </button>
  );
}

// ---------------------------------------------------------------- Toggle (switch)

export function Toggle({ checked, onChange, label, disabled, id }: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean; id?: string }) {
  return (
    <button type="button" role="switch" id={id} aria-checked={checked} aria-label={label} disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cx("relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors disabled:opacity-50",
        checked ? "bg-brand-600" : "bg-line")}>
      <span className={cx("inline-block h-5 w-5 rounded-full bg-white shadow transition-transform", checked ? "translate-x-6" : "translate-x-1")} />
    </button>
  );
}

// ---------------------------------------------------------------- Stepper (quantity)

export function Stepper({ value, onChange, min = 1, max = 99, label }: { value: number; onChange: (v: number) => void; min?: number; max?: number; label: string }) {
  const btn = "h-8 w-8 rounded-lg border border-line bg-white text-lg font-semibold text-brand-700 disabled:opacity-40";
  return (
    <div className="inline-flex items-center gap-2" role="group" aria-label={label}>
      <button type="button" className={btn} aria-label={`${label} −`} disabled={value <= min} onClick={() => onChange(Math.max(min, value - 1))}>−</button>
      <span className="tabular w-8 text-center font-semibold" aria-live="polite">{value}</span>
      <button type="button" className={btn} aria-label={`${label} +`} disabled={value >= max} onClick={() => onChange(Math.min(max, value + 1))}>+</button>
    </div>
  );
}

// ---------------------------------------------------------------- Money (₹ with Indian digit grouping)

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export function formatInr(amount: number): string {
  return inr.format(amount);
}

export function Money({ amount, suffix, className }: { amount: number; suffix?: string; className?: string }) {
  return <span className={cx("tabular", className)}>{formatInr(amount)}{suffix && <span className="text-muted text-[0.8em] font-normal">{suffix}</span>}</span>;
}

// ---------------------------------------------------------------- Pill (status badges)

export type Tone = "ok" | "warn" | "bad" | "info" | "neutral";
const toneClass: Record<Tone, string> = {
  ok: "bg-ok-bg text-ok",
  warn: "bg-warn-bg text-warn",
  bad: "bg-bad-bg text-bad",
  info: "bg-brand-50 text-brand-700",
  neutral: "bg-surface text-muted border border-line",
};

export function Pill({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={cx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold", toneClass[tone])}>{children}</span>;
}

// ---------------------------------------------------------------- Banner (notices, errors)

export function Banner({ tone = "info", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <div role={tone === "bad" ? "alert" : "status"} className={cx("rounded-xl px-4 py-3 text-sm", toneClass[tone])}>
      {title && <p className="font-semibold">{title}</p>}
      <div>{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------- Spinner

export function Spinner({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-muted" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-100 border-t-brand-600" aria-hidden="true" />
      <span className="text-sm">{label}</span>
    </span>
  );
}

// ---------------------------------------------------------------- Timeline (tracker)

export type StepState = "done" | "current" | "upcoming" | "blocked";

export function Timeline({ steps }: { steps: { key: string; label: string; state: StepState; detail?: ReactNode }[] }) {
  const dot: Record<StepState, string> = {
    done: "bg-ok border-ok text-white",
    current: "bg-white border-brand-600 ring-4 ring-brand-100",
    upcoming: "bg-white border-line",
    blocked: "bg-bad border-bad text-white",
  };
  return (
    <ol className="relative">
      {steps.map((s, i) => (
        <li key={s.key} className="relative flex gap-3 pb-5 last:pb-0">
          {i < steps.length - 1 && <span className={cx("absolute left-[11px] top-6 h-[calc(100%-1rem)] w-0.5", s.state === "done" ? "bg-ok" : "bg-line")} aria-hidden="true" />}
          <span className={cx("relative z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold", dot[s.state])} aria-hidden="true">
            {s.state === "done" ? "✓" : s.state === "blocked" ? "!" : ""}
          </span>
          <div className="min-w-0">
            <p className={cx("font-semibold", s.state === "upcoming" && "text-muted")}>{s.label}</p>
            {s.detail && <div className="text-sm text-muted">{s.detail}</div>}
          </div>
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------- Page header

export function PageTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h1 className="text-2xl font-bold leading-tight text-ink text-balance">{title}</h1>
      {subtitle && <p className="mt-1 text-muted">{subtitle}</p>}
    </div>
  );
}

export { cx };
