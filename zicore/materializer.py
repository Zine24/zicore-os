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
    SIMULATION = "simulation"


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
        OutputType.AUDIO: [
            "audio", "sound", "music", "melody", "beat", "ambient",
            "noise", "synth", "sfx", "effects", "voice", "sing",
            "drone", "chord", "laser", "explosion", "whoosh", "beep",
        ],
        OutputType.VIDEO: [
            "video", "animation", "animation", "clip", "sequence",
            "particle", "fire", "spark", "wave", "fractal zoom",
            "starfield", "clock", "timer", "text animation",
        ],
        OutputType.SIMULATION: [
            "vr", "simulation", "scene", "virtual", "environment",
            "space station", "lunar base", "launch pad", "cockpit",
            "planetary surface", "landscape", "habitat", "base",
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
        
        # Engine selection per output type
        self._engines: Dict[str, str] = {
            "image": "procedural",
            "mesh": "trimesh",
            "audio": "synth",
            "video": "procedural",
        }
        
        # Generation queue
        self._queue: List[Dict[str, Any]] = []
        self._queue_lock = None
        self._progress_callback = None
        
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
            elif output_type == OutputType.AUDIO:
                result = self._materialize_audio(prompt, **kwargs)
            elif output_type == OutputType.VIDEO:
                result = self._materialize_video(prompt, **kwargs)
            elif output_type == OutputType.SIMULATION:
                result = self._materialize_simulation(prompt, **kwargs)
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
    # AUDIO GENERATION
    # =========================================================================
    
    def _materialize_audio(self, prompt: str, **kwargs) -> MaterializerResult:
        """
        Generate audio WAV file from prompt.
        
        Categories:
          - ambient: space, wind, rain, thunder
          - effects: laser, explosion, whoosh, beep
          - music: melody, drone, chord
          - voice: speak, sing
        
        Parameters: duration, sample_rate, channels, waveform
        """
        import numpy as np
        import wave
        import struct
        
        prompt_lower = prompt.lower()
        duration = kwargs.get("duration", 3.0)
        sample_rate = kwargs.get("sample_rate", 44100)
        channels = kwargs.get("channels", 1)
        waveform = kwargs.get("waveform", "sine")
        
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        
        # --- Category detection ---
        is_ambient = any(kw in prompt_lower for kw in ["ambient", "space", "wind", "rain", "thunder", "drone", "atmosphere"])
        is_effect = any(kw in prompt_lower for kw in ["laser", "explosion", "whoosh", "beep", "effect", "sfx", "zap", "hit"])
        is_music = any(kw in prompt_lower for kw in ["melody", "music", "chord", "arpeggio", "song", "tune", "beat"])
        is_voice = any(kw in prompt_lower for kw in ["voice", "speak", "sing", "vocal", "talk"])
        
        signal = np.zeros_like(t)
        
        if is_ambient:
            signal = self._gen_ambient(t, prompt_lower, sample_rate)
        elif is_effect:
            signal = self._gen_effect(t, prompt_lower, sample_rate)
        elif is_music:
            signal = self._gen_music(t, prompt_lower, sample_rate)
        elif is_voice:
            signal = self._gen_voice(t, prompt_lower, sample_rate)
        else:
            # Default: generate a pleasant sine sweep
            freq_start = kwargs.get("freq_start", 220)
            freq_end = kwargs.get("freq_end", 880)
            freqs = np.linspace(freq_start, freq_end, len(t))
            signal = 0.5 * np.sin(2 * np.pi * freqs * t)
            # Apply envelope
            envelope = np.ones_like(t)
            fade = int(0.05 * sample_rate)
            envelope[:fade] = np.linspace(0, 1, fade)
            envelope[-fade:] = np.linspace(1, 0, fade)
            signal *= envelope
        
        # Normalize
        peak = np.max(np.abs(signal))
        if peak > 0:
            signal = signal / peak * 0.9
        
        # Write WAV
        timestamp = int(time.time())
        safe_prompt = "".join(c for c in prompt[:20] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt.replace(' ', '_')
        filename = f"audio_{safe_prompt}_{timestamp}.wav"
        filepath = self.output_dir / "audio" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        signal_16 = np.int16(signal * 32767)
        
        with wave.open(str(filepath), 'w') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            if channels == 1:
                wav_file.writeframes(signal_16.tobytes())
            else:
                stereo = np.column_stack([signal_16] * channels)
                wav_file.writeframes(stereo.tobytes())
        
        # Determine category label
        if is_ambient:
            category = "ambient"
        elif is_effect:
            category = "effect"
        elif is_music:
            category = "music"
        elif is_voice:
            category = "voice"
        else:
            category = "sweep"
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.AUDIO,
            file_path=str(filepath),
            method="wav_synth",
            metadata={
                "category": category,
                "duration": duration,
                "sample_rate": sample_rate,
                "channels": channels,
                "waveform": waveform,
            }
        )
    
    def _gen_ambient(self, t, prompt_lower, sample_rate):
        """Generate ambient sound (space drone / wind / rain / thunder)."""
        import numpy as np
        
        duration = len(t) / sample_rate
        
        if "space" in prompt_lower or "cosmos" in prompt_lower:
            # Deep space drone
            sig = 0.3 * np.sin(2 * np.pi * 60 * t)
            sig += 0.15 * np.sin(2 * np.pi * 90 * t + np.sin(2 * np.pi * 0.1 * t))
            sig += 0.1 * np.sin(2 * np.pi * 120 * t)
            # Slow modulation
            mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t)
            sig *= mod
        elif "wind" in prompt_lower:
            # Filtered noise sweep
            sig = np.random.randn(len(t)) * 0.3
            # Slow volume modulation
            mod = 0.3 + 0.7 * np.abs(np.sin(2 * np.pi * 0.2 * t))
            sig *= mod
            # Low pass approximation: moving average
            kernel_size = int(0.005 * sample_rate)
            kernel = np.ones(kernel_size) / kernel_size
            sig = np.convolve(sig, kernel, mode='same')
        elif "rain" in prompt_lower:
            # White noise with rain drops
            sig = np.random.randn(len(t)) * 0.15
            # Random click impulses
            num_drops = int(duration * 200)
            drop_times = np.random.uniform(0, t[-1], num_drops)
            drop_amps = np.random.uniform(0.05, 0.3, num_drops)
            for dt, amp in zip(drop_times, drop_amps):
                idx = int(dt * sample_rate)
                if 0 <= idx < len(sig):
                    sig[idx:idx+20] += amp * np.exp(-np.linspace(0, 4, 20))
        elif "thunder" in prompt_lower:
            # Rumble + crash
            sig = np.random.randn(len(t)) * 0.05
            sig += 0.4 * np.sin(2 * np.pi * 40 * t)
            # Thunder crack at 20% of duration
            crack_pos = int(len(t) * 0.2)
            crack_len = int(0.01 * sample_rate)
            if crack_pos + crack_len < len(t):
                sig[crack_pos:crack_pos+crack_len] += 0.8 * np.random.randn(crack_len)
        else:
            # Generic ambient drone
            sig = 0.3 * np.sin(2 * np.pi * 80 * t)
            sig += 0.2 * np.sin(2 * np.pi * 120 * t + np.sin(2 * np.pi * 0.15 * t) * 2)
            sig += 0.1 * np.sin(2 * np.pi * 160 * t)
            mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t)
            sig *= mod
        
        # Fade in/out
        fade = int(0.1 * sample_rate)
        sig[:fade] *= np.linspace(0, 1, fade)
        sig[-fade:] *= np.linspace(1, 0, fade)
        return sig
    
    def _gen_effect(self, t, prompt_lower, sample_rate):
        """Generate sound effect (laser / explosion / whoosh / beep)."""
        import numpy as np
        
        duration = len(t) / sample_rate
        
        if "laser" in prompt_lower or "zap" in prompt_lower:
            # Descending sine sweep
            freq_start = 2000
            freq_end = 200
            freqs = np.geomspace(freq_start, freq_end, len(t))
            sig = 0.6 * np.sin(2 * np.pi * freqs * t)
            # Rapid decay
            decay = np.exp(-np.linspace(0, 8, len(t)))
            sig *= decay
        elif "explosion" in prompt_lower or "boom" in prompt_lower or "hit" in prompt_lower:
            # Noise burst + low rumble
            sig = np.random.randn(len(t)) * 0.7
            sig += 0.5 * np.sin(2 * np.pi * 50 * t)
            # Sharp attack, long decay
            decay = np.exp(-np.linspace(0, 4, len(t)))
            sig *= decay
        elif "whoosh" in prompt_lower:
            # Filtered noise with frequency sweep
            sig = np.random.randn(len(t)) * 0.4
            # Frequency sweep via AM
            sweep_freq = np.linspace(200, 4000, len(t))
            carrier = np.sin(2 * np.pi * sweep_freq * t)
            sig *= carrier
            # Envelope
            envelope = np.sin(np.pi * np.linspace(0, 1, len(t))) ** 0.5
            sig *= envelope
        elif "beep" in prompt_lower or "blip" in prompt_lower:
            # Series of short beeps
            beep_freq = 880
            beep_duration = 0.08
            gap = 0.12
            sig = np.zeros_like(t)
            pos = 0
            while pos < len(t):
                end = min(pos + int(beep_duration * sample_rate), len(t))
                sig[pos:end] = 0.7 * np.sin(2 * np.pi * beep_freq * t[pos:end])
                pos += int(gap * sample_rate)
        else:
            # Generic zap
            freqs = np.geomspace(1500, 100, len(t))
            sig = 0.5 * np.sin(2 * np.pi * freqs * t)
            decay = np.exp(-np.linspace(0, 6, len(t)))
            sig *= decay
        
        return sig
    
    def _gen_music(self, t, prompt_lower, sample_rate):
        """Generate musical audio (melody / drone / chord / arpeggio)."""
        import numpy as np
        
        # Note frequencies (A3=220, A4=440)
        NOTE_FREQS = {
            'c3': 130.81, 'd3': 146.83, 'e3': 164.81, 'f3': 174.61,
            'g3': 196.00, 'a3': 220.00, 'b3': 246.94,
            'c4': 261.63, 'd4': 293.66, 'e4': 329.63, 'f4': 349.23,
            'g4': 392.00, 'a4': 440.00, 'b4': 493.88,
            'c5': 523.25, 'd5': 587.33, 'e5': 659.25,
        }
        
        if "chord" in prompt_lower:
            # Pad chord
            chords = [
                [261.63, 329.63, 392.00],  # C major
                [220.00, 277.18, 329.63],   # A minor
                [196.00, 246.94, 293.66],   # G major
            ]
            sig = np.zeros_like(t)
            for chord in chords:
                for freq in chord:
                    sig += 0.2 * np.sin(2 * np.pi * freq * t)
            # Slow attack/decay
            envelope = np.sin(np.pi * np.linspace(0, 1, len(t)))
            sig *= envelope
        elif "arpeggio" in prompt_lower or "arp" in prompt_lower:
            # Arpeggiated chord
            notes = ['c4', 'e4', 'g4', 'c5', 'g4', 'e4']
            note_len = len(t) // len(notes)
            sig = np.zeros_like(t)
            for i, note in enumerate(notes):
                start = i * note_len
                end = min(start + note_len, len(t))
                freq = NOTE_FREQS[note]
                sig[start:end] = 0.4 * np.sin(2 * np.pi * freq * t[start:end])
        elif "drone" in prompt_lower:
            # Ambient musical drone
            sig = 0.3 * np.sin(2 * np.pi * 110 * t)
            sig += 0.2 * np.sin(2 * np.pi * 165 * t)
            sig += 0.15 * np.sin(2 * np.pi * 220 * t)
            mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t)
            sig *= mod
        elif "melody" in prompt_lower or "music" in prompt_lower or "song" in prompt_lower:
            # Simple melody
            melody_notes = ['c4', 'e4', 'g4', 'a4', 'g4', 'e4', 'c4', 'd4']
            note_len = len(t) // len(melody_notes)
            sig = np.zeros_like(t)
            for i, note in enumerate(melody_notes):
                start = i * note_len
                end = min(start + note_len, len(t))
                freq = NOTE_FREQS[note]
                # Apply ADSR-like envelope per note
                note_t = np.linspace(0, 1, end - start)
                env = np.exp(-2 * note_t) * (1 - np.exp(-20 * note_t))
                sig[start:end] = 0.5 * np.sin(2 * np.pi * freq * t[start:end]) * env
        else:
            # Default chord pad
            sig = 0.3 * np.sin(2 * np.pi * 261.63 * t)
            sig += 0.2 * np.sin(2 * np.pi * 329.63 * t)
            sig += 0.15 * np.sin(2 * np.pi * 392.00 * t)
            envelope = np.sin(np.pi * np.linspace(0, 1, len(t)))
            sig *= envelope
        
        return sig
    
    def _gen_voice(self, t, prompt_lower, sample_rate):
        """Generate voice-like synthesis (speak / sing)."""
        import numpy as np
        
        # Formant frequencies for vowels
        FORMANTS = {
            'a': [(730, 1090, 2440)],
            'e': [(530, 1840, 2480)],
            'i': [(270, 2290, 3010)],
            'o': [(570, 840, 2410)],
            'u': [(300, 870, 2240)],
        }
        
        duration = len(t) / sample_rate
        base_freq = 150
        
        if "sing" in prompt_lower:
            # Singing: sustained vowels with vibrato
            vowels = list("aeiouaeiou")
            vowel_len = len(t) // len(vowels)
            sig = np.zeros_like(t)
            for i, v in enumerate(vowels):
                start = i * vowel_len
                end = min(start + vowel_len, len(t))
                f0 = base_freq * (1 + 0.02 * np.sin(2 * np.pi * 5 * t[start:end]))  # vibrato
                formant = FORMANTS[v][0]
                sig[start:end] = 0.3 * np.sin(2 * np.pi * f0 * t[start:end])
                sig[start:end] += 0.2 * np.sin(2 * np.pi * formant * t[start:end])
        else:
            # Speaking: harmonic series with fundamental
            sig = 0.4 * np.sin(2 * np.pi * base_freq * t)
            sig += 0.2 * np.sin(2 * np.pi * base_freq * 2 * t)
            sig += 0.1 * np.sin(2 * np.pi * base_freq * 3 * t)
            # Add some noise for breathiness
            sig += 0.05 * np.random.randn(len(t))
            # Amplitude modulation for cadence
            mod = 0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)
            sig *= mod
        
        # Fade
        fade = int(0.05 * sample_rate)
        sig[:fade] *= np.linspace(0, 1, fade)
        sig[-fade:] *= np.linspace(1, 0, fade)
        
        return sig
    
    # =========================================================================
    # VIDEO GENERATION
    # =========================================================================
    
    def _materialize_video(self, prompt: str, **kwargs) -> MaterializerResult:
        """
        Generate procedural video as frame sequence + optional MP4 encode.
        
        Types: particle_simulation, wave_simulation, fractal_zoom,
               starfield_flythrough, clock, text_animation
        """
        import numpy as np
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return MaterializerResult(
                success=False,
                output_type=OutputType.VIDEO,
                error="PIL/Pillow not available"
            )
        
        prompt_lower = prompt.lower()
        width = kwargs.get("width", 640)
        height = kwargs.get("height", 480)
        duration_sec = kwargs.get("duration", 3.0)
        fps = kwargs.get("fps", 24)
        total_frames = int(duration_sec * fps)
        
        # Detect video type
        is_particle = any(kw in prompt_lower for kw in ["particle", "fire", "spark", "explosion", "ember"])
        is_wave = any(kw in prompt_lower for kw in ["wave", "ocean", "ripple", "water", "fluid"])
        is_fractal = any(kw in prompt_lower for kw in ["fractal", "mandelbrot", "zoom", "julia"])
        is_starfield = any(kw in prompt_lower for kw in ["star", "space", "flythrough", "nebula", "cosmos"])
        is_clock = any(kw in prompt_lower for kw in ["clock", "timer", "countdown", "count"])
        is_text = any(kw in prompt_lower for kw in ["text", "title", "subtitle", "caption"])
        
        timestamp = int(time.time())
        safe_prompt = "".join(c for c in prompt[:20] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt.replace(' ', '_')
        frames_dir = self.output_dir / "video" / f"frames_{safe_prompt}_{timestamp}"
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        bg_color = (4, 6, 12)
        primary_color = (0, 229, 255)
        accent_color = (124, 77, 255)
        
        for frame_idx in range(total_frames):
            progress = frame_idx / max(total_frames - 1, 1)
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            if is_particle:
                self._draw_particle_frame(draw, width, height, frame_idx, total_frames, progress)
            elif is_wave:
                self._draw_wave_frame(draw, width, height, frame_idx, total_frames, progress)
            elif is_fractal:
                self._draw_fractal_frame(img, width, height, frame_idx, total_frames, progress)
            elif is_starfield:
                self._draw_starfield_frame(draw, width, height, frame_idx, total_frames, progress)
            elif is_clock:
                self._draw_clock_frame(draw, width, height, frame_idx, total_frames, progress, duration_sec)
            elif is_text:
                self._draw_text_frame(draw, width, height, frame_idx, total_frames, progress, prompt)
            else:
                # Default: particle
                self._draw_particle_frame(draw, width, height, frame_idx, total_frames, progress)
            
            frame_path = frames_dir / f"frame_{frame_idx:05d}.png"
            img.save(str(frame_path))
        
        # Try to encode to MP4 with ffmpeg
        output_path = str(frames_dir)
        ffmpeg_available = False
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, timeout=5
            )
            ffmpeg_available = result.returncode == 0
        except Exception:
            pass
        
        mp4_path = None
        if ffmpeg_available:
            import subprocess
            mp4_path = str(frames_dir.parent / f"video_{safe_prompt}_{timestamp}.mp4")
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-framerate", str(fps),
                    "-i", str(frames_dir / "frame_%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    mp4_path
                ], capture_output=True, timeout=120)
            except Exception:
                mp4_path = None
        
        # Detect type label
        if is_particle:
            vtype = "particle_simulation"
        elif is_wave:
            vtype = "wave_simulation"
        elif is_fractal:
            vtype = "fractal_zoom"
        elif is_starfield:
            vtype = "starfield_flythrough"
        elif is_clock:
            vtype = "clock"
        elif is_text:
            vtype = "text_animation"
        else:
            vtype = "particle_simulation"
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.VIDEO,
            file_path=mp4_path or str(frames_dir),
            method="procedural_video",
            metadata={
                "type": vtype,
                "width": width,
                "height": height,
                "duration_sec": duration_sec,
                "fps": fps,
                "total_frames": total_frames,
                "frames_dir": str(frames_dir),
                "mp4_path": mp4_path,
                "ffmpeg_available": ffmpeg_available,
            }
        )
    
    def _draw_particle_frame(self, draw, w, h, frame_idx, total_frames, progress):
        """Draw a particle simulation frame (fire/sparks)."""
        import random
        rng = random.Random(frame_idx * 42 + self.seed)
        
        # Ground glow
        for y in range(h // 2, h):
            alpha = int(255 * (1 - (y - h // 2) / (h // 2)) * 0.3)
            r = min(255, alpha + rng.randint(0, 20))
            g = min(255, int(alpha * 0.4))
            draw.line([(0, y), (w, y)], fill=(r, g, 0))
        
        # Particles
        num_particles = 80
        for _ in range(num_particles):
            x = rng.randint(0, w)
            y = rng.randint(h // 4, h)
            size = rng.randint(1, 4)
            life = (y - h // 4) / (h * 0.75)
            r = min(255, int(255 * (1 - life)))
            g = min(255, int(200 * (1 - life) * rng.uniform(0.3, 1.0)))
            b = int(100 * life)
            draw.ellipse([x-size, y-size, x+size, y+size], fill=(r, g, b))
    
    def _draw_wave_frame(self, draw, w, h, frame_idx, total_frames, progress):
        """Draw a wave/ocean simulation frame."""
        import math
        
        colors = [(0, 100, 200), (0, 150, 220), (0, 180, 240)]
        t = frame_idx * 0.1
        
        for layer, color in enumerate(colors):
            points = []
            amplitude = 20 - layer * 5
            frequency = 0.02 + layer * 0.01
            y_base = h // 2 + layer * 40 + int(30 * math.sin(t * 0.5))
            
            for x in range(0, w + 10, 10):
                y = y_base + int(amplitude * math.sin(x * frequency + t + layer))
                points.append((x, y))
            
            # Fill below wave
            fill_points = points + [(w, h), (0, h)]
            draw.polygon(fill_points, fill=(color[0], color[1], color[2], 180))
            draw.line(points, fill=color, width=2)
    
    def _draw_fractal_frame(self, img, w, h, frame_idx, total_frames, progress):
        """Draw a fractal zoom frame (Mandelbrot)."""
        import numpy as np
        
        zoom = 1.0 + progress * 100
        cx = -0.745
        cy = 0.186
        
        # Low-res for speed
        scale = 4
        rw, rh = w // scale, h // scale
        
        x = np.linspace(-2.0 / zoom + cx, 2.0 / zoom + cx, rw)
        y = np.linspace(-1.5 / zoom + cy, 1.5 / zoom + cy, rh)
        X, Y = np.meshgrid(x, y)
        C = X + 1j * Y
        Z = np.zeros_like(C, dtype=complex)
        
        max_iter = 30
        diverged = np.zeros(C.shape, dtype=int)
        
        for i in range(max_iter):
            mask = np.abs(Z) <= 2
            Z[mask] = Z[mask] ** 2 + C[mask]
            diverged[mask & (np.abs(Z) > 2)] = i
        
        # Color map
        colors = np.zeros((rh, rw, 3), dtype=np.uint8)
        norm = diverged / max_iter
        colors[:, :, 0] = (np.sin(norm * 3.0) * 127 + 128).astype(np.uint8)
        colors[:, :, 1] = (np.sin(norm * 3.0 + 2.0) * 127 + 128).astype(np.uint8)
        colors[:, :, 2] = (np.sin(norm * 3.0 + 4.0) * 127 + 128).astype(np.uint8)
        
        from PIL import Image
        frame = Image.fromarray(colors, 'RGB')
        frame = frame.resize((w, h), Image.NEAREST)
        img.paste(frame, (0, 0))
    
    def _draw_starfield_frame(self, draw, w, h, frame_idx, total_frames, progress):
        """Draw a starfield flythrough frame."""
        import random
        
        rng = random.Random(self.seed)
        num_stars = 200
        
        for _ in range(num_stars):
            sx = rng.random()
            sy = rng.random()
            sz = rng.random()
            
            # Apply movement
            sz -= progress * 0.5
            sz = sz % 1.0
            
            if sz < 0.01:
                continue
            
            px = int((sx - 0.5) * w / sz + w // 2)
            py = int((sy - 0.5) * h / sz + h // 2)
            
            if 0 <= px < w and 0 <= py < h:
                size = max(1, int((1 - sz) * 4))
                brightness = int(255 * (1 - sz))
                draw.ellipse(
                    [px - size, py - size, px + size, py + size],
                    fill=(brightness, brightness, min(255, brightness + 50))
                )
        
        # Nebula glow
        for _ in range(5):
            nx = rng.randint(0, w)
            ny = rng.randint(0, h)
            nr = rng.randint(30, 80)
            draw.ellipse(
                [nx - nr, ny - nr, nx + nr, ny + nr],
                fill=(20, 10, 40, 30)
            )
    
    def _draw_clock_frame(self, draw, w, h, frame_idx, total_frames, progress, duration):
        """Draw a clock/timer frame."""
        import math
        
        cx, cy = w // 2, h // 2
        radius = min(w, h) // 3
        
        # Outer ring
        draw.ellipse(
            [cx - radius - 5, cy - radius - 5, cx + radius + 5, cy + radius + 5],
            outline=(0, 229, 255), width=2
        )
        
        # Tick marks
        for i in range(60):
            angle = (i / 60) * 2 * math.pi - math.pi / 2
            x1 = cx + int((radius - 10) * math.cos(angle))
            y1 = cy + int((radius - 10) * math.sin(angle))
            x2 = cx + int(radius * math.cos(angle))
            y2 = cy + int(radius * math.sin(angle))
            color = (0, 229, 255) if i % 5 == 0 else (80, 120, 160)
            draw.line([(x1, y1), (x2, y2)], fill=color, width=2)
        
        # Timer arc
        elapsed_angle = progress * 2 * math.pi
        for a in range(int(elapsed_angle * 180 / math.pi)):
            angle = a * math.pi / 180 - math.pi / 2
            x = cx + int((radius - 20) * math.cos(angle))
            y = cy + int((radius - 20) * math.sin(angle))
            draw.ellipse([x-1, y-1, x+1, y+1], fill=(0, 255, 136))
        
        # Digital time
        remaining = duration * (1 - progress)
        minutes = int(remaining) // 60
        seconds = int(remaining) % 60
        ms = int((remaining % 1) * 100)
        time_str = f"{minutes:02d}:{seconds:02d}.{ms:02d}"
        try:
            draw.text((cx - 40, cy + radius + 20), time_str, fill=(0, 229, 255))
        except Exception:
            draw.text((cx - 30, cy + radius + 20), time_str[:5], fill=(0, 229, 255))
    
    def _draw_text_frame(self, draw, w, h, frame_idx, total_frames, progress, prompt):
        """Draw a text animation frame."""
        # Extract text from prompt (after last colon or the whole prompt)
        text = prompt.split(":")[-1].strip() if ":" in prompt else "ZICORE"
        text = text[:30]
        
        # Typewriter effect
        num_chars = max(1, int(len(text) * progress))
        display_text = text[:num_chars]
        
        cx, cy = w // 2, h // 2
        
        # Glow effect
        for offset in range(3, 0, -1):
            alpha = 80 - offset * 20
            try:
                draw.text((cx - len(display_text) * 4 + offset, cy), display_text, fill=(0, alpha, alpha))
            except Exception:
                pass
        
        try:
            draw.text((cx - len(display_text) * 4, cy), display_text, fill=(0, 229, 255))
        except Exception:
            draw.text((cx - len(display_text) * 3, cy), display_text, fill=(0, 229, 255))
        
        # Underline cursor
        if int(progress * 10) % 2 == 0:
            cursor_x = cx - len(display_text) * 4 + len(display_text) * 8
            draw.line([(cursor_x, cy + 12), (cursor_x + 8, cy + 12)], fill=(0, 229, 255), width=2)
    
    # =========================================================================
    # VR SIMULATION GENERATION
    # =========================================================================
    
    def _materialize_simulation(self, prompt: str, **kwargs) -> MaterializerResult:
        """
        Generate a VR-ready scene with objects, lighting, and camera config.
        
        Scene types: planetary_surface, space_station, lunar_base,
                     launch_pad, cockpit, landscape
        """
        prompt_lower = prompt.lower()
        width = kwargs.get("width", 1280)
        height = kwargs.get("height", 720)
        
        # Detect scene type
        scene_type = "planetary_surface"
        if "station" in prompt_lower or "space station" in prompt_lower:
            scene_type = "space_station"
        elif "lunar" in prompt_lower or "moon" in prompt_lower:
            scene_type = "lunar_base"
        elif "launch" in prompt_lower or "pad" in prompt_lower or "rocket" in prompt_lower:
            scene_type = "launch_pad"
        elif "cockpit" in prompt_lower or "pilot" in prompt_lower or "dashboard" in prompt_lower:
            scene_type = "cockpit"
        elif "landscape" in prompt_lower or "mountain" in prompt_lower or "terrain" in prompt_lower:
            scene_type = "landscape"
        
        # Build scene
        scene = {
            "name": f"VR Scene: {prompt[:60]}",
            "scene_type": scene_type,
            "created": int(time.time()),
            "zicore_version": "5.0.0",
            "renderer": {
                "width": width,
                "height": height,
                "fov": 75,
                "near_clip": 0.1,
                "far_clip": 10000,
                "antialiasing": True,
                "hdr": True,
            },
            "camera": self._get_scene_camera(scene_type),
            "lighting": self._get_scene_lighting(scene_type),
            "skybox": self._get_scene_skybox(scene_type),
            "physics": self._get_scene_physics(scene_type),
            "objects": self._get_scene_objects(scene_type, prompt_lower),
            "audio_sources": self._get_scene_audio(scene_type),
            "metadata": {
                "prompt": prompt,
                "auto_generated": True,
            },
        }
        
        # Save scene JSON
        timestamp = int(time.time())
        safe_prompt = "".join(c for c in prompt[:20] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt.replace(' ', '_')
        filename = f"scene_{safe_prompt}_{timestamp}.json"
        filepath = self.output_dir / "scenes" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        filepath.write_text(json.dumps(scene, indent=2))
        
        # Also generate a preview image
        preview_path = self._render_scene_preview(scene, str(filepath).replace('.json', '_preview.png'))
        
        return MaterializerResult(
            success=True,
            output_type=OutputType.SIMULATION,
            file_path=str(filepath),
            method="vr_scene_generator",
            metadata={
                "scene_type": scene_type,
                "num_objects": len(scene["objects"]),
                "preview": preview_path,
                "has_lighting": True,
                "has_physics": True,
                "has_audio": True,
            }
        )
    
    def _get_scene_camera(self, scene_type):
        """Get camera config for scene type."""
        cameras = {
            "planetary_surface": {
                "position": [0, 2, 0],
                "rotation": [-15, 0, 0],
                "type": "first_person",
                "move_speed": 5.0,
                "look_speed": 2.0,
            },
            "space_station": {
                "position": [0, 1.7, 0],
                "rotation": [0, 0, 0],
                "type": "first_person",
                "move_speed": 2.0,
                "look_speed": 1.5,
            },
            "lunar_base": {
                "position": [0, 1.7, -5],
                "rotation": [0, 0, 0],
                "type": "first_person",
                "move_speed": 3.0,
                "look_speed": 2.0,
            },
            "launch_pad": {
                "position": [50, 5, 50],
                "rotation": [-20, 135, 0],
                "type": "orbit",
                "orbit_distance": 70,
                "orbit_speed": 0.1,
            },
            "cockpit": {
                "position": [0, 0, 0],
                "rotation": [0, 0, 0],
                "type": "fixed",
                "look_limits": {"min_pitch": -30, "max_pitch": 30},
            },
            "landscape": {
                "position": [0, 5, -10],
                "rotation": [-10, 0, 0],
                "type": "flycam",
                "move_speed": 10.0,
                "look_speed": 1.0,
            },
        }
        return cameras.get(scene_type, cameras["planetary_surface"])
    
    def _get_scene_lighting(self, scene_type):
        """Get lighting config for scene type."""
        lighting = {
            "planetary_surface": {
                "ambient": {"color": [30, 40, 60], "intensity": 0.3},
                "directional": {
                    "color": [255, 220, 180],
                    "intensity": 1.0,
                    "direction": [-0.5, -1, 0.3],
                    "shadows": True,
                    "shadow_map_size": 2048,
                },
                "fog": {"enabled": True, "color": [20, 25, 40], "density": 0.002},
            },
            "space_station": {
                "ambient": {"color": [40, 50, 80], "intensity": 0.4},
                "point_lights": [
                    {"position": [0, 3, 0], "color": [200, 220, 255], "intensity": 0.8, "range": 15},
                    {"position": [5, 3, 5], "color": [255, 200, 100], "intensity": 0.5, "range": 10},
                ],
            },
            "lunar_base": {
                "ambient": {"color": [20, 20, 30], "intensity": 0.15},
                "directional": {
                    "color": [255, 255, 240],
                    "intensity": 1.2,
                    "direction": [0.3, -0.8, 0.5],
                    "shadows": True,
                },
                "point_lights": [
                    {"position": [0, 3, 0], "color": [255, 180, 100], "intensity": 0.6, "range": 20},
                ],
            },
            "launch_pad": {
                "ambient": {"color": [30, 30, 50], "intensity": 0.2},
                "directional": {
                    "color": [255, 200, 150],
                    "intensity": 0.8,
                    "direction": [-0.3, -0.7, 0.2],
                    "shadows": True,
                },
                "floodlights": [
                    {"position": [20, 15, 0], "color": [255, 255, 200], "intensity": 1.5, "angle": 45},
                    {"position": [-20, 15, 0], "color": [255, 255, 200], "intensity": 1.5, "angle": 45},
                ],
            },
            "cockpit": {
                "ambient": {"color": [10, 15, 25], "intensity": 0.2},
                "point_lights": [
                    {"position": [0, 1, -1], "color": [0, 229, 255], "intensity": 0.3, "range": 3},
                ],
                "instrument_glow": True,
            },
            "landscape": {
                "ambient": {"color": [40, 50, 70], "intensity": 0.35},
                "directional": {
                    "color": [255, 240, 200],
                    "intensity": 1.0,
                    "direction": [0.5, -0.8, 0.3],
                    "shadows": True,
                },
                "hemisphere": {
                    "sky_color": [100, 150, 255],
                    "ground_color": [60, 40, 30],
                    "intensity": 0.4,
                },
            },
        }
        return lighting.get(scene_type, lighting["planetary_surface"])
    
    def _get_scene_skybox(self, scene_type):
        """Get skybox config for scene type."""
        skyboxes = {
            "planetary_surface": {
                "type": "procedural_sky",
                "sun_position": [0.5, 0.3, 0.8],
                "sun_intensity": 1.0,
                "atmosphere_color": [100, 150, 255],
                "stars_visible": False,
            },
            "space_station": {
                "type": "starfield",
                "stars": 5000,
                "nebula_enabled": True,
                "earth_visible": True,
                "earth_position": [100, -50, -200],
            },
            "lunar_base": {
                "type": "lunar_sky",
                "stars": 8000,
                "earth_visible": True,
                "earth_position": [50, 30, -100],
                "earth_phase": 0.7,
            },
            "launch_pad": {
                "type": "procedural_sky",
                "sun_position": [0.3, 0.6, 0.5],
                "time_of_day": "dawn",
                "clouds_enabled": True,
            },
            "cockpit": {
                "type": "viewport",
                "view_through_windows": True,
            },
            "landscape": {
                "type": "procedural_sky",
                "sun_position": [0.4, 0.4, 0.6],
                "clouds_enabled": True,
                "stars_visible": False,
            },
        }
        return skyboxes.get(scene_type, skyboxes["planetary_surface"])
    
    def _get_scene_physics(self, scene_type):
        """Get physics config for scene type."""
        physics = {
            "gravity": [0, -9.81, 0] if scene_type != "space_station" else [0, 0, 0],
            "atmosphere": scene_type in ("planetary_surface", "launch_pad", "landscape"),
            "air_density": 1.225 if scene_type != "lunar_base" else 0.0,
            "wind": {"enabled": scene_type != "space_station", "speed": 2.0, "direction": [1, 0, 0.5]},
            "collision_detection": True,
            "rigid_body_dynamics": True,
            "max_bodies": 1000,
            "collision_margin": 0.01,
        }
        if scene_type == "lunar_base":
            physics["gravity"] = [0, -1.62, 0]
        elif scene_type == "space_station":
            physics["microgravity"] = True
            physics["centrifugal_artificial_gravity"] = None
        return physics
    
    def _get_scene_objects(self, scene_type, prompt_lower):
        """Get default scene objects for scene type."""
        objects = []
        
        if scene_type == "planetary_surface":
            objects.extend([
                {"type": "terrain", "name": "ground", "position": [0, 0, 0],
                 "size": [200, 200], "material": "rocky_soil", "collision": True},
                {"type": "prop", "name": "rocks_cluster_1", "position": [5, 0, 8],
                 "mesh": "procedural_rock", "scale": [1.5, 1.0, 1.2], "collision": True},
                {"type": "prop", "name": "rocks_cluster_2", "position": [-12, 0, -5],
                 "mesh": "procedural_rock", "scale": [0.8, 0.6, 1.0], "collision": True},
                {"type": "vegetation", "name": "alien_tree_1", "position": [10, 0, 15],
                 "mesh": "procedural_alien_tree", "scale": [1.0], "collision": True},
                {"type": "vehicle", "name": "rover", "position": [0, 0.5, 0],
                 "mesh": "rover_mark1", "drivable": True, "collision": True},
            ])
            if "base" in prompt_lower or "habitat" in prompt_lower:
                objects.append(
                    {"type": "structure", "name": "habitat_dome", "position": [20, 0, 0],
                     "mesh": "habitat_dome", "scale": [1.0], "collision": True}
                )
        elif scene_type == "space_station":
            objects.extend([
                {"type": "structure", "name": "central_module", "position": [0, 0, 0],
                 "mesh": "station_module_cylindrical", "scale": [1.0], "collision": True},
                {"type": "structure", "name": "solar_array_left", "position": [-8, 0, 0],
                 "mesh": "solar_array", "rotation": [0, 0, 0], "collision": True},
                {"type": "structure", "name": "solar_array_right", "position": [8, 0, 0],
                 "mesh": "solar_array", "rotation": [0, 180, 0], "collision": True},
                {"type": "structure", "name": "docking_port", "position": [0, 0, -5],
                 "mesh": "docking_adapter", "collision": True},
                {"type": "prop", "name": "debris_1", "position": [30, 5, -20],
                 "mesh": "space_debris", "collision": False, "animated": True},
            ])
        elif scene_type == "lunar_base":
            objects.extend([
                {"type": "terrain", "name": "lunar_surface", "position": [0, 0, 0],
                 "size": [300, 300], "material": "lunar_regolith", "collision": True},
                {"type": "structure", "name": "habitat", "position": [0, 0, 0],
                 "mesh": "lunar_habitat", "scale": [1.0], "collision": True},
                {"type": "structure", "name": "airlock", "position": [5, 0, 0],
                 "mesh": "airlock_module", "collision": True},
                {"type": "vehicle", "name": "lunar_rover", "position": [-5, 0, 3],
                 "mesh": "lunar_rover", "drivable": True, "collision": True},
                {"type": "prop", "name": "solar_panel_array", "position": [10, 3, -5],
                 "mesh": "solar_panel_ground", "collision": True},
                {"type": "prop", "name": "flag", "position": [8, 0, 2],
                 "mesh": "flag_pole", "collision": True},
            ])
            if "mining" in prompt_lower or "isru" in prompt_lower:
                objects.append(
                    {"type": "structure", "name": "mining_rig", "position": [-15, 0, -10],
                     "mesh": "mining_rig", "collision": True}
                )
        elif scene_type == "launch_pad":
            objects.extend([
                {"type": "terrain", "name": "ground", "position": [0, 0, 0],
                 "size": [500, 500], "material": "concrete", "collision": True},
                {"type": "structure", "name": "launch_tower", "position": [5, 0, 0],
                 "mesh": "launch_tower", "collision": True},
                {"type": "vehicle", "name": "rocket", "position": [0, 5, 0],
                 "mesh": "launch_vehicle", "collision": True},
                {"type": "structure", "name": "flame_deflector", "position": [0, -1, 10],
                 "mesh": "flame_deflector", "collision": True},
                {"type": "prop", "name": "fuel_tank_1", "position": [-15, 0, 15],
                 "mesh": "fuel_tank", "collision": True},
                {"type": "prop", "name": "fuel_tank_2", "position": [-20, 0, 15],
                 "mesh": "fuel_tank", "collision": True},
                {"type": "effect", "name": "steam_vents", "position": [3, 0, 5],
                 "particle_system": "steam", "active": True},
            ])
        elif scene_type == "cockpit":
            objects.extend([
                {"type": "structure", "name": "cockpit_frame", "position": [0, 0, 0],
                 "mesh": "cockpit_interior", "collision": True},
                {"type": "ui", "name": "hud_main", "position": [0, 1.2, -1],
                 "mesh": "hud_display", "interactive": True},
                {"type": "ui", "name": "instrument_panel", "position": [0, 0.5, -0.8],
                 "mesh": "instrument_panel", "interactive": True},
                {"type": "prop", "name": "joystick", "position": [0, 0.4, 0.2],
                 "mesh": "flight_stick", "interactive": True},
                {"type": "prop", "name": "throttle", "position": [-0.3, 0.4, 0.2],
                 "mesh": "throttle_quadrant", "interactive": True},
            ])
        elif scene_type == "landscape":
            objects.extend([
                {"type": "terrain", "name": "ground", "position": [0, 0, 0],
                 "size": [500, 500], "material": "grass_rock", "collision": True},
                {"type": "vegetation", "name": "tree_cluster_1", "position": [15, 0, 20],
                 "mesh": "tree_pine", "count": 5, "spread": 5, "collision": True},
                {"type": "vegetation", "name": "tree_cluster_2", "position": [-20, 0, 10],
                 "mesh": "tree_oak", "count": 3, "spread": 4, "collision": True},
                {"type": "prop", "name": "river", "position": [0, -0.2, 30],
                 "mesh": "water_plane", "size": [10, 200], "animated": True},
            ])
        
        # Add prompt-specific objects
        if "drone" in prompt_lower:
            objects.append(
                {"type": "vehicle", "name": "drone", "position": [0, 10, 5],
                 "mesh": "quadcopter", "flyable": True, "collision": True}
            )
        if "robot" in prompt_lower:
            objects.append(
                {"type": "vehicle", "name": "robot", "position": [3, 0, 0],
                 "mesh": "humanoid_robot", "animated": True, "collision": True}
            )
        
        return objects
    
    def _get_scene_audio(self, scene_type):
        """Get audio source config for scene type."""
        audio = {
            "planetary_surface": [
                {"name": "wind_ambient", "type": "ambient", "loop": True,
                 "position": [0, 0, 0], "volume": 0.3, "roll_off": "linear"},
            ],
            "space_station": [
                {"name": "station_hum", "type": "ambient", "loop": True,
                 "position": [0, 0, 0], "volume": 0.2, "roll_off": "linear"},
                {"name": "beep_console", "type": "effect", "loop": True,
                 "position": [0, 1, -1], "volume": 0.15, "interval": 5.0},
            ],
            "lunar_base": [
                {"name": "silence", "type": "ambient", "loop": True,
                 "position": [0, 0, 0], "volume": 0.05},
            ],
            "launch_pad": [
                {"name": "wind", "type": "ambient", "loop": True,
                 "position": [0, 0, 0], "volume": 0.4},
                {"name": "machinery", "type": "effect", "loop": True,
                 "position": [5, 0, 0], "volume": 0.2},
            ],
            "cockpit": [
                {"name": "engine_hum", "type": "ambient", "loop": True,
                 "position": [0, -1, 0], "volume": 0.25},
                {"name": "console_beeps", "type": "effect", "loop": True,
                 "position": [0, 0, -0.8], "volume": 0.1, "interval": 3.0},
            ],
            "landscape": [
                {"name": "birds", "type": "ambient", "loop": True,
                 "position": [0, 10, 0], "volume": 0.2},
                {"name": "wind_trees", "type": "ambient", "loop": True,
                 "position": [0, 5, 0], "volume": 0.15},
            ],
        }
        return audio.get(scene_type, audio["planetary_surface"])
    
    def _render_scene_preview(self, scene, output_path):
        """Render a simple preview image of the scene."""
        try:
            from PIL import Image, ImageDraw
            
            w, h = 640, 360
            img = Image.new('RGB', (w, h), (4, 6, 12))
            draw = ImageDraw.Draw(img)
            
            scene_type = scene["scene_type"]
            
            # Simple ground plane
            ground_y = h * 2 // 3
            draw.rectangle([0, ground_y, w, h], fill=(20, 25, 35))
            
            # Objects as simple shapes
            for obj in scene.get("objects", []):
                x = int((hash(obj["name"]) % 100) / 100 * w)
                y = ground_y - 20 - (hash(obj["name"]) % 40)
                size = 10 + (hash(obj["name"]) % 20)
                
                color = (0, 180, 200)
                if obj.get("type") == "vehicle":
                    color = (200, 100, 0)
                elif obj.get("type") == "structure":
                    color = (100, 100, 120)
                elif obj.get("type") == "vegetation":
                    color = (0, 150, 80)
                elif obj.get("type") == "effect":
                    color = (100, 50, 150)
                
                draw.rectangle([x - size//2, y - size//2, x + size//2, y + size//2], fill=color)
            
            # Title
            try:
                draw.text((10, 10), f"Scene: {scene_type}", fill=(0, 229, 255))
                draw.text((10, 25), f"Objects: {len(scene.get('objects', []))}", fill=(150, 150, 170))
            except Exception:
                pass
            
            img.save(output_path)
            return output_path
        except Exception:
            return None
    
    # =========================================================================
    # BATCH MATERIALIZATION
    # =========================================================================
    
    def materialize_batch(self, prompts: List[str], **kwargs) -> List[MaterializerResult]:
        """
        Materialize multiple prompts with progress tracking.
        
        kwargs:
            output_type: Force same type for all
            progress_callback: Optional callable(progress_pct, current_index, total, current_prompt)
        """
        progress_callback = kwargs.pop("progress_callback", None)
        results = []
        total = len(prompts)
        
        for i, prompt in enumerate(prompts):
            if progress_callback:
                progress_callback((i / total) * 100, i, total, prompt)
            
            result = self.materialize(prompt, **kwargs)
            results.append(result)
            
            if progress_callback:
                progress_callback(((i + 1) / total) * 100, i + 1, total, prompt)
        
        return results
    
    # =========================================================================
    # ENGINE SELECTION
    # =========================================================================
    
    def set_engine(self, output_type: str, engine_name: str) -> bool:
        """
        Select which engine to use for a given output type.
        
        Available engines:
          image:       sd, procedural
          mesh:        trimesh, tripo3d, meshy, openscad
          audio:       synth, procedural
          video:       procedural
        """
        valid_engines = {
            "image": ["sd", "procedural"],
            "mesh": ["trimesh", "tripo3d", "meshy", "openscad"],
            "audio": ["synth", "procedural"],
            "video": ["procedural"],
        }
        
        output_type = output_type.lower()
        if output_type not in valid_engines:
            logger.warning(f"Unknown output type: {output_type}")
            return False
        
        if engine_name.lower() not in valid_engines[output_type]:
            logger.warning(
                f"Invalid engine '{engine_name}' for '{output_type}'. "
                f"Valid: {valid_engines[output_type]}"
            )
            return False
        
        self._engines[output_type] = engine_name.lower()
        logger.info(f"Engine set: {output_type} -> {engine_name}")
        return True
    
    def get_engine(self, output_type: str) -> str:
        """Get the current engine for an output type."""
        return self._engines.get(output_type.lower(), "procedural")
    
    def get_available_engines(self) -> Dict[str, List[str]]:
        """Get all available engines per output type."""
        return {
            "image": ["sd", "procedural"],
            "mesh": ["trimesh", "tripo3d", "meshy", "openscad"],
            "audio": ["synth", "procedural"],
            "video": ["procedural"],
        }
    
    # =========================================================================
    # GENERATION QUEUE
    # =========================================================================
    
    def queue_generation(self, prompt: str, output_type: str = None,
                         priority: int = 0, **kwargs) -> int:
        """
        Queue a generation task.
        
        Returns: task_id (int)
        """
        if self._queue_lock is None:
            import threading
            self._queue_lock = threading.Lock()
        
        with self._queue_lock:
            task_id = len(self._queue)
            task = {
                "task_id": task_id,
                "prompt": prompt,
                "output_type": output_type,
                "priority": priority,
                "kwargs": kwargs,
                "status": "queued",
                "result": None,
                "progress": 0.0,
            }
            self._queue.append(task)
            # Sort by priority (higher first)
            self._queue.sort(key=lambda t: t["priority"], reverse=True)
        
        logger.info(f"Queued task {task_id}: '{prompt[:40]}...' (priority={priority})")
        return task_id
    
    def process_queue(self, max_tasks: int = None) -> List[MaterializerResult]:
        """
        Process queued tasks in priority order.
        
        Returns: list of results for processed tasks
        """
        if self._queue_lock is None:
            return []
        
        results = []
        with self._queue_lock:
            queued = [t for t in self._queue if t["status"] == "queued"]
            if max_tasks:
                queued = queued[:max_tasks]
        
        for task in queued:
            with self._queue_lock:
                task["status"] = "processing"
                task["progress"] = 0.0
            
            self._notify_progress(task)
            
            output_type = None
            if task["output_type"]:
                try:
                    output_type = OutputType(task["output_type"])
                except ValueError:
                    output_type = None
            
            result = self.materialize(task["prompt"], output_type=output_type, **task["kwargs"])
            
            with self._queue_lock:
                task["status"] = "completed"
                task["progress"] = 100.0
                task["result"] = result
            
            self._notify_progress(task)
            results.append(result)
        
        return results
    
    def get_queue_status(self) -> List[Dict[str, Any]]:
        """Get status of all queued tasks."""
        if self._queue_lock is None:
            return []
        
        with self._queue_lock:
            return [
                {
                    "task_id": t["task_id"],
                    "prompt": t["prompt"][:60],
                    "output_type": t["output_type"],
                    "priority": t["priority"],
                    "status": t["status"],
                    "progress": t["progress"],
                }
                for t in self._queue
            ]
    
    def cancel_task(self, task_id: int) -> bool:
        """Cancel a queued task (only if still queued)."""
        if self._queue_lock is None:
            return False
        
        with self._queue_lock:
            for task in self._queue:
                if task["task_id"] == task_id and task["status"] == "queued":
                    task["status"] = "cancelled"
                    logger.info(f"Cancelled task {task_id}")
                    return True
        return False
    
    def clear_queue(self):
        """Clear all queued tasks."""
        if self._queue_lock is not None:
            with self._queue_lock:
                self._queue = [t for t in self._queue if t["status"] == "processing"]
    
    def set_progress_callback(self, callback):
        """Set callback for progress updates: callback(task_dict)"""
        self._progress_callback = callback
    
    def _notify_progress(self, task):
        """Notify progress callback."""
        if self._progress_callback:
            try:
                self._progress_callback(task)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
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
        sd_available = False
        try:
            sd_available = self.image_generator.sd_engine.is_available()
        except Exception:
            pass
        
        return {
            "seed": self.seed,
            "output_dir": str(self.output_dir),
            "engines": {
                "procedural": "always_available",
                "stable_diffusion": sd_available,
                "trimesh": self.mesh_engine is not None,
                "audio_synth": True,
                "video_procedural": True,
                "vr_scene": True,
            },
            "engine_selection": dict(self._engines),
            "queue_size": len([t for t in self._queue if t["status"] == "queued"]) if self._queue else 0,
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
