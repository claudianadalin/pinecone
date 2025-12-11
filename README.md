# Pinecone

A bundler for multi-file PineScript development.

## Installation

```bash
pip install pinecone-bundler
```

## Usage

1. Create a `pine.config.json` in your project root:

```json
{
  "entry": "src/main.pine",
  "output": "dist/bundle.pine"
}
```

2. Use `// @export` to mark functions for export:

```pine
//@version=5
// @export myFunction

myFunction(x) =>
    x * 2
```

3. Use `// @import` to import from other files:

```pine
//@version=5
// @import { myFunction } from "./utils.pine"

indicator("My Indicator", overlay=true)
result = myFunction(close)
plot(result)
```

4. Bundle your project:

```bash
pinecone build
```

## License

MIT
