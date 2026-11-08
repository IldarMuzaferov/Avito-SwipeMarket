import { useEffect, type ReactNode } from 'react';
import { CloseIcon, RetryIcon, WifiOff } from './Icons';

export function Toggle({ checked, onChange, disabled, label }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean; label?: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className={`toggle ${checked ? 'on' : ''}`}
      onClick={() => onChange(!checked)}
    >
      <span />
    </button>
  );
}

export function Modal({ title, onClose, children, wide, hideClose }: { title?: ReactNode; onClose: () => void; children: ReactNode; wide?: boolean; hideClose?: boolean }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true">
        <div className="modal-head">
          {title && <h2>{title}</h2>}
          {!hideClose && (
            <button className="icon-btn ghost" onClick={onClose} aria-label="Закрыть">
              <CloseIcon size={22} />
            </button>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}

export function ConfirmDialog(p: { title: string; text: string; confirmLabel: string; danger?: boolean; onConfirm: () => void; onCancel: () => void }) {
  return (
    <Modal onClose={p.onCancel} hideClose>
      <div className="confirm">
        <h2>{p.title}</h2>
        <p>{p.text}</p>
        <div className="confirm-actions">
          <button className={`btn ${p.danger ? 'btn-danger' : 'btn-primary'}`} onClick={p.onConfirm}>{p.confirmLabel}</button>
          <button className="btn btn-secondary" onClick={p.onCancel}>Отмена</button>
        </div>
      </div>
    </Modal>
  );
}

export function EmptyState(p: { icon?: ReactNode; title: string; text?: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <div className="empty-icon">{p.icon}</div>
      <h2>{p.title}</h2>
      {p.text && <p>{p.text}</p>}
      {p.children && <div className="empty-actions">{p.children}</div>}
    </div>
  );
}

export function NetworkError({ onRetry, text }: { onRetry: () => void; text?: string }) {
  return (
    <EmptyState icon={<WifiOff size={40} />} title="Нет соединения" text={text ?? 'Проверьте интернет и попробуйте снова'}>
      <button className="btn btn-primary" onClick={onRetry}><RetryIcon size={18} /> Повторить</button>
    </EmptyState>
  );
}

export function Spinner() {
  return <div className="spinner" role="progressbar" aria-label="Загрузка" />;
}

export function Avatar({ name, url, size = 28 }: { name: string; url?: string | null; size?: number }) {
  const style = { width: size, height: size, fontSize: size * 0.45 };
  return url ? (
    <img className="avatar" src={url} alt="" style={style} />
  ) : (
    <span className="avatar" style={style}>{name.trim().charAt(0).toUpperCase()}</span>
  );
}
