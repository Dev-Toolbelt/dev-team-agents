import { useEffect, useRef } from 'react';
import { Check, Menu } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export interface NavMenuItem {
  value: string;
  label: string;
}

/**
 * The header's menu for the screens that are not tabs. The trigger reads as pressed while
 * one of them is open, since no tab in the strip is selected then. Choosing an item moves
 * focus into the opened screen rather than back to the trigger: to whatever the screen
 * focused itself (an error fallback does), else to its tab panel.
 */
export function NavMenu({
  items,
  current,
  onSelect,
}: {
  items: NavMenuItem[];
  current: string;
  onSelect: (value: string) => void;
}) {
  const active = items.some((item) => item.value === current);
  const chose = useRef(false);
  const pendingFocus = useRef<number | null>(null);
  useEffect(
    () => () => {
      if (pendingFocus.current !== null) cancelAnimationFrame(pendingFocus.current);
    },
    [],
  );
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant={active ? 'secondary' : 'ghost'} size="icon" aria-label="Menu">
          <Menu aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        onCloseAutoFocus={(event) => {
          if (!chose.current) return;
          chose.current = false;
          event.preventDefault();
          pendingFocus.current = requestAnimationFrame(() => {
            pendingFocus.current = null;
            const focused = document.activeElement;
            if (focused !== null && focused !== document.body) return;
            document.querySelector<HTMLElement>('[role="tabpanel"][data-state="active"]')?.focus();
          });
        }}
      >
        {items.map((item) => (
          <DropdownMenuItem
            key={item.value}
            aria-current={item.value === current ? 'page' : undefined}
            onSelect={() => {
              chose.current = true;
              onSelect(item.value);
            }}
          >
            <Check aria-hidden="true" className={item.value === current ? '' : 'invisible'} />
            {item.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
