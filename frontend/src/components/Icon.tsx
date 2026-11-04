import type { SVGProps } from 'react';

const paths: Record<string, React.ReactNode> = {
  arrow: <><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></>,
  arrowUp: <><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></>,
  store: <><path d="M3 10h18l-2-6H5l-2 6Z"/><path d="M5 10v10h14V10M9 20v-6h6v6"/><path d="M3 10c0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0 0 2 3 2 3 0"/></>,
  briefcase: <><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2"/></>,
  locations: <><rect x="3" y="4" width="8" height="7" rx="1.5"/><rect x="13" y="4" width="8" height="7" rx="1.5"/><rect x="3" y="13" width="8" height="7" rx="1.5"/><rect x="13" y="13" width="8" height="7" rx="1.5"/></>,
  factory: <><path d="M3 20V9l6 3V8l6 4V5h6v15H3Z"/><path d="M7 16h2m3 0h2m3 0h2"/></>,
  wifi: <><path d="M5 9a11 11 0 0 1 14 0M8 12a6.5 6.5 0 0 1 8 0m-5 7h.01"/><path d="M3 6a15 15 0 0 1 18 0"/></>,
  mobile: <><rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/></>,
  message: <><path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5 9 9 0 0 1-4-.9L3 21l1.9-5.5a9 9 0 0 1-.9-4A8.5 8.5 0 0 1 12.5 3h.5a8.5 8.5 0 0 1 8 8v.5Z"/><path d="M8 12h.01M12 12h.01M16 12h.01"/></>,
  cloud: <><path d="M20 16.2A4.5 4.5 0 0 0 18 7.5a6 6 0 0 0-11.5 1A4 4 0 0 0 7 16.5h13"/><path d="m9 20 3 3 3-3"/></>,
  shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
  receipt: <><path d="M4 2h16v20l-4-2-4 2-4-2-4 2V2Z"/><path d="M8 7h8M8 11h8M8 15h5"/></>,
  camera: <><path d="M14 5h-4L8 8H4a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-4l-2-3Z"/><circle cx="12" cy="13" r="3"/></>,
  pin: <><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  close: <><path d="m18 6-12 12M6 6l12 12"/></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
  spark: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-2-5.8L4 11l6-2.2L12 3Z"/><path d="m19 14 1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2Z"/></>,
  lock: <><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 1 1 8 0v3"/></>,
};

export type IconName = keyof typeof paths;

export function Icon({ name, size = 20, ...props }: SVGProps<SVGSVGElement> & { name: IconName; size?: number }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" {...props}>{paths[name]}</svg>;
}
