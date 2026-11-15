import { create } from 'zustand';
import type { CountryCode } from './lib/data';

export interface HoverInfo {
  iso: string;
  name: string;
  country: CountryCode;
}

interface State {
  /** Months on the shared time axis (from series ym). */
  yms: string[];
  ymIndex: number;
  /** True when the last month change came from the user (drives count-up animations). */
  userChange: boolean;
  playing: boolean;
  speed: 1 | 2;
  country: CountryCode;
  selected: string | null;
  hover: HoverInfo | null;
  introDone: boolean;
  reducedMotion: boolean;

  setYms: (yms: string[], start: number) => void;
  setYmIndex: (i: number, user?: boolean) => void;
  setPlaying: (p: boolean) => void;
  setSpeed: (s: 1 | 2) => void;
  setCountry: (c: CountryCode) => void;
  setSelected: (iso: string | null) => void;
  setHover: (h: HoverInfo | null) => void;
  setIntroDone: () => void;
}

const reduced =
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

export const useStore = create<State>((set, get) => ({
  yms: [],
  ymIndex: 0,
  userChange: false,
  playing: false,
  speed: 1,
  country: 'KAZ',
  selected: null,
  hover: null,
  introDone: false,
  reducedMotion: !!reduced,

  setYms: (yms, start) => set({ yms, ymIndex: start }),
  setYmIndex: (i, user = true) => {
    const n = get().yms.length;
    if (!n) return;
    const ymIndex = Math.max(0, Math.min(n - 1, i));
    if (ymIndex !== get().ymIndex) set({ ymIndex, userChange: user });
  },
  setPlaying: (playing) => set({ playing }),
  setSpeed: (speed) => set({ speed }),
  setCountry: (country) => set({ country }),
  setSelected: (selected) => set({ selected }),
  setHover: (hover) => set({ hover }),
  setIntroDone: () => set({ introDone: true }),
}));
