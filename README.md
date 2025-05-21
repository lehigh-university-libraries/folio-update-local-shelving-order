# Generate Local Shelving Order

**WORK IN PROGRESS**

Identify FOLIO items that need a locally defined shelving order, and create an item note with that value.

Uses https://github.com/lehigh-university-libraries/folio-shelving-order to actually generate the local shelving order for a given call number.  See that readme for why a locally generated value may be needed.

## Dependencies

- FOLIO
- MetaDB
- Python

## Development/Deployment

1. Create and configure `config.properties` based on [the example](./config/config.properties.example)
