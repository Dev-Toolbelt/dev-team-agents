import * as React from "react"

/**
 * Where portalled overlays (tooltips, menus) mount. `null` means `document.body`. A subtree shown
 * through the Fullscreen API provides its own element: only that element is painted while it is
 * full screen, so an overlay portalled to `body` would be invisible.
 */
const PortalContainer = React.createContext<HTMLElement | null>(null)

function usePortalContainer(): HTMLElement | undefined {
  return React.useContext(PortalContainer) ?? undefined
}

export { PortalContainer, usePortalContainer }
