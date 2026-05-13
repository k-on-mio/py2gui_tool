# py2gui_tool

将 `.py` 命令行脚本自动转换成带 GUI 界面的工具。

`py2gui_tool` turns common Python CLI scripts into a generated Tkinter GUI project.

Supports:

- `argparse.ArgumentParser().add_argument(...)`
- `@click.command()` with `@click.option(...)` and `@click.argument(...)`
- `typer` command function parameters

## Install

```bash
pip install .
```

Or run directly:

```bash
python -m py2gui_tool
```

## Build exe

```powershell
.\build_exe.ps1
```

Output: `dist\py2gui_tool.exe`

## Workflow

1. Select a `.py` script
2. Click **Analyze**
3. Review detected arguments
4. Choose an output folder
5. Click **Generate GUI project**
6. The generated project comes with its own `build_exe.ps1` if you want an exe for that specific script

The generated GUI runs the original script with `subprocess`, so the original script remains the source of truth.

## Language

The tool UI supports Chinese and English. Use the **Language** selector at the top:

- `zh` — Chinese
- `en` — English

## License

MIT
