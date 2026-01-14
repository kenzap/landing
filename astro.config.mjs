// import sitemap from '@astrojs/sitemap';
import tailwind from '@astrojs/tailwind';
import icon from 'astro-icon';

import { defineConfig } from 'astro/config';

export default defineConfig({
    site: 'https://kenzap.com',
    integrations: [/*sitemap(),*/ tailwind(), icon()],
    i18n: {
        defaultLocale: 'en',
        locales: ['en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'sv', 'da', 'fi', 'pl', 'cs', 'sk', 'hu', 'ro', 'bg', 'hr', 'sl', 'et', 'lv', 'lt', 'el', 'id'],
        routing: {
            prefixDefaultLocale: false
        }
    },
    vite: {
        build: {
            cssCodeSplit: false,
            rollupOptions: {
                output: {
                    assetFileNames: 'assets/[name].[hash][extname]',
                }
            }
        }
    },
    build: {
        inlineStylesheets: 'auto'
    }
});