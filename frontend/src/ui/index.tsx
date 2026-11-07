// Shared UI primitives. Phase 0 owns this file; workstreams compose these and keep feature-specific components
// inside their own src/features/<name>/ folder.
import type { ButtonHTMLAttributes, ReactNode } from "react";

function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

// ---------------------------------------------------------------- Button

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

const buttonSizes: Record<ButtonSize, string> = { sm: "h-8 px-3 text-sm", md: "h-10 px-4 text-[0.95rem]", lg: "h-12 px-5 text-base" };
const buttonVariants: Record<ButtonVariant, string> = {
  primary: "bg-primary text-primary-foreground hover:bg-primary/90",
  secondary: "border border-border bg-card text-foreground hover:bg-secondary",
  ghost: "text-foreground hover:bg-secondary",
  danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
};

/** Button styling, also for router links that act as buttons. */
export function buttonClass(variant: ButtonVariant = "primary", size: ButtonSize = "md") {
  return cx("inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors", buttonSizes[size], buttonVariants[variant]);
}

export function Button({ variant = "primary", size = "md", full, className, ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize; full?: boolean }) {
  return <button className={cx(buttonClass(variant, size), "disabled:cursor-not-allowed disabled:opacity-50", full && "w-full", className)} {...rest} />;
}

// ---------------------------------------------------------------- Card

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("rounded-lg border border-border bg-card p-4 text-card-foreground", className)}>{children}</div>;
}

// ---------------------------------------------------------------- Chip (quick replies, filters)

export function Chip({ children, selected, onClick, disabled }: { children: ReactNode; selected?: boolean; onClick?: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-pressed={selected}
      className={cx("rounded-md border px-3 py-1.5 text-sm transition-colors disabled:opacity-50",
        selected ? "border-foreground bg-foreground text-background" : "border-border bg-card text-foreground hover:bg-secondary")}>
      {children}
    </button>
  );
}

// ---------------------------------------------------------------- Toggle (switch)

export function Toggle({ checked, onChange, label, disabled, id }: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean; id?: string }) {
  return (
    <button type="button" role="switch" id={id} aria-checked={checked} aria-label={label} disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cx("relative inline-flex h-6 w-10 shrink-0 items-center rounded-full transition-colors disabled:opacity-50",
        checked ? "bg-foreground" : "bg-input")}>
      <span className={cx("inline-block h-4 w-4 rounded-full bg-background shadow-xs transition-transform", checked ? "translate-x-5" : "translate-x-1")} />
    </button>
  );
}

// ---------------------------------------------------------------- Stepper (quantity)

export function Stepper({ value, onChange, min = 1, max = 99, label }: { value: number; onChange: (v: number) => void; min?: number; max?: number; label: string }) {
  const btn = "h-8 w-8 rounded-md border border-border bg-card text-base text-foreground hover:bg-secondary disabled:opacity-40";
  return (
    <div className="inline-flex items-center gap-1.5" role="group" aria-label={label}>
      <button type="button" className={btn} aria-label={`${label} −`} disabled={value <= min} onClick={() => onChange(Math.max(min, value - 1))}>−</button>
      <span className="tabular w-7 text-center font-medium" aria-live="polite">{value}</span>
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
  return <span className={cx("tabular", className)}>{formatInr(amount)}{suffix && <span className="text-muted-foreground text-[0.8em] font-normal">{suffix}</span>}</span>;
}

// ---------------------------------------------------------------- Pill (status badges)

export type Tone = "ok" | "warn" | "bad" | "info" | "neutral";
const pillTone: Record<Tone, string> = {
  ok: "border-success/30 text-success",
  warn: "border-warning/35 text-warning",
  bad: "border-destructive/30 text-destructive",
  info: "border-border text-foreground",
  neutral: "border-border text-muted-foreground",
};

export function Pill({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={cx("inline-flex items-center rounded-sm border bg-card px-1.5 py-px text-xs font-medium", pillTone[tone])}>{children}</span>;
}

// ---------------------------------------------------------------- Banner (notices, errors)

// A plain box; only the border and the title pick up the tone.
const ruleTone: Record<Tone, string> = {
  ok: "border-success/35",
  warn: "border-warning/40",
  bad: "border-destructive/35",
  info: "border-border",
  neutral: "border-border",
};
const titleTone: Record<Tone, string> = {
  ok: "text-success", warn: "text-warning", bad: "text-destructive", info: "text-foreground", neutral: "text-foreground",
};

export function Banner({ tone = "info", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <div role={tone === "bad" ? "alert" : "status"}
      className={cx("rounded-md border bg-card px-3.5 py-2.5 text-sm", ruleTone[tone],
        !title && tone === "bad" && "text-destructive")}>
      {title && <p className={cx("font-medium", titleTone[tone])}>{title}</p>}
      <div className={cx(title && "mt-0.5 text-muted-foreground")}>{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------- Spinner

export function Spinner({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-muted-foreground" role="status">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-[1.5px] border-border border-t-foreground" aria-hidden="true" />
      <span className="text-sm">{label}</span>
    </span>
  );
}

// ---------------------------------------------------------------- Timeline (tracker)

export type StepState = "done" | "current" | "upcoming" | "blocked";

export function Timeline({ steps }: { steps: { key: string; label: string; state: StepState; detail?: ReactNode }[] }) {
  const dot: Record<StepState, string> = {
    done: "bg-foreground border-foreground",
    current: "bg-background border-primary border-[3px]",
    upcoming: "bg-background border-border",
    blocked: "bg-destructive border-destructive",
  };
  return (
    <ol className="relative">
      {steps.map((s, i) => (
        <li key={s.key} className="relative flex gap-3 pb-5 last:pb-0">
          {i < steps.length - 1 && <span className={cx("absolute left-[5px] top-4 h-[calc(100%-0.75rem)] w-px", s.state === "done" ? "bg-foreground/60" : "bg-border")} aria-hidden="true" />}
          <span className={cx("relative z-10 mt-1.5 h-[11px] w-[11px] shrink-0 rounded-full border-2", dot[s.state])} aria-hidden="true" />
          <div className="min-w-0">
            <p className={cx("font-medium", s.state === "upcoming" && "text-muted-foreground")}>
              {s.label}
            </p>
            {s.detail && <div className="text-sm text-muted-foreground">{s.detail}</div>}
          </div>
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------- Page header

export function PageTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-5">
      <h1 className="text-[1.6rem] font-semibold leading-tight tracking-tight text-foreground text-balance">{title}</h1>
      {subtitle && <p className="mt-1.5 text-muted-foreground">{subtitle}</p>}
    </div>
  );
}

export { cx };
