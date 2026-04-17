type Messages = Record<string, any>;

const localeModules = import.meta.glob('./*.json', { eager: true, import: 'default' }) as Record<string, Messages>;

const localeDirectory = {
  en: { label: 'English', code: 'EN' },
  es: { label: 'Español', code: 'ES' },
  de: { label: 'Deutsch', code: 'DE' },
  fr: { label: 'Français', code: 'FR' },
  it: { label: 'Italiano', code: 'IT' },
  pt: { label: 'Português', code: 'PT' },
  nl: { label: 'Nederlands', code: 'NL' },
  sv: { label: 'Svenska', code: 'SV' },
  da: { label: 'Dansk', code: 'DA' },
  fi: { label: 'Suomi', code: 'FI' },
  pl: { label: 'Polski', code: 'PL' },
  cs: { label: 'Čeština', code: 'CS' },
  sk: { label: 'Slovenčina', code: 'SK' },
  hu: { label: 'Magyar', code: 'HU' },
  ro: { label: 'Română', code: 'RO' },
  hr: { label: 'Hrvatski', code: 'HR' },
  sl: { label: 'Slovenščina', code: 'SL' },
  bg: { label: 'Български', code: 'BG' },
  et: { label: 'Eesti', code: 'ET' },
  lv: { label: 'Latviešu', code: 'LV' },
  lt: { label: 'Lietuvių', code: 'LT' },
  el: { label: 'Ελληνικά', code: 'EL' },
  id: { label: 'Bahasa Indonesia', code: 'ID' },
} as const;

type LocaleKey = keyof typeof localeDirectory;
type PageKind = 'factory' | 'nesting';

const localeGroups = [
  {
    label: 'Western Europe',
    langs: ['en', 'de', 'fr', 'es', 'it', 'pt', 'nl'],
  },
  {
    label: 'Northern Europe',
    langs: ['sv', 'da', 'fi'],
  },
  {
    label: 'Central & Eastern Europe',
    langs: ['pl', 'cs', 'sk', 'hu', 'ro', 'hr', 'sl', 'bg'],
  },
  {
    label: 'Baltic',
    langs: ['et', 'lv', 'lt'],
  },
  {
    label: 'Other',
    langs: ['el', 'id'],
  },
] as const;

function deepMerge<T>(base: T, override: Partial<T>): T {
  if (Array.isArray(base) || Array.isArray(override)) {
    return (override ?? base) as T;
  }

  if (
    typeof base === 'object' &&
    base !== null &&
    typeof override === 'object' &&
    override !== null
  ) {
    const result: Record<string, any> = { ...(base as Record<string, any>) };

    for (const [key, value] of Object.entries(override)) {
      result[key] = key in result ? deepMerge(result[key], value) : value;
    }

    return result as T;
  }

  return (override ?? base) as T;
}

function routeFor(lang: string, page: PageKind) {
  if (page === 'factory') {
    return lang === 'en' ? '/' : `/${lang}`;
  }

  return lang === 'en' ? '/nesting' : `/${lang}/nesting`;
}

function normalizeFactoryMessages(messages: Messages, lang: string) {
  const normalized = structuredClone(messages);
  const nestingHref = routeFor(lang, 'nesting');

  normalized.factoryHomepage.nav.nestingHref = nestingHref;
  normalized.factoryHomepage.nesting.href = nestingHref;
  normalized.factoryHomepage.footer.nestingHref = nestingHref;

  return normalized;
}

function normalizeNestingMessages(messages: Messages, lang: string) {
  const normalized = structuredClone(messages);

  if (normalized.nestingHomepage?.hero?.secondaryCtaHref) {
    normalized.nestingHomepage.hero.secondaryCtaHref =
      lang === 'en' ? '/#case-study' : `/${lang}#case-study`;
  }

  return normalized;
}

export function getAvailableLocales() {
  const langs = Object.keys(localeModules)
    .map((path) => path.match(/\/([a-z-]+)\.json$/)?.[1])
    .filter((lang): lang is LocaleKey => Boolean(lang && lang in localeDirectory));

  return langs
    .sort((a, b) => (a === 'en' ? -1 : b === 'en' ? 1 : a.localeCompare(b)))
    .map((lang) => ({
      lang,
      label: localeDirectory[lang].label,
      code: localeDirectory[lang].code,
      factoryHref: routeFor(lang, 'factory'),
      nestingHref: routeFor(lang, 'nesting'),
    }));
}

export function getLocaleGroups(page: PageKind) {
  const locales = getAvailableLocales();
  const hrefKey = page === 'factory' ? 'factoryHref' : 'nestingHref';

  return localeGroups
    .map((group) => ({
      label: group.label,
      items: group.langs
        .map((lang) => locales.find((locale) => locale.lang === lang))
        .filter(Boolean)
        .map((locale) => ({
          lang: locale!.lang,
          label: locale!.label,
          code: locale!.code,
          href: locale![hrefKey],
        })),
    }))
    .filter((group) => group.items.length > 0);
}

export function getLocalizedMessages(lang: string) {
  const english = localeModules['./en.json'];
  const localized = localeModules[`./${lang}.json`] ?? english;
  const merged = deepMerge(english, localized);

  return {
    factoryHomepage: normalizeFactoryMessages(merged, lang).factoryHomepage,
    nestingHomepage: normalizeNestingMessages(merged, lang).nestingHomepage,
  };
}

export function getStaticLocaleParams() {
  return getAvailableLocales()
    .filter((locale) => locale.lang !== 'en')
    .map((locale) => ({ params: { lang: locale.lang } }));
}
