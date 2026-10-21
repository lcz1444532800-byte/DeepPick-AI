# DeepPick AI

**A Live Text-inspired screen text tool for Windows.**

Capture an area. Select its text. Copy what you need.

[Download for Windows](https://github.com/lcz1444532800-byte/DeepPick-AI/releases/latest) · [User guide & FAQ](docs/User-Guide.md)

![DeepPick AI homepage](docs/images/home.png)

## Features

- Select text on the original captured image, with yellow highlights and no redrawn text overlay.
- Drag again to add another passage, then copy in reading order.
- Recognize text offline using bundled PaddleOCR PP-OCRv4 models and ONNX Runtime.
- Connect your own **DeepSeek API** for corrections, table recovery, formulas, translation, summaries, and explanations.
- Enable or disable automatic enhancement. Manual enhancement works independently of that switch.
- Customize shortcuts, run in the system tray, keep the last 20 results, and automatically clean caches.

## Quick start

**Windows 10 / 11 x64. A D: drive is required.** Allow at least 1 GB of free disk space and 2 GB of available memory.

1. Download **DeepPickAI-1.2.3-Windows-x64.zip** from [Releases](https://github.com/lcz1444532800-byte/DeepPick-AI/releases/latest).
2. Extract everything to `D:\`, producing `D:\DeepPickAI\DeepPickAI.exe`.
3. Double-click **DeepPickAI.exe**. No Python installation, command line, or separate model download is needed.

Choose the Windows ZIP rather than GitHub's automatically generated **Source code** archives. Keep every bundled component together; do not run inside the ZIP or copy out only the EXE.

| Action | Default shortcut |
|---|---|
| Capture an area | Ctrl + Space |
| Copy selected text | Ctrl + Enter |
| Cancel or close the selection | Esc / right-click |
| Select all recognized text | Ctrl + A |

Drag again to select multiple passages. Shift has no special function. Change the capture shortcut in Settings if it conflicts with your input method or another app.

Create a desktop shortcut in Windows Explorer: right-click the EXE → Show more options → Send to → Desktop (create shortcut).

Closing the homepage keeps the app running in the tray. Right-click the tray icon and choose **Exit** to quit. **Start with Windows is enabled by default** and can be disabled in Settings.

## Optional DeepSeek enhancement

Enter your own API key in **Settings → DeepSeek**, test the connection, and save. Local OCR does not need a key; without one, the app makes no AI requests.

With a saved key, automatic enhancement can improve low-confidence results. Manual **AI enhance** works after a capture even when automatic enhancement is off. The toolbar shows whether this capture has actually been enhanced.

AI uploads the selected screenshot and recognized text to DeepSeek and uses your API balance. A successful connection test does not verify a paid image request. For offline processing, disable automatic enhancement and do not request manual AI actions.

Keys are hidden in the interface and stored in encrypted configuration on D:. Releases contain no developer key, personal settings, recognition history, or screenshots. Share the original release ZIP instead of your used installation folder.

## Storage

Application files, models, and runtime data stay on D:. The startup shortcut uses Windows' actual Startup folder, which may be on C:.

Cache and temporary files share a default **128 MB** limit. Cleanup runs every five minutes; caches expire after seven days, and logs are limited to 50 MB. Models stay warm for responsiveness while unused inference memory is reclaimed.

The [user guide](docs/User-Guide.md) covers installation, AI setup, updates, removal, and **24 FAQs**. An offline HTML guide is included in the ZIP and can be opened from the homepage.

## Source and runtime

`app/source` contains the modular application. This repository's `app/runtime` contains startup scripts and provenance metadata. The complete runtime and OCR models are included in release downloads.

The executable uses an unmodified, officially signed Python embedded GUI runtime. That signature belongs to the runtime; application source has no separate publisher signature. Other hardware, mixed-DPI displays, and enterprise policies still need wider testing.

See [development notes](DEVELOPMENT.md) for the structure and release process.

## Feedback

Open an [issue](https://github.com/lcz1444532800-byte/DeepPick-AI/issues) with your Windows version, display scaling, reproduction steps, and error message. Remove sensitive content from screenshots. Never attach API keys, your `config` folder, or private recognition history.

## Licensing and acknowledgments

The original application code is released under the [MIT License](LICENSE). Third-party components retain their respective licenses; see [notices](THIRD_PARTY_NOTICES.md). License texts are included with releases.

Inspired by macOS Live Text. This project is not affiliated with Apple and does not include Apple's implementation. Local OCR uses PaddleOCR models distributed through RapidOCR, ONNX Runtime, and a PySide6 interface.

A small tool I built to make extracting screen text on Windows more convenient.

Developer:Chunze Liu
