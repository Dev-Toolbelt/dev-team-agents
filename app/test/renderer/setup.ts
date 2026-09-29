/**
 * jsdom polyfills Radix primitives (Dialog, RadioGroup, Checkbox) reach for and jsdom does
 * not implement: pointer capture and `ResizeObserver`. Without these, mounting a screen
 * that opens a Radix dialog throws inside the library before a test gets to assert
 * anything — not a real behavioural difference the app cares about, so it is stubbed once
 * here rather than worked around per test.
 */
if (typeof Element.prototype.hasPointerCapture !== 'function') {
  Element.prototype.hasPointerCapture = () => false;
}
if (typeof Element.prototype.setPointerCapture !== 'function') {
  Element.prototype.setPointerCapture = () => {};
}
if (typeof Element.prototype.releasePointerCapture !== 'function') {
  Element.prototype.releasePointerCapture = () => {};
}
if (typeof Element.prototype.scrollIntoView !== 'function') {
  Element.prototype.scrollIntoView = () => {};
}
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  };
}
