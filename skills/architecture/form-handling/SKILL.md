---
name: form-handling
description: Form design and validation — state, error feedback, library selection. Framework-agnostic.
---

# Form Handling

## Detect the Project's Form Library

Before writing any form code, check for an existing library:

| Signal | Library |
|---|---|
| `react-hook-form`, `useForm`, `register`, `Controller` | React Hook Form |
| `formik`, `useFormik`, `<Formik>` | Formik |
| `vee-validate`, `useField`, `useForm` (Vue) | VeeValidate |
| `@angular/forms`, `FormBuilder`, `FormGroup`, `ReactiveFormsModule` | Angular Reactive Forms |
| `zod`, `yup`, `valibot` imports alongside form code | Schema validation library |

If no library is detected: `useState` per field is acceptable for forms with 1–3 fields. For anything larger, recommend adopting the project's preferred library before building.

---

## Core Rules

### Controlled inputs by default
Always bind input value to state and update state on change. Uncontrolled inputs (`ref`-only) are acceptable only for file inputs or third-party widgets that require direct DOM access.

### Validation placement

| Trigger | When to use |
|---|---|
| `onBlur` | Default for most fields — validates after the user leaves the field |
| `onChange` | Use only after the first submission attempt, or for fields with instant feedback (password strength) |
| `onSubmit` | Always run a full validation pass on submit, regardless of field-level validation |

Never validate `onChange` from the first keystroke on empty fields — it creates errors before the user has had a chance to type.

### Schema-first validation
Define validation rules in a single schema (Zod, Yup, Valibot, or equivalent) rather than scattered `if` statements in handlers. The schema is the single source of truth for what constitutes valid data.

```ts
// good — rules live in one place, reusable on the server too
const orderSchema = z.object({
  quantity: z.number().min(1).max(999),
  email: z.string().email(),
})
```

### Error messages
- One error message per field, displayed below the field it belongs to
- Link the message to the input via `aria-describedby` (the field's `id` matches the error element's `id`)
- Use plain language: "Enter a valid email address", not "Invalid format"
- Clear the error as soon as the field becomes valid again

### Submit state
- Disable the submit button while the form is submitting (see `double-submission prevention` in the agent)
- Show a loading indicator during async submission
- On success: clear the form or navigate away — never leave a successfully submitted form in a dirty state
- On error: surface the server error near the form (not just in a toast), keep field values intact

### Reset and dirty tracking
- Track whether the form is dirty (has unsaved changes) to warn the user before navigation
- `reset()` must restore every field to its initial value, not just clear them to empty

---

## Library-Specific Notes

### React Hook Form
- Prefer `register` over `Controller` for native inputs — less overhead
- Use `Controller` for third-party components (date pickers, select libraries)
- Set `mode: 'onBlur'` as the default validation trigger
- Use `resolver` (zod, yup) to keep validation out of the component

### Formik
- Use `validationSchema` with Yup rather than the `validate` function for complex forms
- Avoid `setFieldValue` inside `onChange` handlers — use Formik's `handleChange` to avoid double renders
- `enableReinitialize` should be `false` by default; set to `true` only when the form must reflect external data changes

### VeeValidate (Vue)
- Use `defineRule` + `configure` globally for shared rules; use inline `rules` only for one-off cases
- Pair with `zod` via `@vee-validate/zod` for schema-first validation
- `useForm` + `useField` (Composition API) is preferred over the Options API component approach

### Angular Reactive Forms
- Always use `FormBuilder` — never instantiate `FormGroup` / `FormControl` manually
- Validators go in the `FormControl` definition, not in the template
- Use `updateOn: 'blur'` on controls that should validate after focus loss
- `AbstractControl.statusChanges` is the right hook for cross-field dependent validation — avoid manual `valueChanges` hacks

---

## Anti-Patterns

| Anti-Pattern | Problem |
|---|---|
| Validation logic duplicated in component and service | Single source of truth broken; rules drift apart |
| Showing all errors before the user interacts | Hostile UX — validate progressively |
| Resetting only visible fields on submit | Hidden state leaks into the next submission |
| Calling `event.preventDefault()` manually and then forgetting to handle errors | Leaves the form in a broken state on failure |
| Storing form state in a global store | Forms are transient UI state — keep them local |
| `any` type for form values | Defeats the purpose of schema validation |
