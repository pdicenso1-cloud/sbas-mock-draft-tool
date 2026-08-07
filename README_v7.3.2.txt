FantasySync v7.3.2 — CSS Runtime Hotfix

Replace only:
components/bottom_sheet.py

The v7.3.1 CSS override used normal braces inside the _render_sheet_css()
Python f-string. Python interpreted the CSS as f-string expressions and raised:

NameError: name 'height' is not defined

v7.3.2 changes only those braces to escaped {{ }} f-string literals.

Unchanged:
- draft board
- app.py
- runtime.py
- search and ALL/QB/RB/WR/TE
- sorting logic
- Queue/Roster behavior
- CPU/autorefresh
- tray sizes and density

Validation:
- py_compile passed
- patched module imported successfully
- _render_sheet_css(1) was executed successfully
- CSS output was inspected programmatically
- 58 / 236 / 332 tray heights verified
