/**
 * Printed after every artifact. The one job is to make sure nobody walks away from a
 * build thinking they have something signed, or publishes it outside the one channel
 * an unsigned build is allowed on.
 */
module.exports = function afterAllArtifactBuild(context) {
  const bar = '='.repeat(78);
  process.stderr.write(
    [
      '',
      bar,
      'UNSIGNED, UNNOTARISED BUILD — DIRECT-DOWNLOAD BETA ONLY',
      '',
      'No Apple Developer ID or Authenticode certificate exists for this project, so',
      'nothing here has been through codesign, notarytool or signtool. ADR-0027 allows',
      'publishing it only as a beta GitHub Release built by `npm run dist:beta` from an',
      'app-v<version> tag, next to release/SHA256SUMS.txt, with the download-page text in',
      'app/README.md. Never to the Homebrew cask or winget: `brew audit --cask` would',
      'reject it, and both manifests are still placeholders.',
      '',
      'Artifacts: ' + (context.artifactPaths || []).join(', '),
      bar,
      '',
    ].join('\n'),
  );
  return [];
};
