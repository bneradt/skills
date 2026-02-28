# `bible-data` layout (targeted)

This skill expects the [`jburson/bible-data`](https://github.com/jburson/bible-data) repository layout:

- `data/VERSION/VERSION.json`

Example:

- `data/KJV/KJV.json`

Each verse row is expected to include:

- `r`: ref like `kjv:Genesis:1:1`
- `t`: verse text (possibly with inline formatting markers)

