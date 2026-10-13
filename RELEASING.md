# Releasing

1. Set `version` in `custom_components/sound_recognition/manifest.json` **and** `__version__` in `service/soundrec/__init__.py` (the same number: Home Assistant offers a service update while the service reports an older one) and add the entry to the changelog (if any). Commit and push.
2. In GitHub Desktop: **History**, right-click the top commit, **Create Tag…** `vX.Y.Z` (same number as the manifest), then **Push origin**.
3. The **Release** workflow creates the GitHub release with generated notes. HACS then shows `vX.Y.Z`.

The workflow fails if the tag and the manifest version differ; fix the manifest, delete the tag and tag again.

## Compatibility

The integration is often updated before the service (HACS first, then the service update from Home Assistant). Whatever it asks the service at startup must therefore tolerate an older service: fall back when a route is missing, so the integration still loads, shows the panel and offers the update. Only raise the minimum API level (`MIN_API_LEVEL`) for things that can wait until the service is updated.

These tests enforce it (`tests/test_compat.py`). Every route of the service is declared in `tests/compat_routes.json` with the API level that introduced it. A route newer than `MIN_API_LEVEL` must be declared `fallback` (the client falls back at startup, and a test calls it against a service that answers 404) or `on_demand` (only called after a user action that the panel offers when the service has the feature). A last test loads the integration against a service one API level behind and checks that the panel, the *Update* entity and the panel's first commands work.
