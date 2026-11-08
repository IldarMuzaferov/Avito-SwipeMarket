import { useEffect, useState } from 'react';
import { api, asList } from '../api';
import type { PromotionPlan } from '../api/types';
import { formatPrice, plural } from '../lib/utils';
import { useToast } from './Toast';
import { Modal, Spinner } from './ui';

export default function PromotionModal({ reelId, onClose }: { reelId: string; onClose: (bought: boolean) => void }) {
  const toast = useToast();
  const [plans, setPlans] = useState<PromotionPlan[] | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.plans().then((r) => {
      const list = asList(r);
      setPlans(list);
      setSel((list.find((p) => p.is_best_value) ?? list[0])?.id ?? null);
    }).catch(() => setFailed(true));
  }, []);

  const chosen = plans?.find((p) => p.id === sel);

  const buy = async () => {
    if (!chosen) return;
    setBusy(true);
    try {
      const promo = await api.buyPromotion(reelId, chosen.id);
      try {
        await api.mockPay(promo.promotion_id); // демо-оплата
        toast({ text: 'Продвижение запущено' });
        onClose(true);
      } catch {
        if (promo.payment_url) window.open(promo.payment_url, '_blank', 'noopener');
        else toast({ text: 'Не удалось оплатить продвижение' });
        setBusy(false);
      }
    } catch (e: any) {
      toast({ text: e?.message ?? 'Не удалось купить продвижение' });
      setBusy(false);
    }
  };

  return (
    <Modal title="Хотите, чтобы рилс увидело больше людей?" onClose={() => onClose(false)} wide>
      {failed && <p className="off-note">Не удалось загрузить тарифы. Продвижение можно купить позже в «Моих объявлениях».</p>}
      {!plans && !failed && <div className="center-pad"><Spinner /></div>}
      {plans && (
        <>
          <div className="plans">
            {plans.map((p) => (
              <button key={p.id} className={`plan ${p.id === sel ? 'on' : ''}`} onClick={() => setSel(p.id)}>
                <b>{p.days} {plural(p.days, ['день', 'дня', 'дней'])}{p.is_best_value && <em>Выгодно</em>}</b>
                <small>около {new Intl.NumberFormat('ru-RU').format(p.estimated_reach)} показов</small>
                <strong>{formatPrice(p.price)}</strong>
              </button>
            ))}
          </div>
          <p className="modal-label">Цены и охваты примерные</p>
        </>
      )}
      <div className="modal-actions">
        <button className="btn btn-primary" disabled={!chosen || busy} onClick={buy}>
          {chosen ? `Продвинуть за ${formatPrice(chosen.price)}` : 'Продвинуть'}
        </button>
        <button className="link-btn inline" onClick={() => onClose(false)}>Не сейчас</button>
      </div>
    </Modal>
  );
}
