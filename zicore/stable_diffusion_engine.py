"""
ZICORE Stable Diffusion Engine
AI Image Generation via CPU Inference (Hugging Face Diffusers)

Supports:
- Stable Diffusion 1.5 (512x512)
- SDXL Turbo (512x512, 1-4 steps)
- Text-to-Image generation
- Image-to-Image transformation
- Image inpainting

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
"""
from __future__ import annotations

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger("zicore.stable_diffusion")

# Lazy imports — avoid blocking on torch initialization at module load time
HAS_TORCH = None
HAS_DIFFUSERS = None
HAS_PIL = None

def _check_deps():
    global HAS_TORCH, HAS_DIFFUSERS, HAS_PIL
    if HAS_TORCH is None:
        try:
            import torch
            HAS_TORCH = True
        except ImportError:
            HAS_TORCH = False
            logger.warning("PyTorch not installed. Stable Diffusion unavailable.")
    if HAS_DIFFUSERS is None:
        try:
            from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
            HAS_DIFFUSERS = True
        except ImportError:
            HAS_DIFFUSERS = False
            logger.warning("diffusers not installed. Run: pip install diffusers[torch]")
    if HAS_PIL is None:
        try:
            from PIL import Image
            HAS_PIL = True
        except ImportError:
            HAS_PIL = False


@dataclass
class SDConfig:
    """Stable Diffusion configuration"""
    model_id: str = "stable-diffusion-v1-5/stable-diffusion-v1-5"
    device: str = "cpu"
    dtype: str = "float32"  # CPU needs float32
    width: int = 512
    height: int = 512
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    max_length: int = 77
    
    # Model variants
    MODELS = {
        "sd15": "stable-diffusion-v1-5/stable-diffusion-v1-5",
        "sdxl-turbo": "stabilityai/sdxl-turbo",
        "sd21": "stabilityai/stable-diffusion-2-1",
        "dreamshaper": "Lykon/DreamShaper",
    }
    
    @classmethod
    def get_model(cls, name: str) -> str:
        return cls.MODELS.get(name, name)


class StableDiffusionEngine:
    """
    ZICORE Stable Diffusion Engine for AI image generation.
    Runs on CPU with optimized settings.
    """
    
    def __init__(self, config: SDConfig = None):
        self.config = config or SDConfig()
        self.pipe = None
        self.loaded = False
        self.output_dir = Path(__file__).parent.parent / "output" / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def is_available(self) -> bool:
        """Check if Stable Diffusion can be used."""
        _check_deps()
        return HAS_TORCH and HAS_DIFFUSERS and HAS_PIL
    
    def load_model(self, model_name: str = None) -> bool:
        """
        Load the Stable Diffusion model.
        
        Args:
            model_name: Model identifier or shortcut (sd15, sdxl-turbo, etc.)
        
        Returns:
            True if model loaded successfully
        """
        if not self.is_available():
            logger.error("Stable Diffusion dependencies not available")
            return False
        
        try:
            model_id = SDConfig.get_model(model_name or self.config.model_id)
            logger.info(f"Loading Stable Diffusion model: {model_id}")
            
            start_time = time.time()
            
            # Load pipeline with CPU-optimized settings
            self.pipe = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float32,  # CPU needs float32
                safety_checker=None,  # Disable for speed
                requires_safety_checker=False,
            )
            
            # Use DPM-Solver for faster inference
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config
            )
            
            # Move to CPU
            self.pipe = self.pipe.to(self.config.device)
            
            # Enable attention slicing for memory efficiency
            self.pipe.enable_attention_slicing()
            
            load_time = time.time() - start_time
            logger.info(f"Model loaded in {load_time:.2f}s")
            
            self.loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.loaded = False
            return False
    
    def generate_image(self, prompt: str, negative_prompt: str = None,
                       width: int = None, height: int = None,
                       steps: int = None, guidance: float = None,
                       seed: int = None) -> Optional[Image.Image]:
        """
        Generate an image from text prompt.
        
        Args:
            prompt: Text description of desired image
            negative_prompt: What to avoid in the image
            width: Image width (default: 512)
            height: Image height (default: 512)
            steps: Number of inference steps (default: 30)
            guidance: Guidance scale (default: 7.5)
            seed: Random seed for reproducibility
        
        Returns:
            Generated PIL Image or None on failure
        """
        if not self.loaded:
            if not self.load_model():
                return None
        
        try:
            # Use config defaults if not specified
            width = width or self.config.width
            height = height or self.config.height
            steps = steps or self.config.num_inference_steps
            guidance = guidance or self.config.guidance_scale
            
            # Set seed for reproducibility
            if seed is not None:
                generator = torch.Generator(device=self.config.device).manual_seed(seed)
            else:
                generator = None
            
            logger.info(f"Generating image: '{prompt[:50]}...' ({width}x{height}, {steps} steps)")
            
            start_time = time.time()
            
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt or "blurry, bad quality, distorted, ugly",
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=guidance,
                generator=generator,
            )
            
            image = result.images[0]
            
            gen_time = time.time() - start_time
            logger.info(f"Image generated in {gen_time:.2f}s")
            
            return image
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None
    
    def generate_batch(self, prompts: List[str], **kwargs) -> List[Optional[Image.Image]]:
        """
        Generate multiple images from prompts.
        
        Args:
            prompts: List of text prompts
            **kwargs: Additional parameters for generate_image
        
        Returns:
            List of generated images
        """
        images = []
        for i, prompt in enumerate(prompts):
            logger.info(f"Generating image {i+1}/{len(prompts)}")
            image = self.generate_image(prompt, **kwargs)
            images.append(image)
        return images
    
    def image_to_image(self, prompt: str, init_image: Image.Image,
                       strength: float = 0.75, **kwargs) -> Optional[Image.Image]:
        """
        Transform an existing image based on text prompt.
        
        Args:
            prompt: Text description of desired transformation
            init_image: Starting image
            strength: How much to transform (0.0 = no change, 1.0 = full change)
        
        Returns:
            Transformed PIL Image or None on failure
        """
        if not self.loaded:
            if not self.load_model():
                return None
        
        try:
            from diffusers import StableDiffusionImg2ImgPipeline
            
            # Create img2img pipeline
            img2img_pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
                self.config.model_id,
                torch_dtype=torch.float32,
                safety_checker=None,
                requires_safety_checker=False,
            )
            img2img_pipe = img2img_pipe.to(self.config.device)
            img2img_pipe.enable_attention_slicing()
            
            # Resize init image
            init_image = init_image.resize((self.config.width, self.config.height))
            
            result = img2img_pipe(
                prompt=prompt,
                image=init_image,
                strength=strength,
                num_inference_steps=kwargs.get('steps', 30),
                guidance_scale=kwargs.get('guidance', 7.5),
            )
            
            return result.images[0]
            
        except Exception as e:
            logger.error(f"Image-to-image failed: {e}")
            return None
    
    def save_image(self, image: Image.Image, filename: str = None,
                   prefix: str = "zicore") -> str:
        """
        Save generated image to disk.
        
        Args:
            image: PIL Image to save
            filename: Output filename (auto-generated if None)
            prefix: Filename prefix
        
        Returns:
            Path to saved image
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"{prefix}_{timestamp}.png"
        
        filepath = self.output_dir / filename
        image.save(filepath)
        logger.info(f"Image saved to: {filepath}")
        
        return str(filepath)
    
    def get_status(self) -> dict:
        """Get engine status information."""
        return {
            "available": self.is_available(),
            "loaded": self.loaded,
            "model": self.config.model_id,
            "device": self.config.device,
            "dtype": self.config.dtype,
            "max_resolution": f"{self.config.width}x{self.config.height}",
            "output_dir": str(self.output_dir),
        }


# =============================================================================
# FALLBACK: Procedural Image Generation (when SD not available)
# =============================================================================

class ProceduralImageFallback:
    """
    Fallback image generation using Pillow when Stable Diffusion is not available.
    Generates simple but visually appealing images based on prompts.
    """
    
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "output" / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_image(self, prompt: str, width: int = 512,
                       height: int = 512) -> Optional[Image.Image]:
        """Generate procedural image based on prompt keywords."""
        _check_deps()
        if not HAS_PIL:
            return None
        
        # Parse prompt for keywords
        prompt_lower = prompt.lower()
        
        # Create base image
        img = Image.new('RGB', (width, height), (10, 15, 25))
        draw = ImageDraw.Draw(img)
        
        # Sky gradient
        for y in range(height // 2):
            r = int(10 + (y / height) * 40)
            g = int(15 + (y / height) * 60)
            b = int(40 + (y / height) * 100)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Ground
        for y in range(height // 2, height):
            r = int(20 + (y - height/2) / height * 30)
            g = int(30 + (y - height/2) / height * 20)
            b = int(20 + (y - height/2) / height * 15)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add elements based on prompt
        if 'star' in prompt_lower or 'space' in prompt_lower:
            # Stars
            for _ in range(100):
                x = random.randint(0, width)
                y = random.randint(0, height // 2)
                size = random.randint(1, 3)
                brightness = random.randint(150, 255)
                draw.ellipse([x, y, x+size, y+size], fill=(brightness, brightness, brightness))
        
        if 'sun' in prompt_lower or 'sunset' in prompt_lower:
            # Sun
            sun_y = height // 3
            for r in range(50, 0, -1):
                color = (255, max(100, 200 - r*2), 0)
                draw.ellipse([width//2-r, sun_y-r, width//2+r, sun_y+r], fill=color)
        
        if 'mountain' in prompt_lower:
            # Mountains
            points = [(0, height//2)]
            for x in range(0, width, 20):
                y = height//2 - random.randint(20, 80)
                points.append((x, y))
            points.append((width, height//2))
            draw.polygon(points, fill=(40, 50, 60))
        
        if 'tree' in prompt_lower or 'forest' in prompt_lower:
            # Trees
            for _ in range(10):
                x = random.randint(0, width)
                y = height//2 + random.randint(0, height//4)
                # Trunk
                draw.rectangle([x-3, y-20, x+3, y], fill=(80, 50, 30))
                # Foliage
                draw.ellipse([x-15, y-40, x+15, y-10], fill=(30, 80, 30))
        
        if 'water' in prompt_lower or 'ocean' in prompt_lower or 'sea' in prompt_lower:
            # Water
            water_y = height * 2 // 3
            for y in range(water_y, height):
                wave = int(math.sin(y * 0.1) * 5)
                r = 20 + wave
                g = 40 + wave
                b = 100 + wave
                draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        if 'moon' in prompt_lower:
            # Moon
            moon_x, moon_y = width * 3 // 4, height // 4
            draw.ellipse([moon_x-25, moon_y-25, moon_x+25, moon_y+25], fill=(220, 220, 200))
            draw.ellipse([moon_x-15, moon_y-30, moon_x+5, moon_y-10], fill=(10, 15, 25))
        
        return img
    
    def save_image(self, image: Image.Image, prompt: str) -> str:
        """Save image with prompt-based filename."""
        timestamp = int(time.time())
        safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt.replace(' ', '_')
        filename = f"procedural_{safe_prompt}_{timestamp}.png"
        filepath = self.output_dir / filename
        image.save(filepath)
        return str(filepath)


# =============================================================================
# UNIFIED INTERFACE
# =============================================================================

class ZICOREImageGenerator:
    """
    Unified image generation interface.
    Tries Stable Diffusion first, falls back to procedural generation.
    """
    
    def __init__(self):
        self.sd_engine = StableDiffusionEngine()
        self.procedural = ProceduralImageFallback()
    
    def generate(self, prompt: str, width: int = 512, height: int = 512,
                 use_sd: bool = True) -> Tuple[Optional[Image.Image], str]:
        """
        Generate image from prompt.
        
        Returns:
            Tuple of (image, method_used)
        """
        if use_sd and self.sd_engine.is_available():
            if not self.sd_engine.loaded:
                self.sd_engine.load_model()
            
            if self.sd_engine.loaded:
                image = self.sd_engine.generate_image(prompt, width=width, height=height)
                if image:
                    return image, "stable_diffusion"
        
        # Fallback to procedural
        image = self.procedural.generate_image(prompt, width, height)
        return image, "procedural"
    
    def get_status(self) -> dict:
        """Get generator status."""
        _check_deps()
        return {
            "sd_available": self.sd_engine.is_available(),
            "sd_loaded": self.sd_engine.loaded,
            "fallback_available": HAS_PIL,
            "sd_config": self.sd_engine.get_status(),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_image_generator() -> ZICOREImageGenerator:
    """Create a new image generator instance."""
    return ZICOREImageGenerator()


# =============================================================================
# ZINEMOTION SIGNATURE
# =============================================================================

__author__ = "ZineMotion Foundation — Aerospace Division"
__version__ = "5.0.0"
__license__ = "ZICORE System"

if __name__ == "__main__":
    # Demo
    print("=== ZICORE Stable Diffusion Engine v5.0.0 ===")
    print(f"Author: {__author__}\n")
    
    generator = create_image_generator()
    status = generator.get_status()
    
    print("Status:")
    for key, value in status.items():
        if key != 'sd_config':
            print(f"  {key}: {value}")
    
    print("\nSD Config:")
    for key, value in status['sd_config'].items():
        print(f"  {key}: {value}")
    
    # Test procedural fallback
    print("\nTesting procedural fallback...")
    image, method = generator.generate("a mountain landscape with stars", 256, 256, use_sd=False)
    if image:
        path = generator.procedural.save_image(image, "mountain landscape")
        print(f"  Generated via {method}: {path}")
    
    print("\n=== Complete ===")
