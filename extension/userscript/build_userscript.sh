#!/bin/bash
# Builds a Safari-compatible userscript from the Chrome extension files.
# Usage: ./build_userscript.sh

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/alc-copilot.user.js"

{
  cat <<'HEADER'
// ==UserScript==
// @name         ALC Copilot
// @namespace    local.alc
// @version      1.0.0
// @description  AI Learning Copilot - explains content, MCQs, coding problems, and chats about the page. Works with the local backend on localhost:8000.
// @match        *://*/*
// @exclude      https://chrome.google.com/*
// @exclude      https://accounts.google.com/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

HEADER

  echo "  const ALC_STYLES = \`"
  cat "$DIR/../styles.css"
  echo "\`;"
  echo ""
  echo "  const styleEl = document.createElement('style');"
  echo "  styleEl.textContent = ALC_STYLES;"
  echo "  document.head.appendChild(styleEl);"
  echo ""

  cat "$DIR/../content.js"

  cat <<'FOOTER'
})();
FOOTER
} > "$OUT"

echo "Built $OUT"
