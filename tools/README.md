# ZICORE Open Source Tools

All tools are open-source, recommended, and secure.

## Installed Tools

### Mozilla Thunderbird (Email)
- **Path**: `C:\Program Files\Mozilla Thunderbird\thunderbird.exe`
- **License**: MPL 2.0
- **API**: `/api/thunderbird/status`, `/api/thunderbird/open`, `/api/thunderbird/compose`
- **Usage**: Full email client with calendar, contacts, chat

### Mozilla Firefox (Browser)
- **Path**: `C:\Program Files\Mozilla Firefox\firefox.exe`
- **License**: MPL 2.0
- **API**: `/api/firefox/status`, `/api/firefox/open`, `/api/firefox/open-file`
- **Usage**: Web browsing, viewing generated content, web apps

### OpenSSH (Remote Access)
- **Port**: 22
- **License**: BSD-style
- **API**: `/api/ssh/status`, `/api/ssh/start`, `/api/ssh/stop`, `/api/ssh/execute`
- **Setup**: Run `tools/ssh/setup_ssh_server.bat` as Administrator
- **Connect**: `ssh zinem@localhost`

### FFmpeg (Video/Audio Processing)
- **License**: LGPL/GPL
- **Usage**: Video conversion, audio extraction, streaming
- **Install**: `winget install Gyan.FFmpeg` or via `tools/install_tools.bat`

## Tools to Install

### EmulatorJS (Game Emulator)
- **License**: MIT
- **Directory**: `tools/emulatorjs/`
- **Systems**: Atari, NES, SNES, GB, N64, PSX, Sega, MAME, and more
- **Setup**: 
  ```
  cd tools/emulatorjs
  npm install
  node server.js
  ```
- **ROMs**: Place game ROMs in `tools/emulatorjs/roms/`

### Webamp (Audio Player)
- **License**: MIT
- **Directory**: `tools/webamp/`
- **Description**: Exact Winamp 2 clone in the browser
- **Setup**:
  ```
  cd tools/webamp
  npm install
  node server.js
  ```

### FileBrowser (File Manager)
- **License**: Apache 2.0
- **Directory**: `tools/filebrowser/`
- **Description**: Web-based file manager, single binary
- **Download**: https://github.com/filebrowser/filebrowser/releases
- **Setup**:
  ```
  # Download binary
  Invoke-WebRequest -Uri "https://github.com/filebrowser/filebrowser/releases/latest/download/filebrowser_windows_amd64.exe" -OutFile "tools/filebrowser/filebrowser.exe"
  
  # Initialize
  tools\filebrowser\filebrowser.exe config init
  tools\filebrowser\filebrowser.exe config set --address 127.0.0.1 --port 8080
  tools\filebrowser\filebrowser.exe users add admin admin --perm.admin
  
  # Run
  tools\filebrowser\filebrowser.exe
  ```

### Photopea (Image Editor)
- **License**: Free web app
- **URL**: https://www.photopea.com
- **Embed**: `<iframe src="https://www.photopea.com"></iframe>`
- **Usage**: Photoshop-like editor in browser

### Monaco Editor (Code Editor)
- **License**: MIT
- **Description**: VS Code editor core (already in CODE workspace)
- **Enhancement**: Add language support, themes, keybindings

## Quick Install

Run `tools/install_tools.bat` as Administrator to install all tools.

## Shell Environment

For the ZICORE shell, we use **PowerShell 5.1** (native Windows):
- Already installed at `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`
- Cross-platform compatible with WSL if needed
- Supports all Windows system commands
- Can execute Python, Node.js, and other tools

For remote SSH sessions:
- PowerShell is the default shell for OpenSSH on Windows
- Can be changed to CMD or WSL bash if preferred
- SSH config at `C:\ProgramData\ssh\sshd_config`

## License

All ZICORE System code: CC-BY-SA-4.0
Individual tools retain their original open-source licenses.
