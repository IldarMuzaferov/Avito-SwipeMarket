import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';

type ToastData = { id: number; text: string; actionLabel?: string; onAction?: () => void };
type ToastFn = (t: { text: string; actionLabel?: string; onAction?: () => void; duration?: number }) => void;

const Ctx = createContext<ToastFn>(() => {});
export const useToast = () => useContext(Ctx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastData | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const seq = useRef(0);

  const show: ToastFn = useCallback(({ duration = 4500, ...t }) => {
    window.clearTimeout(timer.current);
    setToast({ id: ++seq.current, ...t });
    timer.current = window.setTimeout(() => setToast(null), duration);
  }, []);

  return (
    <Ctx.Provider value={show}>
      {children}
      {toast && (
        <div className="snackbar" role="status" key={toast.id}>
          <span>{toast.text}</span>
          {toast.actionLabel && (
            <button
              onClick={() => {
                toast.onAction?.();
                setToast(null);
              }}
            >
              {toast.actionLabel}
            </button>
          )}
        </div>
      )}
    </Ctx.Provider>
  );
}
