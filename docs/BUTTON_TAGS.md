# ZICORE System v5.0 — Complete Button Tags Documentation
## ZineMotion Foundation — Aerospace Division

All buttons, controls, and interactive elements across the ZICORE system with their IDs, tags, descriptions, and keyboard shortcuts.

---

## 1. HOME MENU (index.html)

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `apiDot` | SYS | System status indicator — green when API connected | — |
| `statusDate` | SYS | Current date display (YYYY-MM-DD) | — |
| `statusTime` | SYS | Current time display (HH:MM:SS) | — |
| `connDot` | NET | Internet connection status — toggles green/red | — |
| `ecoLatency` | SYS | API latency display in ms | — |
| `configBtn` | CONFIG | Opens Configuration panel (dashboard view) | — |
| `btnDashboard` | WORKSPACE | Opens Content Creator dashboard | Click |
| `btnZio` | AI | Opens ZIO AI Agent panel | Click |
| `btnFlightSim` | SIM | Opens Flight Simulator | Click |
| `btnBack` | NAV | Returns to main menu from any view | — |

## 2. CONTENT CREATOR DASHBOARD (dashboard.html)

### Workspace Tabs

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `tabSystem` | WORKSPACE | System overview and controls | 1 |
| `tabZio` | WORKSPACE | ZIO AI interface | 2 |
| `tab3d` | WORKSPACE | 3D modeling workspace | 3 |
| `tabVideo` | WORKSPACE | Video editing NLE | 4 |
| `tabAudio` | WORKSPACE | Audio production studio | 5 |
| `tabImage` | WORKSPACE | Image editing suite | 6 |
| `tabCode` | WORKSPACE | Code editor and compiler | 7 |
| `tabText` | WORKSPACE | Text/Document editor | 8 |
| `tabVision` | WORKSPACE | Vision and rendering | 9 |
| `tabLibrary` | WORKSPACE | Content library manager | 0 |

### Video Tab

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `vidNew` | PROJECT | Create new video project | Ctrl+N |
| `vidOpen` | PROJECT | Open existing project | Ctrl+O |
| `vidSave` | PROJECT | Save current project | Ctrl+S |
| `vidExport` | EXPORT | Export video as MP4/MOV | Ctrl+E |
| `vidImportFolder` | IMPORT | Import media folder (shows feedback) | — |
| `vidCut` | EDIT | Cut clip at playhead | C |
| `vidSplit` | EDIT | Split clip at playhead | S |
| `vidTrim` | EDIT | Trim clip start/end | T |
| `vidDelete` | EDIT | Delete selected clip | Del |
| `vidUndo` | EDIT | Undo last action | Ctrl+Z |
| `vidRedo` | EDIT | Redo last action | Ctrl+Y |
| `vidPlay` | PLAYBACK | Play/pause timeline | Space |
| `vidSpeed` | EFFECT | Speed control slider (0.25x-4x) | — |
| `vidColor` | EFFECT | Color correction panel | — |
| `vidFilters` | EFFECT | Apply video filters | — |
| `vidText` | EFFECT | Add text overlay | — |
| `vidTransitions` | EFFECT | Add transition effects | — |

### Audio Tab

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `audNew` | PROJECT | Create new audio project | Ctrl+N |
| `audOpen` | PROJECT | Open audio file | Ctrl+O |
| `audSave` | PROJECT | Save project | Ctrl+S |
| `audExport` | EXPORT | Export as WAV/MP3/OGG | Ctrl+E |
| `audRecord` | RECORD | Start recording | R |
| `audPlay` | PLAYBACK | Play/pause | Space |
| `audCut` | EDIT | Cut selection | C |
| `audNormalize` | EFFECT | Normalize audio | — |
| `audCompress` | EFFECT | Dynamic range compression | — |
| `audEQ` | EFFECT | Equalizer panel | — |
| `audReverb` | EFFECT | Add reverb | — |
| `audBass` | MIXER | Bass EQ knob | — |
| `audVolume` | MIXER | Master volume fader | — |

### Image Tab

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `imgNew` | PROJECT | Create new canvas | Ctrl+N |
| `imgOpen` | PROJECT | Open image file | Ctrl+O |
| `imgSave` | PROJECT | Save image | Ctrl+S |
| `imgExport` | EXPORT | Export as PNG/JPG/WebP | Ctrl+E |
| `imgGen` | GENERATE | AI generate image from prompt | Ctrl+G |
| `imgGenBatch` | GENERATE | Generate batch of images | — |
| `imgCrop` | EDIT | Crop tool | C |
| `imgBrightness` | ADJUST | Brightness slider | — |
| `imgContrast` | ADJUST | Contrast slider | — |
| `imgBlur` | FILTER | Gaussian blur | — |
| `imgSharpen` | FILTER | Sharpen filter | — |
| `imgSepia` | FILTER | Sepia tone | — |
| `imgBrush` | TOOL | Brush tool | B |
| `imgEraser` | TOOL | Eraser tool | E |
| `imgText` | TOOL | Text tool | T |

### Code Tab

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `codeNew` | PROJECT | New file | Ctrl+N |
| `codeOpen` | PROJECT | Open file | Ctrl+O |
| `codeSave` | PROJECT | Save file | Ctrl+S |
| `codeRun` | EXECUTE | Run/execute code | F5 |
| `codeStop` | EXECUTE | Stop execution | Shift+F5 |
| `codeFormat` | EDIT | Auto-format code | Shift+Alt+F |
| `codeFind` | SEARCH | Find in file | Ctrl+F |
| `codeTerminal` | VIEW | Toggle terminal panel | Ctrl+` |
| `codeAIAssist` | AI | AI code completion | Tab |
| `codeAIDoc` | AI | AI generate documentation | — |

### Text Tab

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `textNew` | PROJECT | New document | Ctrl+N |
| `textOpen` | PROJECT | Open document | Ctrl+O |
| `textSave` | PROJECT | Save document | Ctrl+S |
| `textExport` | EXPORT | Export as TXT/MD/HTML | Ctrl+E |
| `textBold` | FORMAT | Bold text | Ctrl+B |
| `textItalic` | FORMAT | Italic text | Ctrl+I |
| `textUnderline` | FORMAT | Underline text | Ctrl+U |
| `textH1` | FORMAT | Heading 1 | — |
| `textBullet` | FORMAT | Bullet list | — |
| `textLink` | FORMAT | Insert link | Ctrl+K |

### Vision Tab

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `visGen` | GENERATE | Generate 3D from image | Ctrl+G |
| `visDepth` | GENERATE | Generate depth map | — |
| `visNormal` | GENERATE | Generate normal map | — |
| `visExport` | EXPORT | Export 3D model | Ctrl+E |
| `visWireframe` | VIEW | Toggle wireframe | W |

### Library Tab

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `libNewDoc` | PROJECT | Create new document | Ctrl+N |
| `libUpload` | IMPORT | Upload file | Ctrl+U |
| `libRefresh` | VIEW | Refresh library view | F5 |
| `libSearch` | SEARCH | Search library | Ctrl+F |
| `libDocUpload` | IMPORT | Upload training documents | Click |
| `libDocRefresh` | VIEW | Refresh document list | Click |
| `libExport` | EXPORT | Export training data as JSONL | Click |

### Floating Panels

#### Materializer Panel

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `matClose` | PANEL | Close materializer panel | — |
| `matGen` | GENERATE | Materialize idea from prompt | Ctrl+Enter |
| `matType` | CONFIG | Select generation type | — |
| `matExport` | EXPORT | Export result | — |

#### Video Edit NLE Panel

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `vedClose` | PANEL | Close video editor panel | — |
| `vedImport` | IMPORT | Import media files | — |
| `vedCut` | EDIT | Cut at playhead | C |
| `vedPlay` | PLAYBACK | Play/pause | Space |
| `vedExport` | EXPORT | Export video | Ctrl+E |

## 3. FLIGHT SIMULATOR (flight-sim.html)

### Top Bar

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `btnStart` | SIM | Start/Resume flight | — |
| `btnPause` | SIM | Pause flight | P |
| `btnReset` | SIM | Reset simulation | — |
| `btnLaunch` | SIM | Toggle flight engine | — |
| `btnKill` | SIM | Emergency stop (danger) | — |
| `destSelect` | CONFIG | Destination dropdown (7 options) | — |

### Left Panel — Vehicles

| Data Attribute | Tag | Description |
|----------------|-----|-------------|
| `data-vehicle="drone"` | VEHICLE | ZI Drone Swarm — Autonomous UAV |
| `data-vehicle="obsidiana"` | VEHICLE | Obsidiana — Stealth Interceptor |
| `data-vehicle="blackvanta"` | VEHICLE | BlackVanta — Heavy Transport |
| `data-vehicle="zironsigma"` | VEHICLE | ZIron Sigma — Orbital Maneuvering |
| `data-vehicle="zivoyager"` | VEHICLE | ZI Voyager — Deep Space Explorer |
| `data-vehicle="xwing"` | VEHICLE | X-Wing — Starfighter (Star Wars) |
| `data-vehicle="freespace"` | VEHICLE | GT Begasus — Terran Bomber (FreeSpace 2) |

### Right Panel — Controls

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `thrustSlider` | PROPULSION | Engine thrust 0-100% | ↑/↓ |
| `ctrlPitchUp` | FLIGHT | Pitch up | W |
| `ctrlPitchDown` | FLIGHT | Pitch down | S |
| `ctrlRollLeft` | FLIGHT | Roll left | A |
| `ctrlRollRight` | FLIGHT | Roll right | D |
| `ctrlYawLeft` | FLIGHT | Yaw left | Q |
| `ctrlYawRight` | FLIGHT | Yaw right | E |
| `ctrlThrustUp` | PROPULSION | Increase thrust | ↑ |
| `ctrlThrustDown` | PROPULSION | Decrease thrust | ↓ |
| `ctrlRcs` | PROPULSION | Toggle RCS thrusters | — |
| `ctrlGear` | SYSTEMS | Toggle landing gear | G |
| `ctrlLights` | SYSTEMS | Toggle navigation lights | L |
| `ctrlNav` | NAV | Toggle navigation mode | N |
| `openConfig()` | CONFIG | Open aircraft config panel | — |

### Star Wars Launchers

| Button | Tag | Description |
|--------|-----|-------------|
| `launchStarWars('xwa')` | STARWARS | Launch X-Wing Alliance HTML5 sim |
| `launchStarWars('fs2')` | STARWARS | Launch FreeSpace 2 HTML5 sim |

## 4. X-WING ALLIANCE SIM (xwing.html)

| Key | Tag | Description |
|-----|-----|-------------|
| W/S | FLIGHT | Pitch up/down |
| A/D | FLIGHT | Roll left/right |
| ↑/↓ | PROPULSION | Thrust up/down |
| Space | WEAPON | Fire laser cannons |
| F | SYSTEMS | Toggle S-foils (attack position) |
| G | SYSTEMS | Recharge shields |
| R | NAV | Target lock nearest enemy |
| X | NAV | Toggle hyperdrive |

## 5. FREESPACE 2 SIM (freespace2.html)

| Key | Tag | Description |
|-----|-----|-------------|
| W/S | FLIGHT | Pitch up/down |
| A/D | FLIGHT | Yaw left/right |
| ↑/↓ | PROPULSION | Thrust up/down |
| Space | WEAPON | Fire fusion cannons |
| B | WEAPON | Drop bomb |
| C | PROPULSION | Afterburner toggle |
| G | SYSTEMS | Recharge shields |
| R | NAV | Target lock nearest Shivan |

## 6. EMULATORJS GAMES MENU

| Button ID | Tag | Description | Shortcut |
|-----------|-----|-------------|----------|
| `launchGame(name)` | GAME | Launch HTML5 game in canvas | Click |
| `launchROM(file)` | GAME | Load ROM into emulator | Click |
| `btnUpload` | IMPORT | Upload ROM file | — |
| `btnRefresh` | VIEW | Refresh game list | F5 |

## 7. WEBAMP MUSIC PLAYER

| Button | Tag | Description |
|--------|-----|-------------|
| Play | PLAYBACK | Play track |
| Pause | PLAYBACK | Pause track |
| Stop | PLAYBACK | Stop track |
| Previous | PLAYBACK | Previous track |
| Next | PLAYBACK | Next track |
| Volume | MIXER | Volume slider |
| EQ | EFFECT | Equalizer toggle |
| Shuffle | PLAYBACK | Shuffle mode |
| Repeat | PLAYBACK | Repeat mode |

---

**Total: 180+ buttons/controls across 7 interfaces**
**Signed by ZineMotion**
