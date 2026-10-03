#!/usr/bin/env node
/**
 * Flip `CODE_SIGNED` to true in the CHECKED-OUT copy of app/src/main/build-info.ts.
 *
 * Run by the release workflow only on a runner that holds the signing credentials for the
 * platform it builds, and before that build. Nothing is committed: the repository keeps
 * `CODE_SIGNED = false`, and a build made without credentials never runs this. It fails
 * loudly when the line is not exactly as expected, so a refactor of build-info.ts cannot
 * make it a silent no-op that leaves a signed build calling itself unsigned (or the
 * reverse).
 *
 * The flag is only ever a CLAIM; the workflow still verifies the produced artifact
 * (codesign, stapler, spctl, Authenticode) and fails the job when the claim is false.
 *
 * Usage: node stamp-code-signed.cjs [path/to/build-info.ts]
 */
const { readFileSync, writeFileSync } = require('node:fs');

const target = process.argv[2] || 'app/src/main/build-info.ts';
const source = readFileSync(target, 'utf8');
const pattern = /^export const CODE_SIGNED = false;$/gm;
const matches = source.match(pattern) || [];
if (matches.length !== 1) {
  process.stderr.write(
    `stamp-code-signed: expected exactly one "export const CODE_SIGNED = false;" in ${target}, found ${matches.length}\n`,
  );
  process.exit(1);
}
writeFileSync(target, source.replace(pattern, 'export const CODE_SIGNED = true;'));
process.stdout.write(`stamp-code-signed: ${target} now says CODE_SIGNED = true (working copy only)\n`);
