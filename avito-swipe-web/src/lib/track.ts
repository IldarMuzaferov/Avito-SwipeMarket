import { api } from '../api';
import type { TrackEvent } from '../api/types';

// Пакетная отправка событий для рекомендаций (POST /events). Ошибки не показываем.
let queue: TrackEvent[] = [];

export function track(type: TrackEvent['type'], reelId: string, valueMs?: number) {
  queue.push({ type, reel_id: reelId, value_ms: valueMs, ts: new Date().toISOString() });
  if (queue.length >= 20) flush();
}

export function flush() {
  if (!queue.length) return;
  const batch = queue;
  queue = [];
  api.events(batch).catch(() => {
    /* события не критичны */
  });
}

setInterval(flush, 5000);
window.addEventListener('pagehide', flush);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') flush();
});
