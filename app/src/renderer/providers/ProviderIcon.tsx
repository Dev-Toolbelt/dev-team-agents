import { Bot } from 'lucide-react';

import { cn } from '@/lib/utils';

import type { Provider } from '../../shared/providers.js';
import claudeLogo from '../logo/providers/claude.svg';
import codexLogo from '../logo/providers/codex.svg';
import opencodeLogo from '../logo/providers/opencode.svg';

// Keyed by `Provider` so a provider added to the CLI fails the typecheck here; looked up by
// `string` below because a feed can carry a provider this build has never heard of.
const PROVIDER_LABELS: Readonly<Record<Provider, string>> = {
  claude: 'Claude Code',
  codex: 'Codex',
  opencode: 'opencode',
};

// The long, vendor-qualified form, for the controls that choose a provider.
const PROVIDER_CHOICE_LABELS: Readonly<Record<Provider, string>> = {
  claude: 'Claude Code (Anthropic)',
  codex: 'Codex (OpenAI)',
  opencode: 'opencode',
};

/**
 * The providers' own marks, in their brand colours, taken from each vendor's official brand
 * kit (Anthropic, OpenAI, opencode) and shown only to name that vendor's product. Drawn as
 * `<img>` files rather than inline paths like `IntegrationLogo`: the marks are multi-colour,
 * and `currentColor` would erase the colour that makes them recognisable. Loaded as images,
 * the SVGs can never run script — re-audit them before inlining them as markup or components.
 * `invertInDark` is for a mark drawn in a near-black ink that would vanish on the dark
 * scheme's background.
 */
const PROVIDER_LOGOS: Readonly<Record<Provider, { readonly url: string; readonly invertInDark: boolean }>> = {
  claude: { url: claudeLogo, invertInDark: false },
  codex: { url: codexLogo, invertInDark: false },
  opencode: { url: opencodeLogo, invertInDark: true },
};

const SIZE_CLASS = { sm: 'size-3.5', md: 'size-4' } as const;

// A feed can carry any string, so own keys only: `constructor` must not find `Object.prototype`.
function lookup<T>(map: Readonly<Record<Provider, T>>, provider: string): T | undefined {
  return Object.hasOwn(map, provider) ? map[provider as Provider] : undefined;
}

export function providerLabel(provider: string): string {
  return lookup(PROVIDER_LABELS, provider) ?? provider;
}

export function providerChoiceLabel(provider: string): string {
  return lookup(PROVIDER_CHOICE_LABELS, provider) ?? provider;
}

/**
 * The provider's mark. Its name is always available as text: the icon is never the only cue.
 * `withLabel` prints the name beside it; `decorative` hides the mark from assistive tech when
 * the caller already prints the name itself. A provider without a mark falls back to a glyph.
 */
export function ProviderIcon({
  provider,
  withLabel = false,
  decorative = false,
  size = 'sm',
}: {
  provider: string;
  withLabel?: boolean;
  decorative?: boolean;
  size?: keyof typeof SIZE_CLASS;
}) {
  const logo = lookup(PROVIDER_LOGOS, provider);
  const label = providerLabel(provider);
  const hidden = withLabel || decorative;
  const sizeClass = `${SIZE_CLASS[size]} shrink-0`;
  return (
    <span className="inline-flex items-center gap-1" title={hidden ? undefined : label}>
      {logo !== undefined ? (
        <img
          src={logo.url}
          alt={hidden ? '' : label}
          draggable={false}
          className={cn(sizeClass, 'object-contain', logo.invertInDark && 'dark:invert')}
        />
      ) : (
        <Bot className={sizeClass} {...(hidden ? {} : { role: 'img', 'aria-label': label })} />
      )}
      {withLabel ? <span>{label}</span> : null}
    </span>
  );
}
