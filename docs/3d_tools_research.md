# ZICORE 3D Tools & API Research Report

> **Generated**: 2026-07-13  
> **Context**: ZICORE System v5.0 — Aerospace OS  
> **Constraint**: No GPU available (CPU-only operation required)  
> **Priority**: Free/open source, Python API, CPU-compatible, aerospace-applicable

---

## TIER 1: ESSENTIAL (Already in codebase or trivially integrable)

### 1. trimesh[easy]

| Property | Value |
|----------|-------|
| **URL** | https://trimesh.org |
| **GitHub** | https://github.com/mikedh/trimesh |
| **License** | MIT |
| **CPU Support** | Yes — CPU-only (no GPU needed) |
| **Python API** | Native Python library |
| **Install** | `pip install trimesh[easy]` |
| **Already in ZICORE** | Yes — used extensively in `web_server.py`, `materializer.py`, `generator.py` |

**What it does**: The foundational 3D mesh library for ZICORE. Loads/saves STL, PLY, OBJ, GLTF/GLB. Creates primitives (box, sphere, cylinder, cone, capsule, torus). Boolean operations (union, difference, intersection) via `manifold3d`. Voxelize meshes. Convex hull, bounding boxes, ray casting, spatial queries. Path operations for 2D.

**Extras via `trimesh[easy]`**:
- `scipy` — convex hull, spatial queries, KD-trees
- `networkx` — graph operations on mesh connectivity
- `manifold3d` — fast mesh boolean operations (intersection, union, difference)
- `shapely` + `rtree` — vector path handling, spatial indexing
- `lxml` — XML 3D formats (3MF, 3DXML, XAML)
- `embreex` — fast ray queries
- `xxhash` — faster cache checks
- `scikit-image` — voxel operations
- `pyglet` — preview windows (optional)
- `openctm` — CTM format support
- `mapbox-earcut` — fast triangulation

**Aerospace relevance**: Already the backbone of ZICORE's 3D generation. All parametric shapes, STL/OBJ export, mesh manipulation.

---

### 2. CadQuery

| Property | Value |
|----------|-------|
| **URL** | https://cadquery.org |
| **GitHub** | https://github.com/CadQuery/cadquery |
| **License** | Apache 2.0 |
| **CPU Support** | Yes — CPU-only (OpenCASCADE kernel, no GPU needed) |
| **Python API** | Native Python library |
| **Install** | `pip install cadquery` (or `mamba install -c conda-forge cadquery`) |
| **Latest** | v2.8.0 (2026-06-20) |

**What it does**: Parametric CAD scripting framework built on OpenCASCADE (OCCT) kernel. Creates precise BREP (Boundary REPresentation) models. Supports CSG (constructive solid geometry), extrusions, lofts, sweeps, fillets, chamfers. Exports STEP, STL, VRML, AMF. Imports/exports DXF. Includes CQ-editor GUI (optional).

**Key features for ZICORE**:
- Parametric design: `cq.Workplane("XY").box(2,2,2).fillet(0.1)`
- Complex aerospace parts: brackets, housings, manifolds
- STEP export for interchange with SolidWorks/Fusion360
- Full CSG: union, difference, intersection
- Mathematical operations on geometry
- Assembly support

**Install options**:
```bash
# Best method (conda)
mamba install -c conda-forge cadquery

# Pip method (limited Python 3.9-3.12)
pip install cadquery
```

**Aerospace relevance**: CRITICAL — this is the parametric CAD engine for designing precise aerospace components (brackets, structural parts, manifolds, enclosures, mounting hardware).

---

### 3. Build123d

| Property | Value |
|----------|-------|
| **URL** | https://build123d.readthedocs.io |
| **GitHub** | https://github.com/gumyr/build123d |
| **License** | Apache 2.0 |
| **CPU Support** | Yes — CPU-only (OpenCASCADE kernel) |
| **Python API** | Native Python library |
| **Install** | `pip install build123d` |
| **Latest** | v0.11.1 (2026-07-02) |

**What it does**: Modern evolution of CadQuery. Pythonic parametric CAD using context managers (`with` blocks) instead of method chaining. Same OpenCASCADE kernel. Full BREP modeling with algebraic operators. Supports for-loops, references, object sorting. Exports STEP, STL, SVG. Imports from many formats.

**Key advantages over CadQuery**:
- Context manager pattern: `with BuildPart() as part: with Box(1,2,3): ...`
- More Pythonic: uses standard Python control flow
- Richer type hints and IDE support
- Operator-driven: `obj += sub_obj`, `Plane.XZ * Pos(X=5) * Rectangle(1, 1)`
- PEP 8 compliant, mypy/pylint support

**Aerospace relevance**: Excellent for parametric aerospace parts. Could replace or complement CadQuery. Better for complex parametric workflows.

---

### 4. SolidPython2 (OpenSCAD Python bindings)

| Property | Value |
|----------|-------|
| **URL** | https://github.com/jeff-dh/SolidPython |
| **PyPI** | https://pypi.org/project/solidpython2/ |
| **License** | LGPL-2.1 |
| **CPU Support** | Yes — generates OpenSCAD code (runs CPU-side) |
| **Python API** | Native Python library |
| **Install** | `pip install solidpython2` |
| **Latest** | v2.1.3 (2025-08-16) |

**What it does**: Python frontend for OpenSCAD's declarative geometry language. Generates valid OpenSCAD code from Python. Supports BOSL2 library. Customizer support, animation support, custom fonts, ImplicitCAD support. Exports via OpenSCAD renderer to STL, OBJ, AMF, 3MF, OFF, CSG.

**Key features**:
- `from solid2 import *` — full OpenSCAD API in Python
- `sphere(1) + cube(2) - cylinder(r=0.5, h=3)` — CSG operators
- BOSL2 support for advanced parametric modeling
- Customizer support for parameter UIs
- Exports to all OpenSCAD formats

**Install**:
```bash
pip install solidpython2
# Requires OpenSCAD binary in PATH for rendering
```

**Aerospace relevance**: Good for parametric CSG models. OpenSCAD is mature for precise mechanical parts. BOSL2 adds parametric joints, screws, threads.

---

## TIER 2: HIGH VALUE (Direct integrations available)

### 5. Open3D

| Property | Value |
|----------|-------|
| **URL** | https://www.open3d.org |
| **GitHub** | https://github.com/isl-org/Open3D |
| **License** | MIT |
| **CPU Support** | Yes — `pip install open3d-cpu` (smaller CPU-only wheel) |
| **Python API** | Native Python library (pybind11) |
| **Install** | `pip install open3d` or `pip install open3d-cpu` |

**What it does**: Point cloud processing, mesh reconstruction, registration (ICP), segmentation, feature extraction, surface reconstruction, visualization. Reads PLY, PCD, OBJ, STL. Filters, normals estimation, Poisson reconstruction. 3D object detection. RGBD image processing.

**Key features for ZICORE**:
- Point cloud processing from LIDAR/scans
- Mesh simplification and reconstruction
- ICP registration for aligning scans
- DBSCAN clustering
- Voxel grid operations
- Depth image to point cloud conversion
- Real-time 3D visualization

**Aerospace relevance**: HIGH — processing scan data, point clouds from LIDAR, mesh reconstruction from sensor data, 3D reconstruction for digital twins.

---

### 6. PyMeshLab

| Property | Value |
|----------|-------|
| **URL** | https://pymeshlab.readthedocs.io |
| **GitHub** | https://github.com/cnr-isti-vclab/PyMeshLab |
| **License** | BSD 3-Clause |
| **CPU Support** | Yes — CPU-only |
| **Python API** | Native Python library (pybind11) |
| **Install** | `pip install pymeshlab` |

**What it does**: Python interface to MeshLab — the gold standard for mesh processing. 400+ mesh processing filters. Cleaning (remove duplicates, close holes, repair), simplification (quadric edge collapse, vertex clustering), remeshing (isotropic, Montecarlo), smoothing, curvature estimation, color/texture operations, measuring.

**Key features**:
- `ms.meshing_remove_duplicate_vertices()`
- `ms.meshing_close_holes(max_hole_size=100)`
- `ms.meshing_decimation_quadric_edge_collapse(targetfacenum=10000)`
- `ms.meshing_isotropic_explicit_remeshing(targetlen=0.5)`
- Boolean operations via `mesh_boolean_operations`
- Voxelization
- Full color/texture processing

**Aerospace relevance**: HIGH — mesh repair, simplification for simulation, quality assurance of generated meshes, decimation for real-time visualization.

---

### 7. Hunyuan3D (already in codebase)

| Property | Value |
|----------|-------|
| **URL** | https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1 |
| **License** | Custom (Tencent) |
| **CPU Support** | No — requires GPU (CUDA). 10GB+ VRAM for shape, 21GB+ for texture |
| **Python API** | Yes — `hy3dgen` package |
| **Install** | `pip install -e .` (from source) |
| **Latest** | v2.1 (2025-06-13) — fully open-sourced with PBR, VAE encoder, all training code |
| **Already in ZICORE** | Yes — `zicore/hunyuan3d_engine.py` with trimesh fallback |

**Current status**: Hunyuan3D is the primary AI text/image-to-3D engine. Currently falls back to trimesh when no GPU is detected.

**Latest capabilities**:
- Image-to-shape generation (Hunyuan3D-DiT, 3.3B params)
- Texture synthesis with PBR materials (Hunyuan3D-Paint, 2B params)
- Docker containerization available (70GB+ image, needs nvidia-container-toolkit)
- REST API server (`python api_server.py`)
- Gradio web UI
- Blender addon
- Diffusers-like Python API

**GPU requirement**: This is the key limitation. On .85 server (GT 230, CC 1.1) this will NOT work. Needs a GPU-equipped server.

**Aerospace relevance**: MEDIUM — excellent for concept visualization, but not for precision engineering. Good for generating rough shapes from descriptions.

---

### 8. PicoGK (via PicoPie)

| Property | Value |
|----------|-------|
| **URL** | https://github.com/leap71/PicoGK |
| **Python binding** | https://github.com/Borderliner/PicoPie (picopie) |
| **License** | Apache 2.0 (PicoGK), Apache 2.0 (PicoPie) |
| **CPU Support** | Yes — CPU-only (OpenVDB-based voxel engine) |
| **Python API** | Yes — `pip install picopie` |
| **Install** | `pip install picopie` |

**What it does**: LEAP 71's computational geometry kernel for engineering. Voxel/level-set modeling on OpenVDB. Parametric shapes (Sphere, Box, Cylinder, Cone, Ring, Lens, Pipe, Revolve), boolean operations, offsets, shell/hollow, implicit SDF modeling (gyroid, super-ellipsoid), lattice structures, mesh conversion. Exports STL/OBJ/VDB.

**Key features**:
- `picopie.init(voxel_size_mm=0.2)` — initialize
- `Voxels.sphere()`, `Voxels.capsule()` — primitives
- Boolean: `+ - &` operators
- `shell_()` — hollow parts
- `calculate_properties()` — volume, area, center of gravity, inertia
- Implicit SDF: gyroid, TPMS, super-ellipsoid
- Lattice structures for lightweighting
- Web viewer for Jupyter/VS Code
- Self-contained wheels for Linux/macOS/Windows

**Aerospace relevance**: HIGH — designed for computational engineering. Lattice structures for lightweight aerospace parts, TPMS for heat exchangers, implicit surfaces for aerodynamic shapes.

---

## TIER 3: AI TEXT/IMAGE-TO-3D (Cloud API or GPU-dependent)

### 9. Tripo AI (Tripo3D)

| Property | Value |
|----------|-------|
| **URL** | https://tripo3d.ai |
| **GitHub** | https://github.com/VAST-AI-Research/tripo-python-sdk |
| **License** | MIT (SDK), API terms apply |
| **CPU Support** | Yes — cloud API (no local GPU needed) |
| **Python API** | Yes — `pip install tripo3d` |
| **Install** | `pip install tripo3d` |
| **Latest SDK** | v0.4.2 (2026-07-01) |

**What it does**: Cloud-based text-to-3D and image-to-3D generation. Full PBR materials. Mesh editing, segmentation, completion. Model animation (auto-rig + retarget). Multi-view to 3D. External model import (GLB/OBJ/FBX/STL). Model conversion and stylization.

**Pricing**:
- Basic: Free (300 credits/month, 1 concurrent task)
- Professional: $15.90/month (3,000 credits)
- Text-to-3D: ~10-20 credits ($0.10-0.20)
- Image-to-3D: ~20-30 credits ($0.20-0.30)

**Python usage**:
```python
import asyncio
from tripo3d import TripoClient, TaskStatus

async def generate():
    async with TripoClient(api_key="YOUR_KEY") as client:
        task_id = await client.text_to_model(prompt="a satellite dish")
        task = await client.wait_for_task(task_id)
        if task.status == TaskStatus.SUCCESS:
            files = await client.download_task_models(task, "./output")
asyncio.run(generate())
```

**Aerospace relevance**: HIGH — free tier for concept generation. Good for rapid prototyping of aerospace concepts from text descriptions.

---

### 10. Meshy AI

| Property | Value |
|----------|-------|
| **URL** | https://www.meshy.ai |
| **Docs** | https://docs.meshy.ai |
| **License** | API terms (commercial) |
| **CPU Support** | Yes — cloud API |
| **Python API** | Yes — REST API (no official SDK, but well-documented) |
| **Install** | `pip install requests` (REST API) |

**What it does**: Cloud text-to-3D and image-to-3D. Two-step workflow: preview (geometry only) then refine (texture). PBR materials. Exports GLB, OBJ, FBX, USDZ, STL, 3MF. Streaming support. Batch generation.

**Pricing**: Free tier available (limited). Paid plans for production.

**REST API usage**:
```python
import requests
headers = {"Authorization": f"Bearer {API_KEY}"}
# Preview
resp = requests.post("https://api.meshy.ai/openapi/v2/text-to-3d",
    headers=headers, json={"mode": "preview", "prompt": "rocket nozzle"})
# Refine
resp = requests.post("https://api.meshy.ai/openapi/v2/text-to-3d",
    headers=headers, json={"mode": "refine", "preview_task_id": task_id})
```

**MCP server**: `@meshy-ai/meshy-mcp-server` (npm) — integrates with Claude Code, Cursor, Windsurf.

**Aerospace relevance**: MEDIUM — good for concept visualization, not precision engineering.

---

### 11. Rodin Gen-1 (Hyper3D)

| Property | Value |
|----------|-------|
| **URL** | https://hyper3d.ai |
| **API Docs** | https://developer.hyper3d.ai |
| **License** | API terms (commercial) |
| **CPU Support** | Yes — cloud API |
| **Python API** | REST API only |
| **Install** | `curl` / `requests` |

**What it does**: Text-to-3D and image-to-3D. Multi-image support (up to 5 images, fuse or concat modes). PBR materials. Configurable face count (4K-200K). Quad mesh output. Mesh simplification and smoothing. Exports GLB, USDZ, FBX, OBJ, STL.

**REST API usage**:
```bash
curl https://api.hyper3d.com/api/v2/rodin \
  -H "Authorization: Bearer ${RODIN_API_KEY}" \
  -F "prompt=A 3D model of a rocket engine nozzle" \
  -F "geometry_file_format=glb" \
  -F "material=PBR"
```

**Aerospace relevance**: MEDIUM — concept generation from images/text. Quad mesh output is nice for CAD workflows.

---

### 12. Shap-E (OpenAI)

| Property | Value |
|----------|-------|
| **URL** | https://github.com/openai/shap-e |
| **License** | MIT |
| **CPU Support** | Yes — but very slow (minutes instead of seconds) |
| **Python API** | Yes — via `diffusers` library |
| **Install** | `pip install -e .` (from repo) or via `diffusers` |

**What it does**: Conditional generative model for 3D assets from text or images. Outputs implicit representations renderable as textured meshes or NeRFs. Trained on large 3D dataset. Generates PLY and OBJ files.

**Python usage (via diffusers)**:
```python
import torch
from diffusers import ShapEPipeline
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
pipe = ShapEPipeline.from_pretrained("openai/shap-e", torch_dtype=torch.float16)
pipe = pipe.to(device)
images = pipe("a rocket nozzle", guidance_scale=15.0, num_inference_steps=64).images
```

**CPU performance**: Works but slow (~minutes per generation). 7-8GB VRAM on GPU. CPU fallback is viable for testing.

**Aerospace relevance**: LOW-MEDIUM — generates general 3D objects, not precise engineering parts. Could be useful for concept visualization.

---

### 13. InstantMesh

| Property | Value |
|----------|-------|
| **URL** | https://github.com/TencentARC/InstantMesh |
| **License** | Apache 2.0 |
| **CPU Support** | No — requires GPU (CUDA 12.1+) |
| **Python API** | Yes — command-line and Python |
| **Install** | From source |

**What it does**: Feed-forward framework for efficient 3D mesh generation from a single image. Uses multi-view diffusion + sparse-view reconstruction. Creates diverse 3D assets within 10 seconds on GPU. FlexiCubes for mesh extraction.

**GPU requirement**: Needs NVIDIA GPU with CUDA. Not suitable for ZICORE's current hardware.

**Aerospace relevance**: LOW for current setup — requires GPU. Good for future GPU-equipped servers.

---

### 14. TRELLIS (Microsoft)

| Property | Value |
|----------|-------|
| **URL** | https://github.com/microsoft/TRELLIS |
| **License** | MIT |
| **CPU Support** | No — requires GPU (16GB+ VRAM, tested on A100/A6000) |
| **Python API** | Yes — `TrellisImageTo3DPipeline` |
| **Install** | Conda environment, from source |
| **PyPI** | `pip install trellis-3d-python` |

**What it does**: Large 3D asset generation model. Text/image to 3D. Outputs Radiance Fields, 3D Gaussians, and meshes. Structured LATent (SLAT) representation. Up to 2B parameters. Trained on 500K 3D assets. Local 3D editing capabilities.

**GPU requirement**: Needs NVIDIA GPU with 16GB+ VRAM. Not suitable for ZICORE's current hardware.

**Aerospace relevance**: LOW for current setup — requires GPU. Excellent for future GPU servers.

---

### 15. Hitem3D / Hi3D

| Property | Value |
|----------|-------|
| **URL** | https://hitem3d.ai |
| **API Docs** | https://docs.hitem3d.ai |
| **License** | API terms (commercial) |
| **CPU Support** | Yes — cloud API |
| **Python API** | REST API |
| **Install** | `requests` library |

**What it does**: AI-powered image-to-3D generation using proprietary Sparc3D and Ultra3D models. Single image input. Multi-view to 3D. Geometry+texture all-in-one generation. PBR support. Exports OBJ, GLB, STL, FBX, USDZ. Resolution up to 1536³.

**REST API**: `POST /open-api/v1/submit-task` with multipart/form-data.

**Aerospace relevance**: LOW — commercial API, generates general objects not precision parts.

---

## TIER 4: MESH PROCESSING UTILITIES

### 16. mesh-voronoi (Voronoi generators)

| Property | Value |
|----------|-------|
| **URL** | https://github.com/FelixBuchele/mesh-voronoi |
| **License** | MIT |
| **CPU Support** | Yes — CPU-only |
| **Python API** | Direct Python script |
| **Install** | `conda create -n mesh-voronoi python=3.10 numpy scipy pyvista trimesh; pip install manifold3d` |

**What it does**: Splits STL meshes into multiple parts using 3D Voronoi tessellation. Places seed points inside mesh volume, constructs bounded Voronoi cells via half-space intersections, clips each cell against input geometry. Exports individual watertight STL files per cell.

**Use case**: Multi-color 3D printing, lightweight lattice structures, aesthetic perforations.

**Also useful**: `voronoizer` (https://github.com/gabr42/voronoizer) — creates Voronoi-perforated shells from STL files.

---

### 17. lattice300

| Property | Value |
|----------|-------|
| **URL** | https://github.com/ivncl/lattice300 |
| **License** | Open source |
| **CPU Support** | Yes (uses gmsh) |
| **Python API** | Yes |
| **Install** | `pip install gmsh trimesh` |

**What it does**: Generates Voronoi and Delaunay 3D reticula (lattice structures). Poisson Disk Sampling with arbitrary density functions. Variable strut diameter. Bounded by any STL shape. Exports high-quality tetrahedral meshes.

**Aerospace relevance**: HIGH — lattice structures for lightweight aerospace components, heat exchangers, energy absorption.

---

## SUMMARY TABLE: CPU-Compatible Tools Ranked by ZICORE Relevance

| Rank | Tool | Type | CPU | Python API | Install | ZICORE Relevance |
|------|------|------|-----|------------|---------|-----------------|
| 1 | **trimesh[easy]** | Mesh library | Yes | Native | `pip install trimesh[easy]` | CRITICAL (already in use) |
| 2 | **CadQuery** | Parametric CAD | Yes | Native | `pip install cadquery` | CRITICAL — precision parts |
| 3 | **Build123d** | Parametric CAD | Yes | Native | `pip install build123d` | HIGH — modern CadQuery alternative |
| 4 | **PicoGK/PicoPie** | Voxel/implicit | Yes | Native | `pip install picopie` | HIGH — lattice, TPMS, implicit |
| 5 | **Open3D** | Point cloud/mesh | Yes | Native | `pip install open3d-cpu` | HIGH — scan processing |
| 6 | **PyMeshLab** | Mesh processing | Yes | Native | `pip install pymeshlab` | HIGH — mesh repair/simplify |
| 7 | **SolidPython2** | OpenSCAD bindings | Yes | Native | `pip install solidpython2` | MEDIUM — CSG via OpenSCAD |
| 8 | **Tripo3D** | Cloud AI 3D | Cloud | SDK | `pip install tripo3d` | MEDIUM — concept gen (free tier) |
| 9 | **Meshy AI** | Cloud AI 3D | Cloud | REST | `requests` | MEDIUM — concept gen |
| 10 | **lattice300** | Lattice gen | Yes | Native | `pip install gmsh trimesh` | MEDIUM — lattice structures |
| 11 | **mesh-voronoi** | Voronoi split | Yes | Script | conda + pip | MEDIUM — Voronoi partitions |
| 12 | **Rodin Gen-1** | Cloud AI 3D | Cloud | REST | `curl`/`requests` | LOW-MED — concept gen |
| 13 | **Shap-E** | AI 3D gen | Slow | Yes | `pip install -e .` | LOW — slow on CPU |
| 14 | **Hunyuan3D** | AI 3D gen | No (GPU) | Yes | Source | LOW — GPU required |
| 15 | **InstantMesh** | AI 3D gen | No (GPU) | Yes | Source | LOW — GPU required |
| 16 | **TRELLIS** | AI 3D gen | No (GPU) | Yes | Source | LOW — GPU required |
| 17 | **Hitem3D** | Cloud AI 3D | Cloud | REST | `requests` | LOW — commercial |

---

## RECOMMENDED INTEGRATION PRIORITY

### Phase 1: Foundation (Already have trimesh)
1. **Add CadQuery** — `pip install cadquery` — parametric CAD for aerospace parts
2. **Add Build123d** — `pip install build123d` — modern parametric CAD
3. **Add Open3D** — `pip install open3d-cpu` — point cloud processing
4. **Add PyMeshLab** — `pip install pymeshlab` — mesh repair/simplification

### Phase 2: Advanced Geometry
5. **Add PicoPie** — `pip install picopie` — voxel/implicit/lattice modeling
6. **Add lattice300** — lattice generation for lightweight structures
7. **Add mesh-voronoi** — Voronoi partitioning for multi-material printing

### Phase 3: AI Generation (Cloud APIs)
8. **Add Tripo3D SDK** — `pip install tripo3d` — free tier for concept generation
9. **Add Meshy AI integration** — REST API for text-to-3D
10. **Add Rodin Gen-1** — REST API for image-to-3D

### Phase 4: Future (GPU Server)
11. **Hunyuan3D** — already integrated, needs GPU server
12. **TRELLIS** — when GPU available
13. **InstantMesh** — when GPU available

---

## INSTALLED PACKAGES LIST (for requirements.txt)

```txt
# Core 3D (already in ZICORE)
trimesh[easy]>=4.0.0
numpy
scipy

# Parametric CAD
cadquery>=2.8.0
build123d>=0.11.0

# Mesh Processing
open3d-cpu>=0.18.0
pymeshlab>=2025.7

# Voxel/Implicit Modeling
picopie>=0.7.0

# OpenSCAD Bindings
solidpython2>=2.1.0

# Voronoi/Lattice (optional)
# mesh-voronoi (script-based)
# lattice300 (pip install gmsh)

# Cloud AI 3D (API keys required)
tripo3d>=0.4.0
# meshy-ai (REST API, no package)
# rodin (REST API, no package)
```

---

*This report covers all 17 requested tools. Priority is given to CPU-compatible, Python-native tools that can integrate directly into ZICORE's materializer pipeline.*
