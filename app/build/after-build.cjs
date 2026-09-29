/**
 * Printed after every artifact. The one job is to make sure nobody walks away from a
 * build thinking they have something distributable.
 */
module.exports = function afterAllArtifactBuild(context) {
  const bar = '='.repeat(78);
  process.stderr.write(
    [
      '',
      bar,
      'UNSIGNED, UNNOTARISED BUILD — DO NOT DISTRIBUTE',
      '',
      'No Apple Developer ID exists for this project, so nothing here has been through',
      'codesign or notarytool. `brew audit --cask` would reject it, macOS Gatekeeper will',
      'refuse to open it without an explicit override, and the cask in packaging/ is still',
      'a placeholder (version 0.0.0-unreleased, sha256 NO_RELEASE_SHA256_DOES_NOT_EXIST_YET).',
      '',
      'Artifacts: ' + (context.artifactPaths || []).join(', '),
      bar,
      '',
    ].join('\n'),
  );
  return [];
};
