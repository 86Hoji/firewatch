// Cursor position for the map tooltip, outside React so mousemove never re-renders the tree.
type Fn = (x: number, y: number) => void;
const subs = new Set<Fn>();
export const pointer = {
  x: 0,
  y: 0,
  emit(x: number, y: number) {
    this.x = x;
    this.y = y;
    subs.forEach((f) => f(x, y));
  },
  subscribe(f: Fn) {
    subs.add(f);
    return () => {
      subs.delete(f);
    };
  },
};
