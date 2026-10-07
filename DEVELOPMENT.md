# Development notes

Developer:Chunze Liu

The English publication is separate from the developer's installed edition. All development and release work stays on D:.

## Structure

- app/source: modular Python application, icons, fixed dependency versions, and the optional PyInstaller specification.
- app/runtime: signed embedded runtime in release packages; this repository includes its bootstrap scripts and provenance only.
- models: bundled PP-OCRv4 models, dictionary, and source/hash manifests in releases.
- app/licenses: third-party licenses in release packages.
- docs: English guide, quick start, and actual English UI screenshot.
- app/source/tools: offline guide renderer and private-data-excluding release publisher.

## Modules

| Module | Responsibility |
|---|---|
| main.py / paths.py | Initialization, single instance, D: data paths, exception handling |
| capture.py / screen_sync.py | Screen freeze, DPI mapping, selection, and DWM synchronization |
| ocr_engine.py / ocr_worker.py / ocr_service.py | Local models, shared memory, asynchronous worker, warmup, and bounded recovery |
| overlay.py / effects.py / cursors.py | Original pixels, text-region contrast, yellow selection, progress dots, red cursor |
| domain.py / selection_mapping.py | Hit testing, reading order, multiple passages, and selection remapping |
| ai_service.py | Fixed official DeepSeek HTTPS endpoint, English instructions, validated structured results |
| storage.py / housekeeping.py | Encrypted settings, Windows ACL, atomic writes, history, quotas, expiration |
| win32.py / native_windows.py | Hotkeys, Shell links, single instance, startup, and native security calls |
| ui.py / style.py / controller.py | English windows, settings, result views, tray, workflow, safe shutdown |

## Working with the runtime

For the simplest development setup, use the complete release extracted on D:. Quit through the tray before replacing source or runtime components. The embedded module path is restricted to application-local directories; it does not use the system or user site-packages.

The root DeepPickAI.exe is an unmodified officially signed CPython GUI runtime, renamed only. Do not patch its PE metadata or icon. Direct launch delegates to the fully initialized `-B -m deeppick_entry` process. Startup adds `--background`; maintenance shutdown uses `-B -m deeppick_entry --quit`.

Do not run Qt inside Python site initialization or use os._exit for the normal GUI shutdown. Keep Qt owners alive until explicit shutdown completes. Runtime provenance and hashes are in app/runtime/manifest.json.

The PyInstaller specification is an alternative development build path. Such builds need appropriate publisher signing and validation before distribution; do not bypass Windows security policies.

## Publishing

Use app/source/tools/publish_release.py with an approved complete runtime root and a D: output directory. The publisher whitelists runtime source, dependencies, licenses, models, and English root documentation. Config, history, logs, cache, temp, output, development environments, and machine shortcuts are excluded.

Guide generation uses make_guide.py. Synchronize version strings in the UI, package metadata, runtime manifest, publisher, and guide when changing a version.

## Validation boundaries

OCR coordinates are physical image pixels; capture geometry is global logical coordinates with DPI conversion. The overlay never redraws recognized glyphs. AI correction retains known local polygons; newly estimated positions need review.

Models remain ready. Serial inference sessions share CPU scratch allocation, shrink it after runs, and release unused workspace while idle. Do not unload the models merely to reduce idle memory at the cost of next-capture responsiveness.

Automatic AI requires the enabled switch, a key, and low-quality results. Manual requests require a key but not the automatic switch. Requests use only the official endpoint and do not follow credential-bearing redirects.

Keep settings.enc and vault.key together. Encryption protects stored configuration with per-user ACLs; it does not protect against the active account or administrator. Never print keys, decrypted settings, private history, or full request bodies.

Validate offline launch, fully exited startup, DPI, negative coordinates, initial drag selection, copying, worker recovery, AI errors and stale requests, and cleanup limits. Use small neutral fixtures or background images rather than repeatedly displaying full-screen colored test patterns.
