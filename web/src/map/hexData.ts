// Year files for (country, resolution), parsed in a worker and cached.
import type { CountryCode } from '../lib/data';
import { boundariesUrl, hexUrl } from '../lib/data';
import type { HexRequest, HexYear } from './hexWorker';

let worker: Worker | null = null;
let nextId = 1;
const pending = new Map<number, { resolve: (v: HexYear) => void; reject: (e: Error) => void }>();
const cache = new Map<string, Promise<HexYear>>();

function getWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL('./hexWorker.ts', import.meta.url), { type: 'module' });
    worker.onmessage = (e: MessageEvent<HexYear & { error?: string }>) => {
      const p = pending.get(e.data.id);
      if (!p) return;
      pending.delete(e.data.id);
      if (e.data.error) p.reject(new Error(e.data.error));
      else p.resolve(e.data);
    };
  }
  return worker;
}

export function loadHexYear(cc: CountryCode, res: string, year: number): Promise<HexYear> {
  const key = `${cc}/${res}/${year}`;
  let p = cache.get(key);
  if (!p) {
    p = new Promise<HexYear>((resolve, reject) => {
      const id = nextId++;
      pending.set(id, { resolve, reject });
      const req: HexRequest = { id, url: hexUrl(cc, res, year), boundariesUrl: boundariesUrl(cc) };
      getWorker().postMessage(req);
    });
    p.catch(() => cache.delete(key));
    cache.set(key, p);
  }
  return p;
}

export function peekHexYear(cc: CountryCode, res: string, year: number): boolean {
  return cache.has(`${cc}/${res}/${year}`);
}
