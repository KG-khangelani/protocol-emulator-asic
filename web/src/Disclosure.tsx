// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';

export function Disclosure({ label, kind, children }: { label: string; kind: string; children: ReactNode }) {
  const [open, setOpen] = useState(() => !matchMedia('(max-width: 760px)').matches);
  useEffect(() => {
    const media = matchMedia('(max-width: 760px)');
    const adapt = () => setOpen(!media.matches);
    media.addEventListener('change', adapt);
    return () => media.removeEventListener('change', adapt);
  }, []);
  return <details className={`responsive-disclosure ${kind}-disclosure`} open={open} onToggle={(event) => { if (event.target === event.currentTarget) setOpen(event.currentTarget.open); }}><summary>{label}</summary>{children}</details>;
}
