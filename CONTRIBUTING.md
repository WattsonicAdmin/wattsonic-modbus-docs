# Contributing

This package mirrors the official Wattsonic MATIC Modbus documentation published at
https://modbus.wattsonic.com/. The data is generated from Wattsonic's documentation sources,
so pull requests that edit files under `src/wattsonic_modbus_docs/data/` cannot be merged
directly.

Welcome contributions:

- **Documentation errata**: open an issue with the register or SunSpec point, the firmware
  version (register 13021 / model 1 `Vr`), what you read or wrote, and what you expected.
- **Server or tooling improvements** (`src/wattsonic_modbus_docs/*.py`, tests, packaging):
  pull requests with tests are welcome.

By contributing you agree that your contribution is licensed under the Apache License 2.0.
