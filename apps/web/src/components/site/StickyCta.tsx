"use client";

import { useEffect, useState, type ReactNode } from "react";

/** Mobile sticky primary action, shown once the hero has scrolled away (design: LandingMobile). */
export function StickyCta({ watchId, children }: { watchId: string; children: ReactNode }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const el = document.getElementById(watchId);
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setShow(!e?.isIntersecting), { threshold: 0 });
    io.observe(el);
    return () => io.disconnect();
  }, [watchId]);
  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper/95 px-4 pt-3 pb-[max(12px,env(safe-area-inset-bottom))] shadow-[0_-8px_24px_rgba(22,32,74,0.10)] transition-transform md:hidden ${show ? "translate-y-0" : "translate-y-full"}`}
      aria-hidden={!show}
    >
      {children}
    </div>
  );
}
