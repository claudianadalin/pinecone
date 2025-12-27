# CLI Reference

Pinecone provides a command-line interface for bundling your PineScript projects.

## Commands

### pinecone build

Bundle your PineScript files into a single output.

```bash
pinecone build [OPTIONS]
```

#### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--config PATH` | `-c` | Path to pine.config.json (default: ./pine.config.json) |
| `--watch` | `-w` | Watch for file changes and rebuild automatically |
| `--copy` | | Copy output to clipboard after build |
| `--help` | | Show help message |

#### Examples

**Basic build:**
```bash
pinecone build
```

**Build with custom config:**
```bash
pinecone build --config ./configs/production.json
```

**Watch mode:**
```bash
pinecone build --watch
```
This will watch for changes in your source files and automatically rebuild when changes are detected. Press `Ctrl+C` to stop.

**Build and copy to clipboard:**
```bash
pinecone build --copy
```
After building, the output is automatically copied to your clipboard, ready to paste into TradingView.

**Combine options:**
```bash
pinecone build --watch --copy
```
Watch for changes and copy to clipboard on each rebuild.

### pinecone --version

Show the current version of Pinecone.

```bash
pinecone --version
```

### pinecone --help

Show help information.

```bash
pinecone --help
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Error (config not found, parse error, circular dependency, etc.) |

## Error Messages

### Config file not found

```
Error: Config file not found. Create a pine.config.json file with 'entry' and 'output' fields.
```

**Solution:** Create a `pine.config.json` file or use `--config` to specify the path.

### Entry file not found

```
Error: Entry file not found: src/main.pine
```

**Solution:** Check that the `entry` path in your config is correct.

### Module not found

```
Error: Module not found: ./utils.pine
```

**Solution:** Check that the import path is correct and the file exists.

### Export not found

```
Error: Name 'foo' is not exported from ./utils.pine
```

**Solution:** Add `// @export foo` to the target file.

### Circular dependency

```
Error: Circular dependency detected: a.pine → b.pine → a.pine
```

**Solution:** Refactor your code to break the circular dependency.
