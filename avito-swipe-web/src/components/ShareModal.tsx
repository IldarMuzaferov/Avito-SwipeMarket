import { useState } from 'react';
import { api } from '../api';
import type { ShareState } from '../api/types';
import { copyText } from '../lib/utils';
import { CheckIcon, CopyIcon } from './Icons';
import { useToast } from './Toast';
import { ConfirmDialog, Modal, Toggle } from './ui';

export default function ShareModal({ share, onChange, onClose }: { share: ShareState; onChange: (s: ShareState) => void; onClose: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [copied, setCopied] = useState(false);

  const set = async (enabled: boolean) => {
    setBusy(true);
    try {
      let s = await api.setShare(enabled);
      if (enabled && !s?.url) s = await api.share(); // на случай, если PUT вернул только enabled
      onChange({ enabled: s?.enabled ?? enabled, url: s?.url ?? null });
    } catch (e: any) {
      toast({ text: e?.message ?? 'Не удалось изменить доступ' });
    } finally {
      setBusy(false);
      setConfirm(false);
    }
  };

  const url = share.url ?? '';
  const text = 'Мой вишлист на Авито';
  const enc = encodeURIComponent;
  const targets = [
    { name: 'Telegram', letter: 'T', color: '#2aabee', href: `https://t.me/share/url?url=${enc(url)}&text=${enc(text)}` },
    { name: 'WhatsApp', letter: 'W', color: '#25d366', href: `https://wa.me/?text=${enc(`${text} ${url}`)}` },
    { name: 'VK', letter: 'V', color: '#3a6ee8', href: `https://vk.com/share.php?url=${enc(url)}&title=${enc(text)}` },
    { name: 'Почта', letter: 'П', color: '#9a9aa5', href: `mailto:?subject=${enc(text)}&body=${enc(url)}` },
  ];

  const copy = async () => {
    if (await copyText(url)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } else toast({ text: 'Не удалось скопировать ссылку' });
  };

  return (
    <>
      <Modal title="Поделиться вишлистом" onClose={onClose}>
        <p className="modal-sub">Друзья увидят ваши желания и смогут купить подарок</p>
        <div className="row-between">
          <b>Доступ по ссылке</b>
          <Toggle checked={share.enabled} disabled={busy} label="Доступ по ссылке" onChange={(v) => (v ? set(true) : setConfirm(true))} />
        </div>
        {share.enabled && url ? (
          <>
            <div className="link-box">
              <span>{url.replace(/^https?:\/\//, '')}</span>
              <button className="btn btn-primary btn-sm" onClick={copy}>
                {copied ? <><CheckIcon size={16} /> Скопировано</> : <><CopyIcon size={16} /> Копировать</>}
              </button>
            </div>
            <p className="modal-label">Отправить через</p>
            <div className="share-targets">
              {targets.map((t) => (
                <a key={t.name} href={t.href} target="_blank" rel="noopener noreferrer">
                  <i style={{ background: t.color }}>{t.letter}</i>
                  <span>{t.name}</span>
                </a>
              ))}
            </div>
          </>
        ) : (
          <p className="off-note">Доступ отключён: друзья не смогут открыть вишлист по ссылке. Включите переключатель, чтобы поделиться.</p>
        )}
      </Modal>
      {confirm && (
        <ConfirmDialog
          title="Отключить доступ?"
          text="Друзья больше не смогут открыть ваш вишлист по этой ссылке."
          confirmLabel="Отключить"
          danger
          onConfirm={() => set(false)}
          onCancel={() => setConfirm(false)}
        />
      )}
    </>
  );
}
