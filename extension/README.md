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

## Manual test checklist

Automated tests cover the DOM logic against fixtures, but the capture paths
only really prove themselves on a live course page. Load the unpacked
extension with the backend running and walk this list.

### Capture preview
- [ ] Open ⚡ → Tools → tick **Preview captured text**. The preview shows the
      exact text that will be sent.
- [ ] The preview never contains the ⚡ ALC Copilot panel's own text.

### MCQ
- [ ] Open a real MCQ (NxtWave / Adda247) → **Explain MCQ**.
- [ ] The banner reads **Using: detected question**.
- [ ] The options in the result match the page word for word, in the same
      order — no invented option text.
- [ ] Verify the suggested answer yourself. If it disagrees, re-run once and
      check whether it is stable rather than trusting it.
- [ ] A page with a numbered nav list (1. Home, 2. Courses, ...) does not turn
      the nav into options.
- [ ] An MCQ further down a long lesson is still found.

### Selection
- [ ] Select a paragraph → **Explain** → banner reads **Using: selection**.
- [ ] Select text inside the ALC panel → nothing is captured; the banner falls
      back to the page instead.
- [ ] Select on page A, navigate to page B, then **Explain** → page A's
      selection is not used.

### Lesson
- [ ] **Generate Notes** on a lesson page produces summary, key concepts and
      flashcards.
- [ ] Hidden answers on the page (`display:none`, `visibility:hidden`) do not
      appear in the captured preview.

### Coding
- [ ] **Coding Help** on a coding exercise works and keeps the starter code's
      function name and parameters.
- [ ] **Explain** and **Explain MCQ** send no code blocks (check the preview).

### Iframe
- [ ] A question rendered inside an iframe is detected; the banner reads
      **Using: detected question (iframe)**.
- [ ] The ⚡ widget appears once, in the top document only — not inside the
      iframe.

### Watcher and chat
- [ ] Type in the chat box while the page re-renders → the conversation is not
      cleared from under you.
- [ ] Advance to the next question → a **New question detected** notice
      appears and the chat resets.
- [ ] Navigate to another lesson → a **New page detected** notice appears.
- [ ] Idle on a heavily animated page for a minute → no repeated chat resets.

### Failure behaviour
- [ ] Stop Ollama, then **Explain MCQ** → the panel shows
      **Model failed, retry**. It must never fall back to a guessed option.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Cannot reach backend" | Start backend: `cd alc && make backend` |
| No response / slow | Check Ollama is running (`ollama list`) |
| Widget not appearing | Reload extension + refresh page |
| Empty results | Page may use heavy JS; click a tool again after the page settles |
