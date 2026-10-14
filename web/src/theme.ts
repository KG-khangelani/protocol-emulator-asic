// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from 'react';
export type Theme = 'system' | 'light' | 'dark';
const key = 'protocol-atlas-theme';
const readTheme = (): Theme => {
  try {
    const stored = localStorage.getItem(key);
    return stored === 'light' || stored === 'dark' ? stored : 'system';
  } catch { return 'system'; }
};
export function useTheme() {
  const [choice, setChoice] = useState<Theme>(readTheme);
  useEffect(() => {
    const preference = matchMedia('(prefers-color-scheme: dark)');
    const apply = () => {
      const resolved = choice === 'system' ? (preference.matches ? 'dark' : 'light') : choice;
      document.documentElement.dataset.theme = resolved;
      document.documentElement.style.colorScheme = resolved;
    };
    apply();
    preference.addEventListener('change', apply);
    return () => preference.removeEventListener('change', apply);
  }, [choice]);
  const choose = (next: Theme) => {
    setChoice(next);
    try { if (next === 'system') localStorage.removeItem(key); else localStorage.setItem(key, next); } catch { /* The current session still works without storage. */ }
  };
  return [choice, choose] as const;
}
