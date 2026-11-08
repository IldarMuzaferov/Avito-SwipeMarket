import type { WishlistItem } from '../api/types';
import { formatPrice, gradientFor, openListing } from '../lib/utils';
import { CloseIcon } from './Icons';
import { useToast } from './Toast';

// Карточка вишлиста: свой (с крестиком) и чужой (по ссылке, «Уже купили»)
export default function WishCard({ item, mode, onRemove }: { item: WishlistItem; mode: 'own' | 'public'; onRemove?: (i: WishlistItem) => void }) {
  const toast = useToast();
  const gone = item.status !== 'available';
  const badge = item.status === 'sold' ? (mode === 'own' ? 'Продано' : 'Уже купили') : item.status === 'removed' ? 'Снято' : null;

  const open = async () => {
    if (gone) return;
    try {
      await openListing(item.listing_id);
    } catch {
      toast({ text: 'Не удалось открыть товар. Попробуйте ещё раз' });
    }
  };

  return (
    <article className={`wcard ${gone ? 'gone' : ''}`}>
      <div className="wcover" onClick={open} role="link" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && open()}
        style={{ background: item.cover_url ? `center/cover url(${item.cover_url})` : gradientFor(item.listing_id) }}>
        {!item.cover_url && <i className="blob" />}
        {badge && <span className="sold-badge">{badge}</span>}
      </div>
      {mode === 'own' && onRemove && (
        <button className="wremove" onClick={() => onRemove(item)} aria-label={`Убрать «${item.title}» из вишлиста`}>
          <CloseIcon size={16} />
        </button>
      )}
      <h3 onClick={open}>{item.title}</h3>
      <div className="wprice">{formatPrice(item.price)}</div>
      {item.city && <div className="wcity">{item.city}</div>}
    </article>
  );
}
