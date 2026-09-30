import { useId, useState, type ReactNode } from "react";
import { FileText, FolderOpen } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { PluginFieldPicker, ProjectId } from "../../shared/api.js";

/**
 * A read-only display of a chosen project-relative path and the button that asks the main
 * process for one. The renderer never types or resolves a path: the bridge answers with a
 * relative path or a refusal, and this only shows the refusal beside the control.
 * `trailing` is where a list editor puts its Add button.
 */
export function PathPicker({
  id,
  label,
  picker,
  projectId,
  value,
  placeholder,
  disabled = false,
  describedBy,
  invalid = false,
  onPick,
  trailing,
}: {
  id: string;
  label: string;
  picker: PluginFieldPicker;
  projectId: ProjectId;
  value: string;
  placeholder?: string | undefined;
  disabled?: boolean;
  describedBy?: string | undefined;
  invalid?: boolean;
  onPick: (path: string) => void;
  trailing?: ReactNode;
}) {
  const [refusal, setRefusal] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const refusalId = useId();
  const Icon = picker === "directory" ? FolderOpen : FileText;

  async function choose() {
    setAsking(true);
    setRefusal(null);
    try {
      const answer = await window.devteam.pickProjectPath(projectId, picker);
      if (answer.picked) onPick(answer.path);
      else if (answer.refused !== undefined) setRefusal(answer.refused);
    } catch {
      setRefusal("The picker could not be opened.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="space-y-1">
      <div className="flex gap-2">
        <Input
          id={id}
          readOnly
          value={value}
          placeholder={
            placeholder ??
            (picker === "directory" ? "No directory chosen" : "No file chosen")
          }
          spellCheck={false}
          autoComplete="off"
          aria-invalid={invalid || refusal !== null || undefined}
          aria-describedby={
            [describedBy, refusal !== null ? refusalId : null]
              .filter(Boolean)
              .join(" ") || undefined
          }
          className="font-mono"
        />
        <Button
          type="button"
          variant="outline"
          disabled={disabled || asking}
          onClick={() => void choose()}
        >
          <Icon aria-hidden="true" />
          Choose…
          <span className="sr-only">
            {" "}
            {picker === "directory" ? "directory" : "file"} for {label}
          </span>
        </Button>
        {trailing}
      </div>
      {refusal !== null ? (
        <p id={refusalId} role="alert" className="text-xs text-destructive">
          {refusal}
        </p>
      ) : null}
    </div>
  );
}
