import { Toaster as Sonner, type ToasterProps } from "sonner"

// The app follows the OS colour scheme and has no theme toggle, so `system` is the theme.
// The CSS variables map sonner's surface onto the same tokens a popover uses.
function Toaster(props: ToasterProps) {
  return (
    <Sonner
      theme="system"
      className="toaster group"
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
        } as React.CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }
