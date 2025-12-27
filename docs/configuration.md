# Configuration

Pinecone uses a `pine.config.json` file to configure your project.

## Config File Location

By default, Pinecone looks for `pine.config.json` in the current directory. You can specify a different path using the `--config` flag:

```bash
pinecone build --config path/to/pine.config.json
```

## Options

### entry

**Required** - Path to your main PineScript entry file.

```json
{
  "entry": "src/main.pine"
}
```

The path is relative to the config file location.

### output

**Required** - Path where the bundled output will be written.

```json
{
  "output": "dist/bundle.pine"
}
```

The directory will be created if it doesn't exist.

## Complete Example

```json
{
  "entry": "src/main.pine",
  "output": "dist/bundle.pine"
}
```

## Import and Export Directives

### Exporting

Use `// @export` to mark functions for export:

```pinescript
//@version=5
// @export functionName

functionName(x) =>
    x * 2
```

Export multiple functions:

```pinescript
// @export foo, bar, baz
```

### Importing

Use `// @import` to import functions from other files:

```pinescript
// @import { functionName } from "./path/to/file.pine"
```

Import multiple functions:

```pinescript
// @import { foo, bar, baz } from "./utils.pine"
```

!!! warning "Path Requirements"
    - Paths must be relative (start with `./` or `../`)
    - Paths must include the `.pine` extension
    - Use forward slashes `/` even on Windows

## Project Structure

A typical project structure:

```
my-project/
├── pine.config.json
├── dist/
│   └── bundle.pine      # Generated output
└── src/
    ├── main.pine        # Entry point
    ├── utils/
    │   ├── math.pine
    │   └── format.pine
    └── indicators/
        ├── rsi.pine
        └── macd.pine
```

You can organize your files however you like - Pinecone will resolve all imports automatically.
