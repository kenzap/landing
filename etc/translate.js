// etc/translate.js
// Automated translation script using Claude API
// Usage: node etc/translate.js

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
// const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const ANTHROPIC_API_KEY = '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';
const SOURCE_LANG = 'en';
// const TARGET_LANGS = ['es', 'fr', 'de', 'it', 'pt', 'nl', 'sv', 'da', 'fi', 'pl', 'cs', 'sk', 'hu', 'ro', 'bg', 'hr', 'sl', 'et', 'lv', 'lt', 'el', 'id']; // Add more European languages as needed
const TARGET_LANGS = ['mt']; // Add more European languages as needed

// Language names for prompts
const LANGUAGE_NAMES = {
  de: 'German',
  fr: 'French',
  it: 'Italian',
  es: 'Spanish',
  pl: 'Polish',
  cs: 'Czech',
  sk: 'Slovak',
  nl: 'Dutch',
  pt: 'Portuguese',
  sv: 'Swedish',
  da: 'Danish',
  fi: 'Finnish',
  no: 'Norwegian',
  hu: 'Hungarian',
  ro: 'Romanian',
  bg: 'Bulgarian',
  hr: 'Croatian',
  sl: 'Slovenian',
  et: 'Estonian',
  lv: 'Latvian',
  lt: 'Lithuanian',
  el: 'Greek',
  id: 'Indonesian',
};

// Paths
const I18N_DIR = path.join(__dirname, '../src/i18n');
const SOURCE_FILE = path.join(I18N_DIR, `${SOURCE_LANG}.json`);

async function translateWithClaude(text, targetLang) {

  console.log(`Sending translation request to Claude for ${LANGUAGE_NAMES[targetLang]}...`);

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      // model: 'claude-haiku-4-5-20251001',
      max_tokens: 10000,
      messages: [
        {
          role: 'user',
          content: `You are a professional translator specializing in technical and business content for manufacturing ERP software.

Translate the following JSON content from English to ${LANGUAGE_NAMES[targetLang]}. 

IMPORTANT RULES:
1. Maintain the exact same JSON structure
2. Translate all text values, keeping keys unchanged
3. Use professional, industry-appropriate terminology for metal fabrication/manufacturing
4. Keep formatting consistent (capitalization, punctuation)
5. Preserve placeholders exactly as they are (e.g., "Your name" stays as a concept)
6. Be culturally appropriate for European business context
7. Maintain formality level appropriate for B2B software
8. Return ONLY valid JSON, no explanations or markdown
9. Use more natural local phrasing rather than literal translation

JSON to translate:
${text}`,
        },
      ],
    }),
  });

  console.log('Parsing response...');

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Translation API error: ${error}`);
  }

  const data = await response.json();
  const translatedText = data.content[0].text;

  console.log('Raw translated text:', translatedText);

  // Clean up markdown if present
  let cleaned = translatedText.trim();
  if (cleaned.startsWith('```json')) {
    cleaned = cleaned.replace(/^```json\n/, '').replace(/\n```$/, '');
  } else if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```\n/, '').replace(/\n```$/, '');
  }

  return JSON.parse(cleaned);
}

async function translateFile(sourcePath, targetLang) {
  console.log(`\n📝 Translating to ${LANGUAGE_NAMES[targetLang]} (${targetLang})...`);

  const sourceContent = fs.readFileSync(sourcePath, 'utf-8');
  const sourceJson = JSON.parse(sourceContent);

  try {
    const translatedJson = await translateWithClaude(
      JSON.stringify(sourceJson, null, 2),
      targetLang
    );

    const targetPath = path.join(I18N_DIR, `${targetLang}.json`);
    fs.writeFileSync(targetPath, JSON.stringify(translatedJson, null, 2), 'utf-8');

    console.log(`✅ Successfully translated to ${targetLang}`);
    return true;
  } catch (error) {
    console.error(`❌ Error translating to ${targetLang}:`, error.message);
    return false;
  }
}

async function main() {
  console.log('🌍 Kenzap Factory i18n Translation Script\n');

  // Check for API key
  if (!ANTHROPIC_API_KEY) {
    console.error('❌ Error: ANTHROPIC_API_KEY environment variable not set');
    console.log('\nPlease set your API key:');
    console.log('  export ANTHROPIC_API_KEY="your-api-key-here"');
    console.log('  node scripts/translate.js');
    process.exit(1);
  }

  // Check if source file exists
  if (!fs.existsSync(SOURCE_FILE)) {
    console.error(`❌ Error: Source file not found: ${SOURCE_FILE}`);
    process.exit(1);
  }

  console.log(`📖 Source file: ${SOURCE_FILE}`);
  console.log(`🎯 Target languages: ${TARGET_LANGS.join(', ')}\n`);

  // Create i18n directory if it doesn't exist
  if (!fs.existsSync(I18N_DIR)) {
    fs.mkdirSync(I18N_DIR, { recursive: true });
  }

  // Translate to each target language
  const results = [];
  for (const targetLang of TARGET_LANGS) {
    const success = await translateFile(SOURCE_FILE, targetLang);
    results.push({ lang: targetLang, success });

    // Add delay to respect rate limits
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  // Summary
  console.log('\n' + '='.repeat(50));
  console.log('📊 Translation Summary');
  console.log('='.repeat(50));

  const successful = results.filter(r => r.success).length;
  const failed = results.filter(r => !r.success).length;

  console.log(`✅ Successful: ${successful}/${TARGET_LANGS.length}`);
  if (failed > 0) {
    console.log(`❌ Failed: ${failed}/${TARGET_LANGS.length}`);
    const failedLangs = results.filter(r => !r.success).map(r => r.lang);
    console.log(`   Languages: ${failedLangs.join(', ')}`);
  }

  console.log('\n✨ Translation complete!\n');
}

main().catch(console.error);

// ============================================================================
// SETUP INSTRUCTIONS
// ============================================================================

/*
## Setup

1. Create the scripts directory:
   mkdir scripts

2. Save this file as scripts/translate.js

3. Update package.json to add translation command:
   {
     "scripts": {
       "translate": "node scripts/translate.js",
       "translate:templates": "node scripts/translate-simple.js"
     }
   }

4. Get your Anthropic API key from: https://console.anthropic.com/

5. Run the translation:
   export ANTHROPIC_API_KEY="your-api-key-here"
   npm run translate

## Customizing Languages

Edit the TARGET_LANGS array at the top of this file:
   const TARGET_LANGS = ['de', 'fr', 'it', 'es', 'pl', 'cs', 'nl'];

Add any European language codes you need:
- de: German
- fr: French  
- it: Italian
- es: Spanish
- pl: Polish
- cs: Czech
- nl: Dutch
- pt: Portuguese
- sv: Swedish
- da: Danish
- fi: Finnish
- no: Norwegian
- hu: Hungarian
- ro: Romanian
- bg: Bulgarian
- el: Greek

## Adding New Pages for Languages

After translation, create page directories:
   mkdir -p src/pages/{it,es,pl}

Then create index.astro in each:
   src/pages/it/index.astro
   src/pages/es/index.astro
   src/pages/pl/index.astro

Copy the structure from src/pages/de/index.astro and update:
   import it from '../../i18n/it.json';
   const translations = it;
   const lang = 'it';

## Update astro.config.mjs

Add new locales:
   i18n: {
     defaultLocale: 'en',
     locales: ['en', 'de', 'fr', 'it', 'es', 'pl'],
     routing: {
       prefixDefaultLocale: false
     }
   }

## Workflow

1. Edit src/i18n/en.json (your source of truth)
2. Run: npm run translate
3. Review generated translations
4. Create page files for new languages
5. Test: npm run dev
6. Deploy!

## Cost Estimation

Using Claude Sonnet 4:
- ~2000 tokens per translation (input + output)
- 7 languages × 2000 tokens = ~14,000 tokens
- Cost: ~$0.04 per run (very affordable!)

You can re-run anytime you update en.json.

## Alternative: Free/Manual Translation

If you prefer not to use API or want to review before auto-translating:

1. Create a simple template generator:
   // scripts/translate-simple.js
   import fs from 'fs';
   import path from 'path';
   import { fileURLToPath } from 'url';

   const __filename = fileURLToPath(import.meta.url);
   const __dirname = path.dirname(__filename);
   const I18N_DIR = path.join(__dirname, '../src/i18n');
   const SOURCE_FILE = path.join(I18N_DIR, 'en.json');
   const TARGET_LANGS = ['de', 'fr'];

   function createTemplates() {
     const sourceContent = fs.readFileSync(SOURCE_FILE, 'utf-8');
     TARGET_LANGS.forEach(lang => {
       const targetPath = path.join(I18N_DIR, `${lang}.json`);
       if (!fs.existsSync(targetPath)) {
         fs.writeFileSync(targetPath, sourceContent, 'utf-8');
         console.log(`✅ Created: ${lang}.json`);
       }
     });
   }

   createTemplates();

2. Run it: node scripts/translate-simple.js
3. Use ChatGPT/Claude to translate each file
4. Paste JSON, ask: "Translate to German, keep structure"
5. Copy/paste result into de.json

*/