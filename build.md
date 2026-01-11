# Building Memory Parasite

This project uses Python with Skia for rendering and ModernGL for post-processing.

## Prerequisites

- Python 3.11+
- pip (Python package manager)

## Installation

1. Clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - **Linux/Mac**: `source venv/bin/activate`
   - **Windows**: `venv\Scripts\activate`
4. Install dependencies:
   ```bash
   pip install skia-python moderngl glfw numpy miniaudio pygame
   ```

## Running the Game

```bash
python main.py
```

## Creating a Standalone Executable

The project includes a cross-platform PyInstaller configuration (`memory_parasite.spec`).

### All Platforms
```bash
pip install pyinstaller
pyinstaller memory_parasite.spec
```
The executable will be in the `dist/` directory.

### Manual build commands (Alternative)

If you prefer not to use the `.spec` file:

#### Linux
```bash
pyinstaller --onefile --noconsole --add-data "assets:assets" --add-data "levels:levels" --add-data "dialog_intro.xml:." main.py
```

#### Windows
```cmd
pyinstaller --onefile --noconsole --add-data "assets;assets" --add-data "levels;levels" --add-data "dialog_intro.xml;." main.py
```

#### macOS
```bash
pyinstaller --onefile --noconsole --add-data "assets:assets" --add-data "levels:levels" --add-data "dialog_intro.xml:." main.py
```

## Troubleshooting

- **Audio**: If you have no sound, ensure `miniaudio` or `pygame` is correctly installed. On Linux, you might need `libasound2-dev`.
- **OpenGL**: Ensure your graphics drivers support OpenGL 3.3+.
