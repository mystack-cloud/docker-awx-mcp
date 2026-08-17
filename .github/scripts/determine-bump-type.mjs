#!/usr/bin/env node

/**
 * Infer semver bump type from a PR or commit title.
 *
 * Conventions (case-insensitive):
 * - major: [major], "breaking change" / "breaking:", type! (e.g. feat!), or BREAKING CHANGE
 * - minor: [minor], feat/feature prefixes
 * - patch: [patch], fix/perf/refactor/chore/docs/etc., or anything else
 */

const title = process.argv[2] ?? "";

if (/\[skip release]|\[no release]/i.test(title)) {
  console.log("skip");
  process.exit(0);
}

const normalized = title.trim();

if (
  /\[major\]/i.test(normalized) ||
  /(?<![-\w])breaking(?: change|:)/i.test(normalized) ||
  /^(feat|fix|chore|refactor|perf|docs|style|test|build|ci)!:/i.test(normalized)
) {
  console.log("major");
  process.exit(0);
}

if (
  /\[minor\]/i.test(normalized) ||
  /^(feat|feature)([(:\s])/i.test(normalized)
) {
  console.log("minor");
  process.exit(0);
}

if (
  /\[patch]/i.test(normalized) ||
  /^(fix|perf|refactor|chore|docs|style|test|build|ci|patch)([(:\s])/i.test(normalized)
) {
  console.log("patch");
  process.exit(0);
}

console.log("patch");
