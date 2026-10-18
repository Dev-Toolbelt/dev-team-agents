# UAPI Filtering, Sorting and Pagination

Source: *UAPI Filters*, *UAPI Sorting*, *UAPI Pagination* (api.docs.cpanel.net/cpanel/filters, /sorting, /paginate).

These `api.*` parameters work on functions whose `data` is an **array of objects**. They are processed by the API layer after the function runs, so they cut the response size but not the server work. Append them to any such call.

## Filtering

| Parameter | Value |
|---|---|
| `api.filter` | `1` enable, `0` disable |
| `api.filter_column` | Name of a return field to match against |
| `api.filter_term` | Value to match (integer or string) |
| `api.filter_type` | Operator; default `contains` |

| Operator group | Operators |
|---|---|
| Numeric | `eq`, `ne`, `lt`, `gt`, `lt_handle_unlimited`, `gt_handle_unlimited` (the `_handle_unlimited` variants understand "unlimited" values) |
| String | `contains`, `begins`, `ends` (all case-insensitive), `matches` (regular expression) |
| Presence | `defined`, `undefined` |

Use a numeric operator when `api.filter_term` is an integer and a string operator when it is a string.

```bash
# Mailboxes on example.com only
curl -sS -H "Authorization: cpanel $U:$T" \
  "https://$H:2083/execute/Email/list_pops_with_disk?api.filter=1&api.filter_column=domain&api.filter_type=eq&api.filter_term=example.com"
```

## Sorting

| Parameter | Value |
|---|---|
| `api.sort` | `1` enable, `0` disable |
| `api.sort_column` | Return field to sort by |
| `api.sort_method` | `lexicographic` (default), `numeric`, `numeric_zero_as_max`, `ipv4` |
| `api.sort_reverse` | `1` descending, `0` ascending |

> **You must set `api.sort_method` when sorting numeric values, or the call fails.**

```bash
uapi --user=username Email list_pops_with_disk api.sort=1 api.sort_column=diskused api.sort_method=numeric api.sort_reverse=1
```

## Pagination

| Parameter | Value |
|---|---|
| `api.paginate` | `1` enable, `0` disable |
| `api.paginate_size` | Records per page |
| `api.paginate_page` | Page number to return |
| `api.paginate_start` | First record to return (alternative to `paginate_page`) |

The response `metadata.paginate` then contains:

```json
"paginate": {
  "total_pages": 4,
  "total_results": 350,
  "current_page": 1,
  "results_per_page": 100,
  "start_result": "1"
}
```

Loop until `current_page == total_pages`.

## Combining

Filter, sort and paginate can be combined in one call. They apply to the function's output: filter, then sort, then paginate. Functions with a native parameter for the same purpose (for example `Email::list_pops` `regex`) are cheaper, because they filter **before** building the output. Prefer the native parameter when one exists.
