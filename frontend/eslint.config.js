// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import react from 'eslint-plugin-react'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'
import tailwind from 'eslint-plugin-tailwindcss'
import prettier from 'eslint-config-prettier'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      react.configs.flat.recommended,
      react.configs.flat['jsx-runtime'],
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      tailwind.configs['flat/recommended'],
      prettier,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      tailwindcss: tailwind,
      react,
    },
    settings: {
      react: {
        version: 'detect',
      },
      tailwindcss: {
        callees: ['clsx', 'ctl'],
        config: 'tailwind.config.cjs',
      },
    },
    rules: {
      // Disable custom classname warnings for files using custom CSS classes
      'tailwindcss/no-custom-classname': 'off',
    },
  },
])
