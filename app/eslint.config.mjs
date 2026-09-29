import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist/**', 'release/**', 'node_modules/**'] },
  js.configs.recommended,
  {
    // Plain JavaScript in this tree — the eslint config itself, the electron-builder hook,
    // the dev launcher and the fake CLI fixture — is not a member of any tsconfig, so it
    // gets the base rules without the type-aware parser. Adding it to a tsconfig purely to
    // satisfy the linter would put build scripts in the app's compilation graph.
    files: ['**/*.{js,mjs,cjs}'],
    languageOptions: { sourceType: 'module', ecmaVersion: 2023 },
    rules: { 'no-undef': 'off' },
  },
  {
    files: ['**/*.ts', '**/*.tsx'],
    extends: [...tseslint.configs.recommendedTypeChecked],
  },
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parserOptions: {
        // The three tsconfigs cover main/preload/cli, renderer, and tests. Type-aware
        // linting needs the project graph, not just the files.
        project: [
          './tsconfig.node.json',
          './tsconfig.preload.json',
          './tsconfig.web.json',
          './tsconfig.test.json',
        ],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // TypeScript already reports undefined identifiers, and `no-undef` has no notion of
      // the DOM/node lib split these projects use.
      'no-undef': 'off',
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
    },
  },
  {
    // shadcn/ui components are generated into our tree and edited as our code, but their
    // formatting and prop-spreading style is the kit's. Linting their *types* still
    // applies; the two rules below fight the generated form for no benefit.
    files: ['src/components/ui/**/*.tsx'],
    rules: {
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unnecessary-type-assertion': 'off',
    },
  },
  {
    files: ['test/**/*.ts', 'test/fixtures/**/*.mjs', 'scripts/**/*.mjs'],
    rules: {
      '@typescript-eslint/no-unsafe-member-access': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
    },
  },
);
