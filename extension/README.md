# ALC Browser Extension

Injects an AI assistant into any website — get help without leaving the page. Built for NxtWave, works on Udemy, Coursera, LeetCode, GeeksforGeeks, documentation sites, etc.

## How to Install (Chrome)

1. Open Chrome and go to `chrome://extensions`
2. Enable **Developer mode** (toggle top-right)
3. Click **Load unpacked**
4. Select this folder (`extension/`)
5. The extension is now active on `https://learning.ccbp.in/*`

## How to Use

1. Make sure the backend is running: `make backend` from the `alc/` root
2. Go to any website (NxtWave, Udemy, LeetCode, etc.)
3. Click the **⚡** button that appears bottom-right
4. Two tabs available:

### Tools tab
- **🔍 Explain**: Select text on the page, click Explain — gets a simple explanation
- **✅ Explain MCQ**: Automatically detects MCQ questions on the page and explains each option
- **💻 Coding Help**: Explains coding problems with algorithms, data structures, approach
- **📝 Generate Notes**: Summarizes the page into study notes (summary, key concepts, flashcards)

### Chat tab
- Ask any doubt in plain text — the AI answers conversationally
- Chat history is maintained for follow-up questions
- Works with any content on the page (no selection needed)

## Updating After a Fix

If you edit files in this folder, reload the extension:
1. Go to `chrome://extensions`
2. Click the **refresh** icon on the ALC Copilot card
3. Refresh the NxtWave page

## Requirements

- Backend running on `http://localhost:8000` (`make backend`)
- Ollama running with a model pulled (e.g. `ollama pull qwen2.5:7b`)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Cannot reach backend" | Start backend: `cd alc && make backend` |
| No response / slow | Check Ollama is running (`ollama list`) |
| Widget not appearing | Reload extension + refresh page |
| Empty results | Page may use heavy JS; click a tool again after the page settles |
