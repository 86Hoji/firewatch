// Camera changes, published outside React (starfield parallax).
type Cam = { bearing: number; lng: number; zoom: number };
type Fn = (c: Cam) => void;
const subs = new Set<Fn>();
export const mapEvents = {
  emit(c: Cam) {
    subs.forEach((f) => f(c));
  },
  subscribe(f: Fn) {
    subs.add(f);
    return () => {
      subs.delete(f);
    };
  },
};
