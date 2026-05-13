# py2gui_tool

将 `.py` 命令行脚本自动转换成带 GUI 界面的工具。

支持以下框架：

- `argparse.ArgumentParser().add_argument(...)`
- `@click.command()` + `@click.option(...)` / `@click.argument(...)`
- `typer` 命令函数参数

## 安装

```bash
pip install .
```

或直接运行：

```bash
python -m py2gui_tool
```

## 打包为 exe

```powershell
.\build_exe.ps1
```

输出位置：`dist\py2gui_tool.exe`

## 使用流程

1. 选择一个 `.py` 脚本
2. 点击 **分析**
3. 查看识别到的参数
4. 选择输出目录
5. 点击 **生成 GUI 工程**
6. 生成的工程自带 `build_exe.ps1`，可进一步打包为 exe

生成的 GUI 通过 `subprocess` 调用原始脚本，原始脚本始终是唯一的数据来源。

## 语言

工具界面支持中文和英文。通过顶部的 **语言** 下拉框切换：

- `zh` — 中文
- `en` — English

## 许可证

MIT
