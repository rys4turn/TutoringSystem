import { createPortal } from "react-dom";
import type { MouseEvent, ReactNode } from "react";

export function Modal({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  const handleBackdrop = (e: MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };
  return createPortal(
    <div className="fixed inset-0 z-50 modal-backdrop overflow-y-auto backdrop-in" onMouseDown={handleBackdrop}>
      <div className="flex min-h-full items-start justify-center p-4 sm:p-8">
        {children}
      </div>
    </div>,
    document.body
  );
}
