# Generate Local Shelving Order

**WORK IN PROGRESS**

Identify FOLIO items that need a locally defined shelving order, and create an item note with that value.

Uses https://github.com/lehigh-university-libraries/folio-shelving-order to actually generate the local shelving order for a given call number.  See that readme for why a locally generated value may be needed.

## Dependencies

- FOLIO
- MetaDB
- Python

## Command Line Parameters

| Parameter | Default | Description |
|---|---|---|
| `--call-number-prefix` | _(none)_ | Limit processing to items whose call number (item or holdings level) starts with this prefix. |
| `--start-offset` | `0` | Skip this many items before processing begins (useful for resuming a partial run). |
| `--overwrite` | _(flag, off by default)_ | If present, replace any existing shelving order note. Otherwise items that already have the note are skipped. |

Example:

```
python update_local_shelving_order.py --call-number-prefix 6 --start-offset 500 --overwrite
```

## Development/Deployment

1. Create and configure `config.properties` based on [the example](./config/config.properties.example)
