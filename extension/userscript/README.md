# ALC Copilot on Safari (userscript)

Works with the free **Userscripts** app for macOS/iOS Safari. No Xcode needed.

## Setup (macOS)

1. Install **Userscripts** from the Mac App Store (free, by Justin Pradier)
2. Open Safari → open **Userscripts** app once → it adds an extension icon in the Safari toolbar
3. In Safari: **Settings → Extensions** → enable **Userscripts** → click it in the toolbar → **Open Editor**
4. Drag `alc-copilot.user.js` into the Userscripts editor window (or use + to add it)
5. Back in Safari **Settings → Extensions**, click **Userscripts** and toggle:
   - "Allow on all websites" (or click *Always Allow on Every Website*)
   - "Full page access" if prompted
6. Start the backend: `make backend` from the `alc/` root
7. Visit any website → click the **⚡** button bottom-right

## Rebuilding after extension changes

The userscript is generated from the Chrome extension files so they stay in sync:

```bash
cd extension/userscript && ./build_userscript.sh
```

Then re-add the new file in the Userscripts editor (replace the old one).

## Notes / limitations

- Works on any website except Chrome-internal URLs (those aren't reachable in Safari anyway)
- Backend must run on `localhost:8000` (same as the Chrome extension)
- If a site loads the script but the ⚡ button is missing, refresh the page once (SPA pages can sometimes delay injection)
