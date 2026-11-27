# Layout Proposals — Structure

Translate the headings into the `language` in `.dev-team-agents/resolved/preferences.json`; keep the order.

## The `layout-proposals` doc

Committed, short, the durable record. It holds no wireframe detail: that lives in the HTML page.

| # | Section | Content |
|---|---|---|
| 1 | Header | Project, date, the reference folder (name only), site type |
| 2 | Source map | One row per file in the folder: name, role, how it was used |
| 3 | Directions | One row per direction: label, thesis, theme, screen count |
| 4 | Assumptions | What the client must confirm, each as a checkbox |
| 5 | Research | Sources actually opened, one line each; sources not reached |
| 6 | Approval | Chosen direction or mix, requested changes, date. `Pending` until the client answers |
| 7 | Page | The Artifact link, or the path of the HTML file |

## The HTML page

One self-contained file: inline CSS, no external scripts, readable on desktop and phone, light and dark theme, a background and text color set explicitly.

| Part | Content |
|---|---|
| Top | Project name, site type, one-line summary, tabs or anchors for Direction A, B, C |
| Per direction | Thesis, theme, then the flow: a left-to-right strip of desktop screen wireframes with arrows for the user's path, each labeled with its name and purpose |
| Per screen | Wireframe, purpose, main action, asset used, requirement served, motion intent |
| Mobile | A phone-width wireframe per screen or per differing screen |
| Bottom | Assumptions to confirm, and an approval box describing how to answer |

Wireframes use grey boxes, labels and the real copy; the real logo appears only where the flow places it. No framework, no external image, embedded logos and photos downscaled to about 1600px on the long side (the page stays well under 16MB; a photo that would not fit becomes a labeled placeholder), no animation beyond a tab switch.
