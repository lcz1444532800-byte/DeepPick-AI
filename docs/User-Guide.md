# DeepPick AI

Screen text, ready to copy. Windows x64 · Version 1.2.3

Developer:Chunze Liu

## 1. First launch

Requires Windows 10/11 x64 and a D: drive. Reserve at least 1 GB of disk space and 2 GB of available memory. A native ARM or 32-bit edition is not provided.

1. Download **DeepPickAI-1.2.3-Windows-x64.zip** from the project's Releases page.
2. Right-click the ZIP, choose **Extract All**, and set the destination to `D:\`. The archive already includes the DeepPickAI folder; avoid a second nested folder.
3. Double-click `D:\DeepPickAI\DeepPickAI.exe`. The homepage opens while offline OCR prepares in the background.
4. No Python installation, model download, API key, or command line is required for local recognition.

Keep `app`, `models`, `DeepPickAI._pth`, and the DLL files together. Do not launch inside the ZIP or copy out only the EXE.

To create a desktop shortcut, right-click the EXE → Show more options → Send to → Desktop (create shortcut). Windows 10 shows Send to directly.

## 2. Capture, select, copy

1. Press **Ctrl + Space**, or click **Capture** on the homepage.
2. Hold the left mouse button, drag around the desired area, and release. A red cursor remains visible on bright backgrounds.
3. During recognition, the selected area retains its original image with a translucent animated dot field. The toolbar displays progress.
4. When ready, recognized text regions stay bright while other regions dim. Original screenshot glyphs are preserved instead of being redrawn.
5. Drag across text to select it. Selected text is highlighted yellow. Release, then drag again to add another passage; Shift is not required.
6. Press **Ctrl + Enter** to copy the selected text and close the area. Paste it in another app with Ctrl + V.

Copying follows reading order with reasonable spaces and line breaks. Review complex columns, merged cells, formulas, or important numbers in **View text**.

View text opens editable results, **Copy all**, and **Export text**. Exports go to `D:\DeepPickAI\output` and are not automatically deleted.

The selected area is a frozen capture. Press Esc or right-click to close it before interacting with the underlying window.

## 3. Shortcuts

| Action | Default | Scope |
|---|---|---|
| Capture | Ctrl + Space | Global while the app runs |
| Copy selected text | Ctrl + Enter | Text selection |
| Cancel or close | Esc | Capture or text selection |
| Select all | Ctrl + A | Text selection |
| Close | Right-click | Capture or text selection |
| Add another passage | Drag again | Keeps earlier selections |

Shift has no special function. Change capture, copy, and close shortcuts in **Settings → Shortcuts**. If Ctrl + Space conflicts with an input method, try an unused combination such as Ctrl + Alt + D.

## 4. DeepSeek AI setup — optional

Local OCR is free and works offline. AI needs an internet connection and your own DeepSeek API balance. A chat subscription or working web chat does not necessarily provide API credit.

1. Sign in to the [DeepSeek API console](https://platform.deepseek.com/api_keys) and create your own API key.
2. Confirm your API account has usable credit if you want AI features.
3. Open **Settings → DeepSeek** and paste the complete key. Its characters are hidden.
4. Click **Test connection**, then **Save**. The test checks the account endpoint; it does not submit an image or confirm a paid image request.
5. Capture an area and use automatic or manual enhancement as needed.

The app uses the official HTTPS endpoint and the image-capable `deepseek-flash` model. See the [official image guide](https://api-docs.deepseek.com/guides/vision/) and [pricing](https://api-docs.deepseek.com/quick_start/pricing/).

**Automatic enhancement:** enabled by default on the homepage. A saved key and low-quality recognition trigger it. The default threshold is 0.82, configurable in Settings. Local results appear first. Without a key, only local OCR runs.

**Manual enhancement:** click **AI enhance** on the capture toolbar. It works whenever a key is saved, including when automatic enhancement is disabled. View text also provides **AI correct**, **Restore table**, **Improve formulas**, **Translate**, **Summarize**, and **Explain**. Translation targets English; summaries and explanations are in English.

**Status:** the toolbar distinguishes processing, success, failure, or cancellation. A configured key or enabled switch alone does not mean a capture was enhanced.

AI sends this selected screenshot and its OCR text to DeepSeek and consumes your API balance. For private or offline processing, turn automatic enhancement off and do not request manual AI actions. Check important AI output for errors.

## 5. Tray and startup

Double-clicking the EXE opens the homepage. Closing its × button hides it, leaving the tray icon and global shortcut active.

The tray icon may be under the taskbar's hidden-icons arrow. Click it to open the homepage. Right-click for Capture, Settings, History, or **Exit**.

**Start with Windows is enabled by default.** Disable it in **Settings → General**. With **Start in the background** enabled, Windows startup shows the tray without opening the homepage; a manual launch opens the homepage.

App files and data stay on D:. Startup creates only DeepPick AI.lnk in Windows' registered Startup folder, which may be on C:. No services, drivers, or security-policy changes are installed.

## 6. History and storage

History keeps the last 20 recognized texts. Use the homepage's **History** button to view, copy, delete selected results, or clear history. Disable future saving in Settings → General; existing results are not deleted by that switch.

History contains text, not saved screenshot images, and may still contain personal information. Delete records when appropriate.

**Settings → Storage** shows usage, the cache limit, and **Clear cache**. Cache and temporary files share a default 128 MB limit, configurable from 32 to 4096 MB.

| Data | Cleanup |
|---|---|
| Temporary files | At startup and after one hour of storage |
| Cache | After seven days, and according to the combined size limit |
| Scheduled cleanup | Startup, every five minutes, and when opening or saving Settings |
| Logs | Total limit of 50 MB; older logs removed first |
| History | Last 20 results, deletable by the user |
| Exports | User-managed; not automatically removed |

Busy files and newly created temporary files are skipped and retried later. Runtime libraries and models are fixed components, not cache. OCR images are transferred through memory rather than saved continuously.

Models remain warm to preserve responsiveness. Extra work memory is reclaimed when idle, but large captures can temporarily increase memory usage.

## 7. Folders

| Inside D:\DeepPickAI | Purpose |
|---|---|
| DeepPickAI.exe | Application entry |
| DeepPickAI._pth, python3.dll, python311.dll | Required runtime files |
| app | Application, runtime, and licenses |
| models | Bundled offline OCR models |
| config | Encrypted API key and settings |
| logs | Runtime and error logs |
| cache | Limited runtime cache |
| temp | Temporary files |
| history | Last 20 text results |
| output | Exported text |
| User-Guide.html | Offline guide and FAQ |
| File-Checksums.json | Bundled file SHA-256 values |

Keep `settings.enc` and `vault.key` together. Configuration permissions are restricted to the current Windows user and SYSTEM. This does not protect against someone with your account or administrator access.

## 8. Update, share, remove

**Update:** exit through the tray first, then replace the program components with the new full package. Keep your existing config, history, and output. Do not remove the configuration key or replace DLLs while the app is running.

**Share:** distribute the original release ZIP. Do not repackage a used installation, which may contain your configuration, history, or exports.

**Remove:** disable Start with Windows and save; exit through the tray; remove the desktop shortcut; keep any desired exports and delete D:\DeepPickAI. No system runtime uninstall is needed.

## 9. Frequently asked questions

### 1. Do I need Python or separate model downloads?

No. Extract the complete Windows release ZIP and run its EXE. A lone EXE or the Source code archive is not a runnable installation.

### 2. What if my computer has no D: drive?

This version requires D:. It does not install to C: or repartition drives automatically. A different installation layout is not currently supported.

### 3. Why is the EXE missing, or why are runtime/models reported missing?

Check complete extraction and avoid `D:\DeepPickAI\DeepPickAI` nesting. The correct entry is `D:\DeepPickAI\DeepPickAI.exe`. Re-extract the original ZIP, preserving your existing config, history, and output if updating.

### 4. What if Windows security blocks the app?

Check the original package, its checksum, your x64 Windows version, and extraction path. The official runtime retains its signature, but application code has no separate publisher signature. Do not disable system security. Ask your organization's administrator about policy blocks and report the exact error without sending credentials.

### 5. Why does the shortcut still work after I close the homepage?

The × button hides the homepage. To fully quit, right-click the tray icon and choose Exit. Look under hidden taskbar icons if necessary.

### 6. Why is there no homepage after Windows starts?

Background startup is enabled by default. Look for the tray icon or try the capture shortcut. Disable Start in the background if you want the homepage at startup.

### 7. Why does Ctrl + Space do nothing or switch input methods?

Try the homepage Capture button. If it works, change the shortcut in Settings → Shortcuts. Games, remote sessions, or secure desktops may not accept ordinary desktop hotkeys.

### 8. Why does text not become selectable immediately?

The dot animation means recognition is running. First launch prepares models; large or dense captures and busy computers take longer. Capture the actual text area to reduce work. AI also depends on network and service response times.

### 9. How do I know whether this capture used AI?

Read the toolbar status. Only a successful enhancement that was applied counts. An enabled switch or successful connection test is not an enhancement. Failed AI requests leave local results available.

### 10. Can I use AI manually with automatic enhancement disabled?

Yes. Save an API key, then use AI enhance or the result window's AI actions. Automatic enhancement controls only automatic requests.

### 11. Can I use it without a key, and will the default switch charge me?

Local OCR works offline without a key, and no DeepSeek request is made without one. After saving a key, automatic triggers or manual AI actions may consume API credit.

### 12. Why are AI buttons unavailable after entering a key?

Click Save, not just Test connection or Cancel. Capture again. Use an API key rather than your web login password.

### 13. What does Invalid API key / HTTP 401 mean?

Check that your key was not revoked, copy the complete value again, and save it. Never post the key or expose it in screenshots.

### 14. What does Insufficient balance / HTTP 402 mean?

Check your API account credit. Working web chat does not imply API balance. Local OCR is unaffected.

### 15. What about HTTP 429, 500, or 503?

429 means rate limiting: wait and reduce consecutive requests. 500/503 indicate service errors or overload; try later. See [official error codes](https://api-docs.deepseek.com/quick_start/error_codes/).

### 16. Why does connection testing pass but image enhancement fail?

The connection test does not send images or verify a paid call. Check balance, image-model availability, network, proxy, and firewall access to DeepSeek. Continue using local results if the service is unavailable.

### 17. How can I improve missed text, errors, or table order?

Zoom the source page, capture clear text at a smaller size, and avoid cutting glyphs. The bundled model supports Chinese, English, and common characters; handwriting, tiny fonts, and other scripts are not guaranteed. Use AI actions or edit in View text as needed.

### 18. Why does the image look unchanged after AI corrects text?

The app preserves the original screenshot to avoid redraw artifacts. AI updates the recognized content used by View text and copying, not the original pixels. New positions may be estimates; check complex results.

### 19. What if selecting text does not respond or highlights are inaccurate?

Wait for recognition, then drag within bright text regions rather than toolbar buttons. Re-capture a clear area on one display if mapping looks wrong. Report display scaling and the affected app. Ctrl + A selects all recognized text.

### 20. Why is a video, game, or security window black in the capture?

Protected content and Windows secure desktops may prevent capture. Try a normal page or document. The app does not bypass screen protection; report problems affecting ordinary windows with your display setup.

### 21. Why does Ctrl + Enter not copy every word?

It copies only yellow-highlighted selections. Use Ctrl + A first, or View text → Copy all. Keep the selection open and check whether another clipboard tool is replacing it.

### 22. Why does memory or disk usage remain after cleanup?

Warm models use persistent memory; large captures have temporary peaks. Libraries and models are fixed files and are not removed by Clear cache. Exports are user-managed. Restart and report capture sizes if memory grows abnormally over time.

### 23. Why does cleanup say some files are in use?

Busy and newly created temporary files are preserved for active tasks. Cleanup retries every five minutes. Restart if needed; do not remove app, models, or config to clear cache.

### 24. Can I move settings to another computer?

Prefer a fresh release extraction and re-enter your key. Configuration has per-user Windows permissions and is not guaranteed to migrate across accounts. Copy exported text if needed; do not distribute config and vault.key as ordinary sharing material.

## 10. Help and component notices

Report Windows version, scaling, actions, and relevant error timestamps. Logs are in `D:\DeepPickAI\logs`. Remove private content and do not send API keys, config, or private history.

Local recognition and startup are checked. Real AI calls need your valid key, network, and balance. Other hardware, mixed-DPI configurations, and enterprise policies still need wider testing.

See Third-Party-Notices.txt and app/licenses for component sources and licenses. This guide can be read offline; external DeepSeek links need internet access.
