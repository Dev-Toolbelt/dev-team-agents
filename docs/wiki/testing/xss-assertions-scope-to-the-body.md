# XSS Assertions Must Scope to the Element That Renders Untrusted Content

**Origin:** Provider logos on skills and projects screens | 2026-10-19
**Tags:** xss, onerror, innerHTML, img, querySelector, toBeNull, skills.test.tsx, sanitize, text rendering, regression test

> Read this first: an XSS guard that asserts "no `<img>` on the page" breaks as soon as any legitimate image appears. Scope the assertion to the element that renders the untrusted content.

---

## What it is
`app/test/renderer/skills.test.tsx` guards that a skill body containing markup, such as `<img src=x onerror=alert(1)>`, renders as text and never as an element. The guard has to keep working when the rest of the screen is allowed to contain images.

## How it works
1. The test feeds a skill body of `# Title <img src=x onerror=alert(1)>` into the renderer.
2. The original assertion was `document.querySelector('img')` to be `null`. That was global, so provider logos (real `<img>` elements) on the same screen made it fail.
3. Narrowing to `img[src="x"]` removes the false failure but couples the test to the fixture string. Any change to the payload silently makes it pass.
4. The robust form scopes to the rendering element:
   - `expect(body.querySelector('*')).toBeNull()` checks that the body has no child elements.
   - `expect(body).toHaveTextContent('<img src=x onerror=alert(1)>')` checks that the payload shows up as literal text.

## Gotchas
- A passing `querySelector('*')` check alone proves nothing if the body is not the element that renders the content. Locate the body first and assert on it.
- Keep the literal payload in the text assertion. It proves the markup was escaped, not dropped.

## References
- `app/test/renderer/skills.test.tsx`
- `docs/wiki/testing/vitest-inlines-small-assets.md` (why logo `src` values are not asserted by filename)
