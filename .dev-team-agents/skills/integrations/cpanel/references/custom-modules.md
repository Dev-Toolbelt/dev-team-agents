# Custom UAPI Modules

Source: *Custom UAPI Modules* (api.docs.cpanel.net/cpanel/custom). Requires root on the server; WHM API 1 does not support custom modules.

## Steps

1. Write a Perl module at `/usr/local/cpanel/Cpanel/API/<Module>.pm` (namespace `Cpanel::API::<Module>`).
2. Add functions (one subroutine each).
3. Test on a **non-production** server before installing to production.

Every `.pm` in `/usr/local/cpanel/Cpanel/API/` is treated as a UAPI module — keep only module files there.

## Naming

| Element | Rule |
|---|---|
| Module | CamelCase; must not clash with an existing UAPI module; must not start with `_` |
| Function | lowercase snake_case; names starting with `_` are **private** (not callable, hidden from API Shell) |

## Template

```perl
package Cpanel::API::Example;

use strict;

our $VERSION = '1.0';

use Cpanel         ();
use Cpanel::API    ();   # lets your functions call other UAPI functions
use Cpanel::Locale ();
use Cpanel::Logger ();

sub do_thing {
    my ( $args, $result ) = @_;                       # always first

    my $feature = 'filemanager';                      # optional feature gate
    if ( !main::hasfeature($feature) ) {
        $result->error( '_ERROR_FEATURE', $feature );
        return 0;
    }
    if ( $Cpanel::CPDATA{'DEMO'} ) {                  # block demo accounts
        $result->error('_ERROR_DEMO_MODE');
        return 0;
    }

    my ($name) = $args->get_length_required('name');  # required, non-empty
    my ($opt)  = $args->get('optional_param');        # optional

    # validate, sanitize, act …

    $result->data( [ { name => $name, ok => 1 } ] );  # array of hashes => filter/sort/paginate work
    return 1;                                         # 1 success, 0 failure — never bare `return`
}

1;
```

## `Cpanel::Args` Methods

| Method | Behaviour |
|---|---|
| `$args->exists('p')` | `1` if the param exists (even blank) |
| `$args->get('a','b')` | Values of optional params; no error when missing |
| `$args->get_required('p')` | Error if missing; blank is allowed |
| `$args->get_length_required('p')` | Error if missing **or** blank |
| `$args->add('k','v')` | Inject a named param |
| `$args->keys()` | All param names |

## `Cpanel::Result` Methods

| Method | Behaviour |
|---|---|
| `$result->data($x)` | Set output data — call **once** (a second call overwrites) |
| `$result->error('literal')` | Append a localized error — string literals only, no interpolation |
| `$result->raw_error('… [_1]', $v)` | Append an error with interpolated data, not localized |
| `$result->message('literal')` / `raw_message(...)` | Same pair, for informational messages |
| `$result->metadata('k', 'v')` | Add metadata (rarely needed) |

Encode Unicode output before returning it, to avoid "Wide character" warnings: `use Encode qw(encode); $result->data( encode('utf-8', $data) );`

## Calling It

```bash
uapi --user=username Example do_thing name=foo
curl -H "Authorization: cpanel user:TOKEN" "https://host:2083/execute/Example/do_thing?name=foo"
```
