"""
ZICORE Materializer Engine
Integral system for materializing ideas into reality.

Combines:
- Stable Diffusion (AI Image Generation)
- Procedural Generation (Noise, Cellular Automata, WFC, Voronoi, Fractals, L-Systems)
- 3D Mesh Generation (trimesh, OpenSCAD)
- Audio Synthesis
- Video Generation

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("zicore.materializer")


# =============================================================================
# OUTPUT TYPES
# =============================================================================

class OutputType(Enum):
    """Supported output types"""
    IMAGE = "image"
    MESH_3D = "mesh_3d"
    TERRAIN = "terrain"
    CAVE = "cave"
    DUNGEON = "dungeon"
    PLANT = "plant"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    LEVEL = "level"
    FRACTAL = "fractal"


@dataclass
class MaterializerResult:
    """Result from materialization"""
    success: bool
    output_type: OutputType
    file_path: Optional[str] = None
    data: Optional[Any] = None
    method: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output_type": self.output_type.value,
            "file_path": self.file_path,
            "method": self.method,
            "metadata": self.metadata,
            "error": self.error,
        }


# =============================================================================
# INTENT CLASSIFIER
# =============================================================================

class IntentClassifier:
    """Classify user intent from natural language prompts"""
    
    KEYWORDS = {
        OutputType.IMAGE: [
            "image", "picture", "photo", "draw", "paint", "illustration",
            "artwork", "render", "generate image", "create image", "make image",
            "sunset", "landscape", "portrait", "scene", "concept art",
        ],
        OutputType.MESH_3D: [
            "3d", "model", "mesh", "stl", "obj", "three dimensional",
            "cube", "sphere", "cylinder", "cone", "torus", "rocket",
            "satellite", "drone", "station", "vehicle", "object",
        ],
        OutputType.TERRAIN: [
            "terrain", "heightmap", "landscape", "mountain", "hills",
            "ground", "topography", "elevation", "geography",
        ],
        OutputType.CAVE: [
            "cave", "cavern", "underground", "tunnel", "grotto",
            "dungeon", "catacombs", "hollow",
        ],
        OutputType.DUNGEON: [
            "dungeon", "level", "maze", "labyrinth", "rooms",
            "corridors", "hallway", "chamber",
        ],
        OutputType.PLANT: [
            "plant", "tree", "branch", "leaf", "flower", "foliage",
            "vegetation", "forest", "bush", "vine", "weed",
            "organic", "growth", "nature",
        ],
        OutputType.TEXT: [
            "text", "story", "narrative", "poem", "prose",
            "words", "writing", "content", "essay", "article",
        ],
        OutputType.FRACTAL: [
            "fractal", "mandelbrot", "julia", "sierpinski", "koch",
            "dragon curve", "self-similar", "recursive", "mathematical",
        ],
        OutputType.LEVEL: [
            "level", "map", "tile", "grid", "tilemap", "wfc",
            "wave function collapse", "constraint",
        ],
    }
    
    @classmethod
    def classify(cls, prompt: str) -> OutputType:
        """Classify prompt into output type"""
        prompt_lower = prompt.lower()
        
        # Check each output type
        scores = {}
        for output_type, keywords in cls.KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > 0:
                scores[output_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        # Default to image
        return OutputType.IMAGE


# =============================================================================
# MATERIALIZER ENGINE
# =============================================================================

class ZICOREMaterializer:
    """
    Integral materialization engine.
    Converts text prompts into real content using the best available engine.
    """
    
    def __init__(self, seed: int = None):
        self.seed = seed or int(time.time())
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Lazy-load engines
        self._procedural = None
        self._image_generator = None
        self._mesh_engine = None
        
        logger.info(f"ZICORE Materializer initialized (seed={self.seed})")
    
    @property
    def procedural(self):
        """Lazy-load procedural engine"""
        if self._procedural is None:
            from zicore.procedural import ProceduralEngine
            self._procedural = ProceduralEngine(seed=self.seed)
        return self._procedural
    
    @property
    def image_generator(self):
        """Lazy-load image generator"""
        if self._image_generator is None:
            from zicore.stable_diffusion_engine import ZICOREImageGenerator
            self._image_generator = ZICOREImageGenerator()
        return self._image_generator
    
    @property
    def mesh_engine(self):
        """Lazy-load mesh engine"""
        if self._mesh_engine is None:
            try:
                import trimesh
                self._mesh_engine = trimesh
            except ImportError:
                logger.warning("trimesh not available for 3D generation")
        return self._mesh_engine
    
    # =========================================================================
    # MAIN MATERIALIZATION METHOD
    # =========================================================================
    
    def materialize(self, prompt: str, output_type: OutputType = None,
                    **kwargs) -> MaterializerResult:
        """
        Materialize a prompt into content.
        
        Args:
            prompt: Natural language description of desired output
            output_type: Override output type (auto-detected if None)
            **kwargs: Additional parameters
        
        Returns:
            MaterializerResult with generated content
        """
        start_time = time.time()
        
        # Classify intent if not specified
        if output_type is None:
            output_type = IntentClassifier.classify(prompt)
        
        logger.info(f"Materializing: '{prompt[:60]}...' -> {output_type.value}")
        
        try:
            # Route to appropriate engine
            if output_type == OutputType.IMAGE:
                result = self._materialize_image(prompt, **kwargs)
            elif output_type == OutputType.MESH_3D:
                result = self._materialize_mesh(prompt, **kwargs)
            elif output_type == OutputType.TERRAIN:
                result = self._materialize_terrain(prompt, **kwargs)
            elif output_type == OutputType.CAVE:
                result = self._materialize_cave(prompt, **kwargs)
            elif output_type == OutputType.DUNGEON:
                result = self._materialize_dungeon(prompt, **kwargs)
            elif output_type == OutputType.PLANT:
                result = self._materialize_plant(prompt, **kwargs)
            elif output_type == OutputType.FRACTAL:
                result = self._materialize_fractal(prompt, **kwargs)
            elif output_type == OutputType.LEVEL:
                result = self._materialize_level(prompt, **kwargs)
            elif output_type == OutputType.TEXT:
                result = self._materialize_text(prompt, **kwargs)
            else:
                result = MaterializerResult(
                    success=False,
                    output_type=output_type,
                    error=f"Unsupported output type: {output_type}"
                )
            
            # Add timing metadata
            result.metadata["generation_time"] = time.time() - start_time
            result.metadata["prompt"] = prompt
            result.metadata["seed"] = self.seed
            
            return result
            
        except Exception as e:
            logger.error(f"Materialization failed: {e}")
            return MaterializerResult(
                success=False,
                output_type=output_type,
                error=str(e)
            )
    
    # =========================================================================
    # INDIVIDUAL ENGINES
    # =========================================================================
    
    def _materialize_image(self, prompt: str, **kwargs) -> MaterializerResult:
        """Generate image using Stable Diffusion or procedural fallback"""
        image, method = self.image_generator.generate(
            prompt,
            width=kwargs.get('width', 512),
            height=kwargs.get('height', 512),
            use_sd=kwargs.get('use_sd', True),
        )
        
        if image is None:
            return MaterializerResult(
                success=False,
                output_type=OutputType.IMAGE,
                error="Image generation failed"
            )
        
        # Save image
        filepath = self.image_generator.procedural.save_image(image, prompt)
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.IMAGE,
            file_path=filepath,
            method=method,
            metadata={"size": f"{image.width}x{image.height}"}
        )
    
    def _materialize_mesh(self, prompt: str, **kwargs) -> MaterializerResult:
        """Generate 3D mesh using trimesh"""
        if self.mesh_engine is None:
            return MaterializerResult(
                success=False,
                output_type=OutputType.MESH_3D,
                error="trimesh not available"
            )
        
        try:
            import trimesh
            import numpy as np
            
            prompt_lower = prompt.lower()
            size = kwargs.get('size', 1.0)
            
            # Generate shape based on prompt
            if 'sphere' in prompt_lower or 'ball' in prompt_lower:
                mesh = trimesh.creation.icosphere(subdivisions=3, radius=size)
            elif 'cube' in prompt_lower or 'box' in prompt_lower:
                mesh = trimesh.creation.box(extents=[size, size, size])
            elif 'cylinder' in prompt_lower:
                mesh = trimesh.creation.cylinder(radius=size/2, height=size*2)
            elif 'cone' in prompt_lower:
                mesh = trimesh.creation.cone(radius=size/2, height=size*2)
            elif 'torus' in prompt_lower or 'ring' in prompt_lower:
                mesh = trimesh.creation.annulus(r_min=size*0.3, r_max=size, height=size*0.2)
            elif 'rocket' in prompt_lower or 'ship' in prompt_lower:
                # Composite rocket shape
                body = trimesh.creation.cylinder(radius=size*0.2, height=size*1.5)
                nose = trimesh.creation.cone(radius=size*0.2, height=size*0.5)
                nose.apply_translation([0, 0, size])
                fin1 = trimesh.creation.box(extents=[size*0.4, size*0.05, size*0.3])
                fin1.apply_translation([0, 0, -size*0.5])
                mesh = trimesh.util.concatenate([body, nose, fin1])
            else:
                # Default to sphere
                mesh = trimesh.creation.icosphere(subdivisions=2, radius=size)
            
            # Export to STL
            timestamp = int(time.time())
            safe_prompt = "".join(c for c in prompt[:20] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_prompt = safe_prompt.replace(' ', '_')
            filename = f"mesh_{safe_prompt}_{timestamp}.stl"
            filepath = self.output_dir / "3d" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            mesh.export(str(filepath))
            
            return MaterializerResult(
                success=True,
                output_type=OutputType.MESH_3D,
                file_path=str(filepath),
                method="trimesh",
                metadata={
                    "vertices": len(mesh.vertices),
                    "faces": len(mesh.faces),
                    "volume": float(mesh.volume) if mesh.is_watertight else None,
                }
            )
            
        except Exception as e:
            return MaterializerResult(
                success=False,
                output_type=OutputType.MESH_3D,
                error=str(e)
            )
    
    def _materialize_terrain(self, prompt: str, **kwargs) -> MaterializerResult:
        """Generate terrain heightmap"""
        width = kwargs.get('width', 256)
        height = kwargs.get('height', 256)
        scale = kwargs.get('scale', 50.0)
        mountains = 'mountain' in prompt.lower() or 'peak' in prompt.lower()
        
        terrain = self.procedural.generate_terrain(width, height, scale, mountains)
        
        # Save as image
        timestamp = int(time.time())
        filename = f"terrain_{timestamp}.png"
        filepath = self.output_dir / "terrain" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        self.procedural.generate_heightmap_image(terrain, str(filepath))
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.TERRAIN,
            file_path=str(filepath),
            method="perlin_noise",
            metadata={"size": f"{width}x{height}", "scale": scale}
        )
    
    def _materialize_cave(self, prompt: str, **kwargs) -> MaterializerResult:
        """Generate cave system"""
        width = kwargs.get('width', 80)
        height = kwargs.get('height', 40)
        fill_prob = kwargs.get('fill_prob', 0.4)
        iterations = kwargs.get('iterations', 5)
        
        cave = self.procedural.cellular_cave(width, height, fill_prob, iterations)
        
        # Save as image
        timestamp = int(time.time())
        filename = f"cave_{timestamp}.png"
        filepath = self.output_dir / "caves" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        self.procedural.generate_cave_image(cave, str(filepath))
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.CAVE,
            file_path=str(filepath),
            method="cellular_automata",
            metadata={"size": f"{width}x{height}", "iterations": iterations}
        )
    
    def _materialize_dungeon(self, prompt: str, **kwargs) -> MaterializerResult:
        """Generate dungeon layout"""
        width = kwargs.get('width', 40)
        height = kwargs.get('height', 30)
        num_rooms = kwargs.get('num_rooms', 8)
        
        dungeon = self.procedural.generate_dungeon(width, height, num_rooms)
        
        # Save as ASCII and image
        timestamp = int(time.time())
        
        # ASCII
        ascii_filename = f"dungeon_{timestamp}.txt"
        ascii_filepath = self.output_dir / "dungeons" / ascii_filename
        ascii_filepath.parent.mkdir(parents=True, exist_ok=True)
        
        ascii_content = self.procedural.grid_to_ascii(
            dungeon,
            {0: '#', 1: '#', 2: '.', 3: '+'}
        )
        ascii_filepath.write_text(ascii_content)
        
        # Image
        img_filename = f"dungeon_{timestamp}.png"
        img_filepath = self.output_dir / "dungeons" / img_filename
        self.procedural.generate_cave_image(dungeon, str(img_filepath))
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.DUNGEON,
            file_path=str(ascii_filepath),
            method="bsp_dungeon",
            metadata={
                "size": f"{width}x{height}",
                "rooms": num_rooms,
                "ascii_file": str(ascii_filepath),
                "image_file": str(img_filepath),
            }
        )
    
    def _materialize_plant(self, prompt: str, **kwargs) -> MaterializerResult:
        """Generate plant using L-System"""
        iterations = kwargs.get('iterations', 5)
        angle = kwargs.get('angle', 25.0)
        
        # Generate L-System
        instructions = self.procedural.plant_l_system(iterations)
        
        # Interpret as turtle graphics
        lines = self.procedural.interpret_turtle(instructions, angle=angle)
        
        # Save as SVG
        timestamp = int(time.time())
        filename = f"plant_{timestamp}.svg"
        filepath = self.output_dir / "plants" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Calculate bounds
        all_points = [p for line in lines for p in line]
        if all_points:
            min_x = min(p[0] for p in all_points)
            max_x = max(p[0] for p in all_points)
            min_y = min(p[1] for p in all_points)
            max_y = max(p[1] for p in all_points)
            
            width = max_x - min_x + 20
            height = max_y - min_y + 20
            
            # Generate SVG
            svg_lines = [
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x-10} {min_y-10} {width} {height}">',
                '<rect fill="#0a0f19" width="100%" height="100%"/>',
                '<g stroke="#00e5ff" stroke-width="0.5" fill="none">',
            ]
            
            for (x1, y1), (x2, y2) in lines:
                svg_lines.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
            
            svg_lines.extend(['</g>', '</svg>'])
            
            filepath.write_text('\n'.join(svg_lines))
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.PLANT,
            file_path=str(filepath),
            method="l_system",
            metadata={
                "iterations": iterations,
                "angle": angle,
                "segments": len(lines),
                "instructions_length": len(instructions),
            }
        )
    
    def _materialize_fractal(self, prompt: str, **kwargs) -> MaterializerResult:
        """Generate fractal"""
        prompt_lower = prompt.lower()
        width = kwargs.get('width', 400)
        height = kwargs.get('height', 300)
        max_iter = kwargs.get('max_iter', 100)
        
        timestamp = int(time.time())
        
        if 'mandelbrot' in prompt_lower:
            fractal = self.procedural.mandelbrot(width, height, max_iter)
            name = "mandelbrot"
        elif 'julia' in prompt_lower:
            cx = kwargs.get('cx', -0.7)
            cy = kwargs.get('cy', 0.27015)
            fractal = self.procedural.julia_set(width, height, cx, cy, max_iter)
            name = "julia"
        else:
            fractal = self.procedural.mandelbrot(width, height, max_iter)
            name = "mandelbrot"
        
        # Save as image
        filename = f"fractal_{name}_{timestamp}.png"
        filepath = self.output_dir / "fractals" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        self.procedural.generate_fractal_image(fractal, str(filepath))
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.FRACTAL,
            file_path=str(filepath),
            method=f"fractal_{name}",
            metadata={"size": f"{width}x{height}", "max_iter": max_iter}
        )
    
    def _materialize_level(self, prompt: str, **kwargs) -> MaterializerResult:
        """Generate level using Wave Function Collapse"""
        width = kwargs.get('width', 20)
        height = kwargs.get('height', 20)
        num_tile_types = kwargs.get('num_tile_types', 4)
        
        level = self.procedural.wave_function_collapse(width, height, num_tile_types)
        
        # Save as JSON and ASCII
        timestamp = int(time.time())
        
        # JSON
        json_filename = f"level_{timestamp}.json"
        json_filepath = self.output_dir / "levels" / json_filename
        json_filepath.parent.mkdir(parents=True, exist_ok=True)
        json_filepath.write_text(json.dumps(level, indent=2))
        
        # ASCII
        ascii_filename = f"level_{timestamp}.txt"
        ascii_filepath = self.output_dir / "levels" / ascii_filename
        
        symbols = {0: '.', 1: '#', 2: ' ', 3: '+'}
        ascii_content = "\n".join(
            "".join(symbols.get(cell, '?') for cell in row)
            for row in level
        )
        ascii_filepath.write_text(ascii_content)
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.LEVEL,
            file_path=str(json_filepath),
            method="wave_function_collapse",
            metadata={
                "size": f"{width}x{height}",
                "tile_types": num_tile_types,
                "ascii_file": str(ascii_filepath),
            }
        )
    
    def _materialize_text(self, prompt: str, **kwargs) -> MaterializerResult:
        """Generate text using Markov chains"""
        length = kwargs.get('length', 200)
        order = kwargs.get('order', 2)
        
        # Use prompt as corpus seed
        corpus = prompt * 10  # Repeat prompt for more material
        
        text = self.procedural.markov_text(corpus, length, order)
        
        # Save as text file
        timestamp = int(time.time())
        filename = f"text_{timestamp}.txt"
        filepath = self.output_dir / "text" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(text)
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.TEXT,
            file_path=str(filepath),
            method="markov_chain",
            metadata={"length": len(text), "order": order}
        )
    
    # =========================================================================
    # BATCH MATERIALIZATION
    # =========================================================================
    
    def materialize_batch(self, prompts: List[str], **kwargs) -> List[MaterializerResult]:
        """Materialize multiple prompts"""
        results = []
        for prompt in prompts:
            result = self.materialize(prompt, **kwargs)
            results.append(result)
        return results
    
    def materialize_all_types(self, base_prompt: str = "ZICORE",
                              **kwargs) -> Dict[str, MaterializerResult]:
        """Generate one of each type for demonstration"""
        results = {}
        
        for output_type in OutputType:
            result = self.materialize(base_prompt, output_type=output_type, **kwargs)
            results[output_type.value] = result
        
        return results
    
    # =========================================================================
    # STATUS AND CONFIGURATION
    # =========================================================================
    
    def get_status(self) -> dict:
        """Get materializer status"""
        return {
            "seed": self.seed,
            "output_dir": str(self.output_dir),
            "engines": {
                "procedural": "always_available",
                "stable_diffusion": self.image_generator.sd_engine.is_available(),
                "trimesh": self.mesh_engine is not None,
            },
            "supported_types": [t.value for t in OutputType],
        }
    
    def set_seed(self, seed: int):
        """Set random seed"""
        self.seed = seed
        if self._procedural:
            self._procedural.seed = seed


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_materializer(seed: int = None) -> ZICOREMaterializer:
    """Create a new Materializer instance"""
    return ZICOREMaterializer(seed=seed)


# =============================================================================
# ZINEMOTION SIGNATURE
# =============================================================================

__author__ = "ZineMotion Foundation — Aerospace Division"
__version__ = "5.0.0"
__license__ = "ZICORE System"

if __name__ == "__main__":
    # Demo
    print("=== ZICORE Materializer Engine v5.0.0 ===")
    print(f"Author: {__author__}\n")
    
    mat = create_materializer(seed=42)
    status = mat.get_status()
    
    print("Status:")
    for key, value in status.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")
    
    print("\nGenerating sample content...")
    
    # Generate terrain
    result = mat.materialize("mountain landscape", OutputType.TERRAIN, width=64, height=64)
    print(f"  Terrain: {result.success} - {result.file_path}")
    
    # Generate cave
    result = mat.materialize("underground cavern", OutputType.CAVE)
    print(f"  Cave: {result.success} - {result.file_path}")
    
    # Generate plant
    result = mat.materialize("tree branch", OutputType.PLANT, iterations=4)
    print(f"  Plant: {result.success} - {result.file_path}")
    
    # Generate fractal
    result = mat.materialize("mandelbrot set", OutputType.FRACTAL, width=100, height=75)
    print(f"  Fractal: {result.success} - {result.file_path}")
    
    # Generate dungeon
    result = mat.materialize("dungeon level", OutputType.DUNGEON, width=30, height=20)
    print(f"  Dungeon: {result.success} - {result.file_path}")
    
    print("\n=== Materialization Complete ===")
