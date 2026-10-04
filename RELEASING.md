# Releasing

1. Set `version` in `custom_components/sound_recognition/manifest.json` and add the entry to the changelog (if any). Commit and push.
2. In GitHub Desktop: **History**, right-click the top commit, **Create Tag…** `vX.Y.Z` (same number as the manifest), then **Push origin**.
3. The **Release** workflow creates the GitHub release with generated notes. HACS then shows `vX.Y.Z`.

The workflow fails if the tag and the manifest version differ; fix the manifest, delete the tag and tag again.
