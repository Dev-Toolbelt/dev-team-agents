# Brand Guide — Output Structure

Write the sections in exactly this order. Headings below are in English; translate them into the output language (`SKILL.md` § Principles → Language). Bracketed text is guidance, not output.

# Brand Guide — [Brand name, when identifiable]

## Project Summary

- **Brand / apparent segment:**
- **Personality:** [3–5 adjectives]
- **Visual impression / mood:**
- **Identity keywords:** [6–10 terms]

---

# PART A — Brand and Site Foundations

## 1. Logo Analysis

- Elements, shapes and composition
- Graphic style and visual weight
- Strengths of the identity
- Usage cautions (the essentials, no print rules)

## 2. Typography

For each role give the font, why, and a **free Google Fonts alternative**:

- **Logo font:** [probable or closest] *(approximation)* + Google Fonts alternative
- **Heading font:**
- **Body font:**
- **Support font** (captions, UI labels, microcopy):
- **Premium equivalent** (optional, when it makes sense)
- **Recommended weights** per role (e.g. 700 headings, 400/500 body)
- **Recommended pairings** (2–3 combinations that work together)

## 3. Web Type Scale and Hierarchy

The scale's values live in the `design-system` doc (`SKILL.md` § Outputs). Here: the modular scale chosen — base and ratio (e.g. base 16px, ratio 1.250, Major Third) — and why it fits the brand; the role of each level (H1–H4, body, small, caption, button, overline) by token name; and the spacing scale's rhythm (e.g. a 4px base), with a link to the values.

## 4. Color Palette

The HEX/RGB values and CSS tokens live in the `design-system` doc. Here, for each color: its **name**, its **token name**, where it comes from in the image and its role:

- **Primary** and its tints/shades (e.g. 50, 100, 300, 500 base, 700, 900)
- **Secondary** and its tints/shades
- **Neutrals** (text, backgrounds and borders)
- **Recommended complementary colors** (accents and highlights, coherent with the brand)
- **State colors** (success, warning, error, info) for UI

## 5. Contrast and Accessibility (WCAG)

- **Approved text-on-background combinations** by token name (AA or AAA, estimated ratio)
- Recommended accessible color for **body text**, **links** and **buttons**
- **Combinations to avoid** (likely to fail contrast)
- Note: validate exact ratios in a checker before applying

## 6. Graphic Style and Components

- Graphic elements (lines, shapes, ornaments, dividers)
- **Icons:** outline or filled, stroke, corners; recommended libraries (e.g. Lucide, Phosphor, Heroicons, Feather)
- Style of **buttons** (primary, secondary, messaging-app contact), **cards**, **highlight blocks** and **CTAs** — style description, not code

## 7. Image and Photography Direction (for the site)

- Recommended photo types
- Lighting, dominant colors, composition
- Treatment and what to avoid

---

# PART B — AI Image Generation Layer

## 8. Style Signature

A compact, reusable string to prepend to any prompt for consistency. The main one plus 2 variations (premium/institutional and vibrant/commercial), in copyable blocks:

```
[e.g. clean minimalist editorial style, muted earthy palette, soft diffused natural light, generous negative space, premium and understated]
```

## 9. Reusable Prompt Components

- **Style prefix** and **quality suffix** (copyable blocks)
- **Keyword bank** per category (style, color, light, mood, texture)
- **Aspect ratios per piece** (post 1:1, story 9:16, banner/hero 16:9 or 3:2)

## 10. Ready Prompts per Piece

Complete, copyable prompts in English and natural language (tool-agnostic), shaped `[style signature] + [subject] + [light] + [composition] + [aspect ratio]`. Cover: site hero/banner, product photo/mockup, post/carousel background, brand texture/pattern, and lifestyle image (when it fits).

## 11. Negative Prompt

```
avoid: [e.g. cluttered composition, neon colors, harsh flash, cartoonish, low resolution, watermark, distorted text]
```

Note: in tools without a negative parameter, describe the exclusions in the prompt text.

## 12. Per-tool Adaptation

- **Midjourney:** `--ar`, `--sref`, `--no`; use the brand image as style reference
- **Flux / GPT-Image / DALL·E:** plain natural language; describe ratio and exclusions in text
- **Ideogram:** when the image needs **legible text**
- Reminder: insert the logo in post-production

---

# PART C — Consolidation

## 13. Tone of Voice (summary)

- Register (formal / informal / balanced)
- Words to use and to avoid
- Short examples: institutional sentence, commercial call, CTA

## 14. Consolidated Visual Tokens

Final summary to paste and reuse. Fonts, styles and ratios are written out; colors and sizes are named by token, with the link to the `design-system` doc that holds their values:

```
fonts: { heading: ..., body: ..., support: ... }
type_scale: base 16px, ratio ... (values: design-system)
palette: { primary: --color-primary, secondary: --color-secondary, neutrals: [...], accents: [...] } (values: design-system)
icons: [style]
image_style: [style signature]
image_avoid: [...]
default_ratios: [...]
voice: [...]
```

## 15. Executive Summary

A short paragraph: how the brand should be perceived and how to keep it consistent across the site and the generated images.
