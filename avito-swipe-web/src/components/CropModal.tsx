import { useRef, useState } from 'react';
import { clamp, isVideoUrl } from '../lib/utils';
import type { CropRect } from '../api/types';
import { Modal } from './ui';

const RATIO = 9 / 16;

// Кадрирование 9:16: двигаем рамку по свободной оси, отдаём доли исходного кадра
export default function CropModal({ src, onApply, onClose }: { src: string; onApply: (r: CropRect) => void; onClose: () => void }) {
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null);
  const [pos, setPos] = useState(0.5); // 0..1 по свободной оси
  const box = useRef<HTMLDivElement>(null);
  const drag = useRef<{ start: number; pos: number } | null>(null);

  let fw = 1, fh = 1;
  let axis: 'x' | 'y' | 'none' = 'none';
  if (dims) {
    const r = dims.w / dims.h;
    if (r > RATIO) { fw = RATIO / r; axis = 'x'; }
    else if (r < RATIO) { fh = r / RATIO; axis = 'y'; }
  }
  const x = axis === 'x' ? pos * (1 - fw) : 0;
  const y = axis === 'y' ? pos * (1 - fh) : 0;

  const down = (e: React.PointerEvent) => {
    if (axis === 'none') return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { start: axis === 'x' ? e.clientX : e.clientY, pos };
  };
  const move = (e: React.PointerEvent) => {
    const d = drag.current;
    const el = box.current;
    if (!d || !el) return;
    const rect = el.getBoundingClientRect();
    const size = axis === 'x' ? rect.width : rect.height;
    const free = axis === 'x' ? 1 - fw : 1 - fh;
    const delta = ((axis === 'x' ? e.clientX : e.clientY) - d.start) / size;
    setPos(clamp(d.pos + delta / free, 0, 1));
  };

  return (
    <Modal title="Кадрирование 9:16" onClose={onClose} wide>
      <p className="modal-sub">Перетащите рамку, чтобы выбрать, какая часть кадра попадёт в рилс</p>
      <div className="crop-box" ref={box}>
        {isVideoUrl(src) ? (
          <video src={src} muted playsInline preload="metadata" onLoadedMetadata={(e) => setDims({ w: e.currentTarget.videoWidth, h: e.currentTarget.videoHeight })} />
        ) : (
          <img src={src} alt="" draggable={false} onLoad={(e) => setDims({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })} />
        )}
        {dims && (
          <div
            className={`crop-frame ${axis}`}
            style={{ left: `${x * 100}%`, top: `${y * 100}%`, width: `${fw * 100}%`, height: `${fh * 100}%` }}
            onPointerDown={down}
            onPointerMove={move}
            onPointerUp={() => (drag.current = null)}
          />
        )}
      </div>
      <div className="modal-actions">
        <button className="btn btn-primary" disabled={!dims} onClick={() => onApply({ x, y, width: fw, height: fh })}>Применить</button>
        <button className="btn btn-secondary" onClick={onClose}>Отмена</button>
      </div>
    </Modal>
  );
}
