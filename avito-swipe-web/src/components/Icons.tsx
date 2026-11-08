import type { SVGProps } from 'react';

type P = { size?: number } & Omit<SVGProps<SVGSVGElement>, 'width' | 'height'>;

const Svg = ({ size = 20, children, ...rest }: P) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    {...rest}
  >
    {children}
  </svg>
);

export const AvitoMark = ({ height = 28 }: { height?: number }) => (
  <svg width={(height * 26) / 28} height={height} viewBox="0 0 26 28" aria-hidden="true">
    <circle cx="7" cy="7" r="6" fill="#97cf26" />
    <circle cx="19" cy="9" r="5" fill="#04a5f5" />
    <circle cx="7" cy="21" r="5" fill="#965eeb" />
    <circle cx="19" cy="21" r="6" fill="#ff4053" />
  </svg>
);

export const GridIcon = ({ size = 20 }: P) => (
  <svg width={size} height={size} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    {[3, 10, 17].flatMap((x) => [3, 10, 17].map((y) => <circle key={`${x}${y}`} cx={x} cy={y} r="1.5" />))}
  </svg>
);
export const SearchIcon = (p: P) => (<Svg {...p}><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></Svg>);
export const PinIcon = (p: P) => (<Svg {...p} fill="currentColor" stroke="none"><path d="M12 2a7 7 0 00-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 00-7-7zm0 9.5A2.5 2.5 0 119.5 9 2.5 2.5 0 0112 11.5z" /></Svg>);
export const SwipeIcon = (p: P) => (<Svg {...p}><rect x="7" y="3" width="12" height="16" rx="3" /><path d="M4 7v11a3 3 0 003 3h9" /></Svg>);
export const HeartIcon = (p: P) => (<Svg {...p} fill="currentColor" stroke="none"><path d="M12 21s-8-5.2-8-11a4.5 4.5 0 018-2.8A4.5 4.5 0 0120 10c0 5.8-8 11-8 11z" /></Svg>);
export const HeartOutline = (p: P) => (<Svg {...p}><path d="M12 20s-7-4.6-7-10a4 4 0 017-2.4A4 4 0 0119 10c0 5.4-7 10-7 10z" /></Svg>);
export const GiftIcon = (p: P) => (
  <Svg {...p}>
    <rect x="3" y="8" width="18" height="4" rx="1" />
    <path d="M5 12v8h14v-8M12 8v12" />
    <path d="M12 8c-1.5 0-4.5-.5-4.5-3A2 2 0 0112 6a2 2 0 014.5-1c0 2.5-3 3-4.5 3z" />
  </Svg>
);
export const CloseIcon = (p: P) => (<Svg {...p}><path d="M6 6l12 12M18 6L6 18" /></Svg>);
export const CheckIcon = (p: P) => (<Svg {...p} strokeWidth={3}><path d="M5 12.5l4.5 4.5L19 7.5" /></Svg>);
export const ArrowUp = (p: P) => (<Svg {...p}><path d="M12 19V5M5 12l7-7 7 7" /></Svg>);
export const ArrowDown = (p: P) => (<Svg {...p}><path d="M12 5v14M5 12l7 7 7-7" /></Svg>);
export const ChevronRight = (p: P) => (<Svg {...p}><path d="M9 5l7 7-7 7" /></Svg>);
export const ShareIcon = (p: P) => (<Svg {...p}><path d="M12 15V4M7.5 8.5L12 4l4.5 4.5" /><path d="M5 13v6h14v-6" /></Svg>);
export const CopyIcon = (p: P) => (<Svg {...p}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V6a2 2 0 012-2h9" /></Svg>);
export const StarIcon = (p: P) => (<Svg {...p} fill="#ffc700" stroke="none"><path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5L2.5 9.4l6.6-.9z" /></Svg>);
export const SoundOff = (p: P) => (<Svg {...p}><path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" /><path d="M17 9l5 6M22 9l-5 6" /></Svg>);
export const SoundOn = (p: P) => (<Svg {...p}><path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" /><path d="M17 8.5a5 5 0 010 7M19.5 6a8.5 8.5 0 010 12" /></Svg>);
export const PlusIcon = (p: P) => (<Svg {...p}><path d="M12 5v14M5 12h14" /></Svg>);
export const HomeIcon = (p: P) => (<Svg {...p}><path d="M3 11l9-8 9 8" /><path d="M5 10v10h14V10" /></Svg>);
export const UserIcon = (p: P) => (<Svg {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.5-6 8-6s8 2 8 6" /></Svg>);
export const UploadIcon = (p: P) => (<Svg {...p}><path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v4h16v-4" /></Svg>);
export const VideoIcon = (p: P) => (<Svg {...p}><rect x="3" y="6" width="13" height="12" rx="2" /><path d="M16 10l5-3v10l-5-3z" /></Svg>);
export const ImageIcon = (p: P) => (<Svg {...p}><rect x="3" y="4" width="18" height="16" rx="3" /><circle cx="9" cy="10" r="2" /><path d="M21 16l-5-5-8 9" /></Svg>);
export const CropIcon = (p: P) => (<Svg {...p}><path d="M6 2v14a2 2 0 002 2h14M2 6h14a2 2 0 012 2v14" /></Svg>);
export const RetryIcon = (p: P) => (<Svg {...p}><path d="M20 11a8 8 0 10-2.3 5.7" /><path d="M20 4v7h-7" /></Svg>);
export const WifiOff = (p: P) => (<Svg {...p}><path d="M2 8.5a15 15 0 0120 0M5 12a10 10 0 0114 0M8.5 15.5a5 5 0 017 0" /><circle cx="12" cy="19" r="1" fill="currentColor" /><path d="M3 3l18 18" /></Svg>);
export const MessageIcon = (p: P) => (<Svg {...p}><path d="M4 5h16v11H9l-5 4z" /></Svg>);
