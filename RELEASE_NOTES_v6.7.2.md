# FantasySync v6.7.2 — v6.7.1 Syntax Hotfix

Fixes the Streamlit `NameError` introduced in v6.7.1.

The full-width board CSS was added inside an existing Python f-string without escaping literal CSS braces. Python therefore attempted to evaluate CSS tokens such as `width:` as Python expressions.

## Fixed
- Escaped all CSS braces in the v6.7.1 full-width/snake-label style block.
- Preserves removal of round labels.
- Preserves 1.1–1.10 / 2.10–2.1 snake notation.
- Preserves the wider board layout.
- No tray, navigation, CPU, scrolling, roster, keeper, or draft logic changes.

## GitHub
Replace only `app.py`.
