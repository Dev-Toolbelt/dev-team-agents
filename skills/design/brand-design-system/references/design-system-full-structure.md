# Design System (full) — Output Structure

The `design-system-full` doc uses the **same 15 sections in the same order** as `brand-guide-structure.md`, titled `# Design System — [Brand name, when identifiable]`. Only the three sections below differ: the values live **inline** here, because this document is self-contained. Everything else (Project Summary, 1, 2, 5–13, 15) is written exactly as that file says, except that section 5 may also cite HEX values.

When the project already has `design-system` or `brand-guide` docs, open the document with this banner (translated into the output language) and keep the values identical to `design-system`:

> Derived snapshot, YYYY-MM-DD. The owners are the `design-system` (`design-tokens` in the gated layout) and `brand-guide` docs; change a value there first.

## 3. Web Type Scale and Hierarchy

State the modular scale (base and ratio, e.g. base 16px, ratio 1.250 Major Third) and why it fits the brand, then the table. Every level gives px **and** rem:

| Level | Size (px / rem) | Weight | Line-height | Letter-spacing |
|---|---|---|---|---|
| H1 / main title | | | | |
| H2 / subtitle | | | | |
| H3 | | | | |
| H4 | | | | |
| Body | | | | |
| Small / auxiliary | | | | |
| Caption | | | | |
| Button | | | | |
| Overline / label | | | | |

Then a **spacing scale** (e.g. 4, 8, 12, 16, 24, 32, 48, 64px).

## 4. Color Palette

For each color: **name + HEX + RGB**, grouped as primary with tints/shades (50, 100, 300, 500 base, 700, 900), secondary with tints/shades, neutrals, recommended complementary colors, and state colors (success, warning, error, info). Close with copyable CSS tokens:

```css
:root {
  --color-primary: #......;
  --color-primary-dark: #......;
  --color-primary-light: #......;
  --color-secondary: #......;
  --color-neutral-900: #......;
  /* ... */
}
```

## 14. Consolidated Visual Tokens

Same block as the brand guide, with the values written out (HEX, px) instead of token names:

```
fonts: { heading: ..., body: ..., support: ... }
type_scale: base 16px, ratio ...
palette: { primary: #..., secondary: #..., neutrals: [...], accents: [...] }
icons: [style]
image_style: [style signature]
image_avoid: [...]
default_ratios: [...]
voice: [...]
```
