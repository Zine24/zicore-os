"""
ZICORE Procedural Generation Engine
Materialize ideas into reality through algorithmic content generation.

Techniques: Noise Functions, Cellular Automata, Wave Function Collapse,
            Voronoi/Delaunay, Fractals, L-Systems, Markov Chains, Graph Algorithms

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
"""

import math
import random
import hashlib
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass
class Grid2D:
    """2D grid container for procedural generation"""
    width: int
    height: int
    cells: List[List[int]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.cells:
            self.cells = [[0 for _ in range(self.width)] for _ in range(self.height)]
    
    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x]
        return 0
    
    def set(self, x: int, y: int, value: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.cells[y][x] = value
    
    def count_neighbors(self, x: int, y: int, include_diagonal: bool = True) -> int:
        count = 0
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue
                if not include_diagonal and abs(dx) + abs(dy) > 1:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    count += self.cells[ny][nx]
        return count


class ProceduralEngine:
    """
    Integral procedural generation engine for ZICORE Materializer.
    Generates terrain, caves, plants, text, levels, and more.
    """
    
    def __init__(self, seed: int = None):
        self.seed = seed or random.randint(0, 999999)
        random.seed(self.seed)
        if HAS_NUMPY:
            np.random.seed(self.seed % (2**31))
    
    # =========================================================================
    # 1. NOISE FUNCTIONS (Perlin, Simplex, Worley)
    # =========================================================================
    
    def perlin_noise_2d(self, width: int, height: int, scale: float = 50.0,
                        octaves: int = 6, persistence: float = 0.5) -> List[List[float]]:
        """
        Generate 2D Perlin-like noise for terrain, clouds, textures.
        Pure Python implementation (no external noise library required).
        """
        if not HAS_NUMPY:
            return [[0.0] * width for _ in range(height)]
        
        result = np.zeros((height, width))
        
        for octave in range(octaves):
            freq = 2 ** octave
            amp = persistence ** octave
            
            # Generate permutation table for this octave
            perm = list(range(256))
            random.shuffle(perm)
            perm = perm + perm
            
            for y in range(height):
                for x in range(width):
                    # Scale coordinates
                    sx = x / scale * freq
                    sy = y / scale * freq
                    
                    # Grid cell coordinates
                    x0 = int(sx) & 255
                    y0 = int(sy) & 255
                    x1 = (x0 + 1) & 255
                    y1 = (y0 + 1) & 255
                    
                    # Relative coordinates within cell
                    fx = sx - int(sx)
                    fy = sy - int(sy)
                    
                    # Fade curves
                    u = fx * fx * (3 - 2 * fx)
                    v = fy * fy * (3 - 2 * fy)
                    
                    # Hash corners
                    def hash_coord(px, py):
                        return perm[perm[px] + py] / 255.0
                    
                    # Gradient dot products
                    g00 = hash_coord(x0, y0)
                    g10 = hash_coord(x1, y0)
                    g01 = hash_coord(x0, y1)
                    g11 = hash_coord(x1, y1)
                    
                    # Bilinear interpolation
                    nx0 = g00 + u * (g10 - g00)
                    nx1 = g01 + u * (g11 - g01)
                    value = nx0 + v * (nx1 - nx0)
                    
                    result[y][x] += value * amp
        
        # Normalize to 0-1
        if result.max() > 0:
            result = result / result.max()
        
        return result.tolist()
    
    def worley_noise_2d(self, width: int, height: int, num_points: int = 50,
                        distance_type: str = 'euclidean') -> List[List[float]]:
        """
        Generate Worley/Voronoi noise for organic patterns, cell textures.
        """
        if not HAS_NUMPY:
            return [[0.0] * width for _ in range(height)]
        
        # Generate random seed points
        points = np.random.rand(num_points, 2) * [width, height]
        
        result = np.zeros((height, width))
        
        for y in range(height):
            for x in range(width):
                # Find distances to all points
                distances = np.sqrt(np.sum((points - [x, y]) ** 2, axis=1))
                
                if distance_type == 'euclidean':
                    result[y][x] = np.min(distances)
                elif distance_type == 'manhattan':
                    result[y][x] = np.min(np.abs(points[:, 0] - x) + np.abs(points[:, 1] - y))
                elif distance_type == 'chebyshev':
                    result[y][x] = np.min(np.maximum(np.abs(points[:, 0] - x), np.abs(points[:, 1] - y)))
        
        # Normalize
        if result.max() > 0:
            result = result / result.max()
        
        return result.tolist()
    
    def generate_terrain(self, width: int = 256, height: int = 256,
                         scale: float = 50.0, mountains: bool = True) -> List[List[float]]:
        """
        Generate realistic terrain heightmap using layered noise.
        Returns values 0.0 (sea level) to 1.0 (peak).
        """
        terrain = self.perlin_noise_2d(width, height, scale, octaves=6)
        
        if mountains:
            # Add ridged noise for mountain ridges
            ridged = self.perlin_noise_2d(width, height, scale * 0.7, octaves=4)
            for y in range(height):
                for x in range(width):
                    # Ridge formula
                    ridged[y][x] = 1.0 - abs(ridged[y][x] * 2 - 1)
                    terrain[y][x] = terrain[y][x] * 0.6 + ridged[y][x] * 0.4
        
        return terrain
    
    # =========================================================================
    # 2. CELLULAR AUTOMATA (Caves, Patterns, Game of Life)
    # =========================================================================
    
    def cellular_cave(self, width: int = 80, height: int = 40,
                      fill_prob: float = 0.4, iterations: int = 5,
                      birth_limit: int = 4, death_limit: int = 4) -> Grid2D:
        """
        Generate cave-like structures using cellular automata.
        Perfect for dungeon generation, underground levels.
        """
        grid = Grid2D(width, height)
        
        # Initialize with random fill
        for y in range(height):
            for x in range(width):
                if random.random() < fill_prob:
                    grid.set(x, y, 1)
        
        # Apply automata rules
        for _ in range(iterations):
            new_grid = Grid2D(width, height)
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    neighbors = grid.count_neighbors(x, y)
                    if neighbors > birth_limit:
                        new_grid.set(x, y, 1)
                    elif neighbors < death_limit:
                        new_grid.set(x, y, 0)
                    else:
                        new_grid.set(x, y, grid.get(x, y))
            grid = new_grid
        
        return grid
    
    def game_of_life(self, width: int = 50, height: int = 50,
                     density: float = 0.3, steps: int = 50) -> Grid2D:
        """
        Conway's Game of Life simulation.
        Returns final state after N steps.
        """
        grid = Grid2D(width, height)
        
        # Initialize with density
        for y in range(height):
            for x in range(width):
                if random.random() < density:
                    grid.set(x, y, 1)
        
        # Run simulation
        for _ in range(steps):
            new_grid = Grid2D(width, height)
            for y in range(height):
                for x in range(width):
                    neighbors = grid.count_neighbors(x, y, include_diagonal=True)
                    current = grid.get(x, y)
                    
                    if current == 1:
                        # Survival: 2 or 3 neighbors
                        new_grid.set(x, y, 1 if neighbors in (2, 3) else 0)
                    else:
                        # Birth: exactly 3 neighbors
                        new_grid.set(x, y, 1 if neighbors == 3 else 0)
            grid = new_grid
        
        return grid
    
    def wireless_automata(self, width: int = 80, height: int = 40,
                          steps: int = 3) -> Grid2D:
        """
        Generate rooms and corridors using cellular automata variant.
        Good for dungeon layouts.
        """
        # Start with random fill
        grid = self.cellular_cave(width, height, fill_prob=0.45, iterations=4)
        
        # Smooth pass
        for _ in range(steps):
            new_grid = Grid2D(width, height)
            for y in range(1, height - 1):
                for x in range(1, width - 1):
                    neighbors = grid.count_neighbors(x, y)
                    if neighbors >= 5:
                        new_grid.set(x, y, 1)
                    elif neighbors <= 3:
                        new_grid.set(x, y, 0)
                    else:
                        new_grid.set(x, y, grid.get(x, y))
            grid = new_grid
        
        return grid
    
    # =========================================================================
    # 3. WAVE FUNCTION COLLAPSE (Level Generation)
    # =========================================================================
    
    def wave_function_collapse(self, width: int = 20, height: int = 20,
                               num_tile_types: int = 4) -> List[List[int]]:
        """
        Simplified WFC for tile-based level generation.
        Tiles: 0=empty, 1=wall, 2=floor, 3=door
        
        Rules: walls connect to walls, floors connect to floors, doors connect both.
        """
        # Adjacency rules: allowed neighbors for each tile type
        rules = {
            0: [0, 1],        # Empty: can have empty or wall neighbors
            1: [1, 2, 3],     # Wall: can have wall, floor, or door neighbors
            2: [2, 3],        # Floor: can have floor or door neighbors
            3: [1, 2, 3],     # Door: can have wall, floor, or door neighbors
        }
        
        # Initialize grid with all possibilities
        grid = [[set(range(num_tile_types)) for _ in range(width)] for _ in range(height)]
        
        def get_valid_neighbors(x, y, tile_type):
            """Get valid tile types for neighbors given current tile"""
            return rules.get(tile_type, [])
        
        def collapse_cell(x, y):
            """Collapse a cell to a single value"""
            possible = grid[y][x]
            if len(possible) == 1:
                return list(possible)[0]
            
            # Choose based on neighbors
            chosen = random.choice(list(possible))
            grid[y][x] = {chosen}
            return chosen
        
        def propagate(x, y):
            """Propagate constraints to neighbors"""
            stack = [(x, y)]
            visited = set()
            
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in visited:
                    continue
                visited.add((cx, cy))
                
                current = grid[cy][cx]
                if len(current) != 1:
                    continue
                
                tile = list(current)[0]
                valid_neighbors = get_valid_neighbors(cx, cy, tile)
                
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        old_possible = grid[ny][nx].copy()
                        grid[ny][nx] = grid[ny][nx].intersection(set(valid_neighbors))
                        if grid[ny][nx] != old_possible:
                            stack.append((nx, ny))
        
        # Find cell with minimum entropy (fewest possibilities)
        def find_min_entropy():
            min_entropy = float('inf')
            min_cell = None
            for y in range(height):
                for x in range(width):
                    entropy = len(grid[y][x])
                    if 1 < entropy < min_entropy:
                        min_entropy = entropy
                        min_cell = (x, y)
            return min_cell
        
        # Collapse all cells
        while True:
            cell = find_min_entropy()
            if cell is None:
                break
            x, y = cell
            collapse_cell(x, y)
            propagate(x, y)
        
        # Extract final grid
        result = []
        for y in range(height):
            row = []
            for x in range(width):
                cell = grid[y][x]
                row.append(list(cell)[0] if len(cell) == 1 else 0)
            result.append(row)
        
        return result
    
    # =========================================================================
    # 4. VORONOI / DELAUNAY (Maps, Regions)
    # =========================================================================
    
    def voronoi_regions(self, width: int = 100, height: int = 100,
                        num_regions: int = 15) -> List[List[int]]:
        """
        Generate region map using Voronoi diagram.
        Returns grid with region IDs (0 to num_regions-1).
        """
        if not HAS_NUMPY:
            return [[0] * width for _ in range(height)]
        
        # Generate seed points
        seeds = [(random.randint(0, width-1), random.randint(0, height-1), i)
                 for i in range(num_regions)]
        
        # Assign each cell to nearest seed
        grid = [[0] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                min_dist = float('inf')
                min_region = 0
                for sx, sy, region_id in seeds:
                    dist = math.sqrt((x - sx)**2 + (y - sy)**2)
                    if dist < min_dist:
                        min_dist = dist
                        min_region = region_id
                grid[y][x] = min_region
        
        return grid
    
    def delaunay_triangulation(self, points: List[Tuple[int, int]]) -> List[Tuple[int, int, int]]:
        """
        Simplified Delaunay triangulation.
        Returns list of triangles as (p1_idx, p2_idx, p3_idx).
        
        Note: For production use, consider scipy.spatial.Delaunay
        """
        if len(points) < 3:
            return []
        
        # Simple incremental Delaunay (O(n^2) - sufficient for small point sets)
        triangles = []
        
        # Create super triangle
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        
        dx = max_x - min_x
        dy = max_y - min_y
        dmax = max(dx, dy)
        
        midx = (min_x + max_x) / 2
        midy = (min_y + max_y) / 2
        
        # Super triangle vertices (large enough to contain all points)
        super_tri = [
            (midx - 20 * dmax, midy - dmax),
            (midx, midy + 20 * dmax),
            (midx + 20 * dmax, midy - dmax)
        ]
        
        # Add super triangle to triangles list
        all_points = list(points) + super_tri
        triangles.append((len(points), len(points) + 1, len(points) + 2))
        
        # Add each point one by one
        for i, p in enumerate(points):
            bad_triangles = []
            
            # Find triangles whose circumcircle contains the new point
            for tri in triangles:
                p1, p2, p3 = all_points[tri[0]], all_points[tri[1]], all_points[tri[2]]
                
                # Calculate circumcircle
                ax, ay = p1
                bx, by = p2
                cx, cy = p3
                
                d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
                if abs(d) < 1e-10:
                    continue
                
                ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
                uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
                
                radius = math.sqrt((ax - ux)**2 + (ay - uy)**2)
                dist = math.sqrt((p[0] - ux)**2 + (p[1] - uy)**2)
                
                if dist <= radius:
                    bad_triangles.append(tri)
            
            # Find boundary of the polygonal hole
            polygon = []
            for tri in bad_triangles:
                for j in range(3):
                    edge = (tri[j], tri[(j + 1) % 3])
                    shared = False
                    for other_tri in bad_triangles:
                        if other_tri == tri:
                            continue
                        for k in range(3):
                            other_edge = (other_tri[k], other_tri[(k + 1) % 3])
                            if (edge[0] == other_edge[1] and edge[1] == other_edge[0]):
                                shared = True
                                break
                    if not shared:
                        polygon.append(edge)
            
            # Remove bad triangles
            for tri in bad_triangles:
                triangles.remove(tri)
            
            # Create new triangles from point to polygon edges
            for edge in polygon:
                new_tri = (edge[0], edge[1], i)
                triangles.append(new_tri)
        
        # Remove triangles that share vertices with super triangle
        result = []
        for tri in triangles:
            if tri[0] < len(points) and tri[1] < len(points) and tri[2] < len(points):
                result.append(tri)
        
        return result
    
    # =========================================================================
    # 5. FRACTALS (Mandelbrot, Julia, Sierpinski, Koch)
    # =========================================================================
    
    def mandelbrot(self, width: int = 800, height: int = 600,
                   max_iter: int = 100) -> List[List[int]]:
        """
        Generate Mandelbrot set.
        Returns 2D array of iteration counts.
        """
        result = [[0] * width for _ in range(height)]
        
        for y in range(height):
            for x in range(width):
                # Map pixel to complex plane
                cx = (x - width * 0.7) / (width * 0.25)
                cy = (y - height * 0.5) / (height * 0.5)
                
                zx, zy = 0.0, 0.0
                iteration = 0
                
                while zx * zx + zy * zy < 4 and iteration < max_iter:
                    xtemp = zx * zx - zy * zy + cx
                    zy = 2 * zx * zy + cy
                    zx = xtemp
                    iteration += 1
                
                result[y][x] = iteration
        
        return result
    
    def julia_set(self, width: int = 800, height: int = 600,
                  cx: float = -0.7, cy: float = 0.27015,
                  max_iter: int = 100) -> List[List[int]]:
        """
        Generate Julia set.
        """
        result = [[0] * width for _ in range(height)]
        
        for y in range(height):
            for x in range(width):
                zx = 1.5 * (x - width / 2) / (0.5 * width)
                zy = (y - height / 2) / (0.5 * height)
                
                iteration = 0
                
                while zx * zx + zy * zy < 4 and iteration < max_iter:
                    xtemp = zx * zx - zy * zy + cx
                    zy = 2 * zx * zy + cy
                    zx = xtemp
                    iteration += 1
                
                result[y][x] = iteration
        
        return result
    
    def sierpinski_triangle(self, iterations: int = 6) -> List[Tuple[int, int, int]]:
        """
        Generate Sierpinski triangle vertices.
        Returns list of triangles as (x1,y1,x2,y2,x3,y3).
        """
        # Start with single triangle
        triangles = [((0, 0), (1, 0), (0.5, math.sqrt(3)/2))]
        
        for _ in range(iterations):
            new_triangles = []
            for (x1, y1), (x2, y2), (x3, y3) in triangles:
                # Midpoints
                m1 = ((x1 + x2) / 2, (y1 + y2) / 2)
                m2 = ((x2 + x3) / 2, (y2 + y3) / 2)
                m3 = ((x1 + x3) / 2, (y1 + y3) / 2)
                
                # Three new triangles
                new_triangles.extend([
                    ((x1, y1), m1, m3),
                    (m1, (x2, y2), m2),
                    (m3, m2, (x3, y3))
                ])
            triangles = new_triangles
        
        return triangles
    
    def koch_curve(self, iterations: int = 4) -> List[Tuple[float, float]]:
        """
        Generate Koch snowflake curve points.
        """
        # Start with equilateral triangle
        points = [
            (0, 0),
            (1, 0),
            (0.5, math.sqrt(3) / 2),
            (0, 0)  # Close the curve
        ]
        
        for _ in range(iterations):
            new_points = []
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                
                # Divide into thirds
                dx = x2 - x1
                dy = y2 - y1
                
                p1 = (x1, y1)
                p2 = (x1 + dx/3, y1 + dy/3)
                p4 = (x1 + 2*dx/3, y1 + 2*dy/3)
                p5 = (x2, y2)
                
                # Peak point
                px = (x1 + x2) / 2 - dy * math.sqrt(3) / 6
                py = (y1 + y2) / 2 + dx * math.sqrt(3) / 6
                p3 = (px, py)
                
                new_points.extend([p1, p2, p3, p4])
            new_points.append(points[-1])
            points = new_points
        
        return points
    
    def dragon_curve(self, iterations: int = 10) -> List[Tuple[float, float]]:
        """
        Generate Dragon curve points.
        """
        points = [(0, 0), (1, 0)]
        
        for _ in range(iterations):
            new_points = list(points)
            cx, cy = points[-1]
            
            for i in range(len(points) - 2, -1, -1):
                x, y = points[i]
                dx = cx - x
                dy = cy - y
                
                # Rotate 90 degrees
                new_points.append((cx + dy, cy - dx))
                
                cx, cy = points[i]
            
            points = new_points
        
        return points
    
    # =========================================================================
    # 6. L-SYSTEMS (Plants, Trees, Architecture)
    # =========================================================================
    
    def l_system(self, axiom: str, rules: Dict[str, str],
                 iterations: int = 5) -> str:
        """
        Generate L-System string from axiom and rules.
        
        Example for plant:
            axiom = "X"
            rules = {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"}
        """
        current = axiom
        for _ in range(iterations):
            next_str = ""
            for char in current:
                next_str += rules.get(char, char)
            current = next_str
        return current
    
    def plant_l_system(self, iterations: int = 5) -> str:
        """
        Generate a plant/tree L-System.
        Returns turtle graphics instructions.
        """
        axiom = "X"
        rules = {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"}
        return self.l_system(axiom, rules, iterations)
    
    def koch_l_system(self, iterations: int = 4) -> str:
        """
        Generate Koch curve using L-System.
        """
        axiom = "F"
        rules = {"F": "F+F-F-F+F"}
        return self.l_system(axiom, rules, iterations)
    
    def sierpinski_l_system(self, iterations: int = 6) -> str:
        """
        Generate Sierpinski triangle using L-System.
        """
        axiom = "F-G-G"
        rules = {"F": "F-G+F+G-F", "G": "GG"}
        return self.l_system(axiom, rules, iterations)
    
    def hilbert_curve(self, iterations: int = 4) -> str:
        """
        Generate Hilbert space-filling curve.
        """
        axiom = "A"
        rules = {"A": "-BF+AFA+FB-", "B": "+AF-BFB-FA+"}
        return self.l_system(axiom, rules, iterations)
    
    def interpret_turtle(self, instructions: str, angle: float = 25.0,
                         length: float = 5.0) -> List[List[Tuple[float, float]]]:
        """
        Interpret L-System turtle graphics instructions.
        Returns list of line segments.
        """
        lines = []
        stack = []
        x, y = 0, 0
        heading = -90  # Start pointing up
        
        for char in instructions:
            if char == 'F' or char == 'G':
                # Move forward
                rad = math.radians(heading)
                nx = x + length * math.cos(rad)
                ny = y + length * math.sin(rad)
                lines.append([(x, y), (nx, ny)])
                x, y = nx, ny
            elif char == '+':
                heading += angle
            elif char == '-':
                heading -= angle
            elif char == '[':
                stack.append((x, y, heading))
            elif char == ']':
                x, y, heading = stack.pop()
        
        return lines
    
    # =========================================================================
    # 7. MARKOV CHAINS (Text Generation)
    # =========================================================================
    
    def markov_text(self, corpus: str, length: int = 200,
                    order: int = 2) -> str:
        """
        Generate text using Markov chains.
        
        Args:
            corpus: Input text to learn from
            length: Output length
            order: Markov order (lookback size)
        """
        if len(corpus) < order + 1:
            return corpus
        
        # Build transition table
        transitions = {}
        for i in range(len(corpus) - order):
            state = corpus[i:i + order]
            next_char = corpus[i + order]
            if state not in transitions:
                transitions[state] = []
            transitions[state].append(next_char)
        
        # Generate text
        state = corpus[:order]
        result = state
        
        for _ in range(length):
            if state in transitions:
                next_char = random.choice(transactions[state])
                result += next_char
                state = result[-order:]
            else:
                break
        
        return result
    
    def markov_words(self, words: List[str], length: int = 50,
                     order: int = 1) -> str:
        """
        Generate text from word list using Markov chains.
        """
        if len(words) < order + 1:
            return " ".join(words)
        
        # Build word transitions
        transitions = {}
        for i in range(len(words) - order):
            state = tuple(words[i:i + order])
            next_word = words[i + order]
            if state not in transitions:
                transitions[state] = []
            transitions[state].append(next_word)
        
        # Generate
        state = tuple(words[:order])
        result = list(state)
        
        for _ in range(length):
            if state in transitions:
                next_word = random.choice(transactions[state])
                result.append(next_word)
                state = tuple(result[-order:])
            else:
                break
        
        return " ".join(result)
    
    # =========================================================================
    # 8. GRAPH ALGORITHMS (Dungeons, Roads, Networks)
    # =========================================================================
    
    def generate_dungeon(self, width: int = 40, height: int = 30,
                         num_rooms: int = 8) -> Grid2D:
        """
        Generate dungeon layout with rooms and corridors.
        Uses BSP-like approach.
        """
        grid = Grid2D(width, height)
        rooms = []
        
        # Place rooms randomly
        for _ in range(num_rooms * 3):  # Try more times than needed
            if len(rooms) >= num_rooms:
                break
            
            room_w = random.randint(4, 8)
            room_h = random.randint(4, 6)
            room_x = random.randint(1, width - room_w - 1)
            room_y = random.randint(1, height - room_h - 1)
            
            # Check overlap
            overlap = False
            for rx, ry, rw, rh in rooms:
                if (room_x < rx + rw + 1 and room_x + room_w + 1 > rx and
                    room_y < ry + rh + 1 and room_y + room_h + 1 > ry):
                    overlap = True
                    break
            
            if not overlap:
                rooms.append((room_x, room_y, room_w, room_h))
                # Carve room
                for y in range(room_y, room_y + room_h):
                    for x in range(room_x, room_x + room_w):
                        grid.set(x, y, 2)  # 2 = floor
        
        # Connect rooms with corridors
        for i in range(len(rooms) - 1):
            x1 = rooms[i][0] + rooms[i][2] // 2
            y1 = rooms[i][1] + rooms[i][3] // 2
            x2 = rooms[i+1][0] + rooms[i+1][2] // 2
            y2 = rooms[i+1][1] + rooms[i+1][3] // 2
            
            # L-shaped corridor
            if random.random() < 0.5:
                # Horizontal first, then vertical
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    grid.set(x, y1, 2)
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    grid.set(x2, y, 2)
            else:
                # Vertical first, then horizontal
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    grid.set(x1, y, 2)
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    grid.set(x, y2, 2)
        
        # Add doors at room entrances (random positions)
        for rx, ry, rw, rh in rooms:
            if random.random() < 0.7:
                # Pick a random wall position
                side = random.choice(['top', 'bottom', 'left', 'right'])
                if side == 'top':
                    dx = random.randint(rx + 1, rx + rw - 2)
                    grid.set(dx, ry, 3)  # 3 = door
                elif side == 'bottom':
                    dx = random.randint(rx + 1, rx + rw - 2)
                    grid.set(dx, ry + rh - 1, 3)
                elif side == 'left':
                    dy = random.randint(ry + 1, ry + rh - 2)
                    grid.set(rx, dy, 3)
                else:
                    dy = random.randint(ry + 1, ry + rh - 2)
                    grid.set(rx + rw - 1, dy, 3)
        
        return grid
    
    def shortest_path(self, grid: Grid2D, start: Tuple[int, int],
                      end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        BFS shortest path on grid.
        Walls (1) are obstacles, floors (2) and doors (3) are walkable.
        """
        from collections import deque
        
        sx, sy = start
        ex, ey = end
        
        if grid.get(sx, sy) in (1, 0) or grid.get(ex, ey) in (1, 0):
            return []
        
        queue = deque([(sx, sy, [])])
        visited = {(sx, sy)}
        
        while queue:
            x, y, path = queue.popleft()
            
            if (x, y) == (ex, ey):
                return path + [(x, y)]
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in visited and grid.get(nx, ny) in (2, 3):
                    visited.add((nx, ny))
                    queue.append((nx, ny, path + [(x, y)]))
        
        return []
    
    # =========================================================================
    # 9. IMAGE GENERATION (Procedural Textures)
    # =========================================================================
    
    def generate_heightmap_image(self, terrain: List[List[float]],
                                 filename: str = "heightmap.png") -> str:
        """
        Convert heightmap to PNG image.
        """
        if not HAS_PIL:
            return ""
        
        height = len(terrain)
        width = len(terrain[0]) if height > 0 else 0
        
        img = Image.new('L', (width, height))
        pixels = img.load()
        
        for y in range(height):
            for x in range(width):
                value = int(terrain[y][x] * 255)
                pixels[x, y] = value
        
        img.save(filename)
        return filename
    
    def generate_cave_image(self, cave: Grid2D,
                            filename: str = "cave.png") -> str:
        """
        Convert cave grid to PNG image.
        """
        if not HAS_PIL:
            return ""
        
        cell_size = 8
        img = Image.new('RGB', (cave.width * cell_size, cave.height * cell_size), (10, 10, 15))
        draw = ImageDraw.Draw(img)
        
        for y in range(cave.height):
            for x in range(cave.width):
                value = cave.get(x, y)
                if value == 1:
                    color = (40, 35, 50)  # Wall
                elif value == 2:
                    color = (80, 75, 90)  # Floor
                elif value == 3:
                    color = (120, 100, 60)  # Door
                else:
                    color = (10, 10, 15)  # Empty
                
                draw.rectangle(
                    [x * cell_size, y * cell_size,
                     (x + 1) * cell_size - 1, (y + 1) * cell_size - 1],
                    fill=color
                )
        
        img.save(filename)
        return filename
    
    def generate_fractal_image(self, fractal: List[List[int]],
                               filename: str = "fractal.png",
                               colormap: str = 'hot') -> str:
        """
        Convert fractal data to PNG image with coloring.
        """
        if not HAS_PIL:
            return ""
        
        height = len(fractal)
        width = len(fractal[0]) if height > 0 else 0
        max_val = max(max(row) for row in fractal) if fractal else 1
        
        img = Image.new('RGB', (width, height))
        pixels = img.load()
        
        for y in range(height):
            for x in range(width):
                # Normalize and apply simple coloring
                t = fractal[y][x] / max_val if max_val > 0 else 0
                
                # Simple hot colormap
                if t < 0.33:
                    r = int(t * 3 * 255)
                    g = 0
                    b = 0
                elif t < 0.66:
                    r = 255
                    g = int((t - 0.33) * 3 * 255)
                    b = 0
                else:
                    r = 255
                    g = 255
                    b = int((t - 0.66) * 3 * 255)
                
                pixels[x, y] = (min(r, 255), min(g, 255), min(b, 255))
        
        img.save(filename)
        return filename
    
    # =========================================================================
    # 10. UTILITY METHODS
    # =========================================================================
    
    def grid_to_ascii(self, grid: Grid2D, symbols: Dict[int, str] = None) -> str:
        """Convert grid to ASCII representation for display."""
        if symbols is None:
            symbols = {0: '.', 1: '#', 2: ' ', 3: '+'}
        
        lines = []
        for y in range(grid.height):
            line = ""
            for x in range(grid.width):
                value = grid.get(x, y)
                line += symbols.get(value, '?')
            lines.append(line)
        
        return "\n".join(lines)
    
    def generate_procedural_texture(self, width: int, height: int,
                                     pattern: str = 'noise') -> List[List[Tuple[int, int, int]]]:
        """
        Generate procedural RGB texture.
        Patterns: 'noise', 'checker', 'stripes', 'circles', 'cells'
        """
        result = [[(0, 0, 0)] * width for _ in range(height)]
        
        if pattern == 'noise':
            noise = self.perlin_noise_2d(width, height, 30.0)
            for y in range(height):
                for x in range(width):
                    v = int(noise[y][x] * 255)
                    result[y][x] = (v, v, v)
        
        elif pattern == 'checker':
            size = 20
            for y in range(height):
                for x in range(width):
                    check = ((x // size) + (y // size)) % 2
                    v = 200 if check else 50
                    result[y][x] = (v, v, v)
        
        elif pattern == 'stripes':
            for y in range(height):
                for x in range(width):
                    v = 200 if (x % 20 < 10) else 50
                    result[y][x] = (v, v, v)
        
        elif pattern == 'circles':
            cx, cy = width // 2, height // 2
            for y in range(height):
                for x in range(width):
                    dist = math.sqrt((x - cx)**2 + (y - cy)**2)
                    v = int((math.sin(dist * 0.1) + 1) * 127)
                    result[y][x] = (v, v, v)
        
        elif pattern == 'cells':
            noise = self.worley_noise_2d(width, height, 30)
            for y in range(height):
                for x in range(width):
                    v = int(noise[y][x] * 255)
                    result[y][x] = (v, v, v)
        
        return result


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_procedural_engine(seed: int = None) -> ProceduralEngine:
    """Create a new ProceduralEngine instance."""
    return ProceduralEngine(seed=seed)


# =============================================================================
# ZINEMOTION SIGNATURE
# =============================================================================

__author__ = "ZineMotion Foundation — Aerospace Division"
__version__ = "5.0.0"
__license__ = "ZICORE System"

if __name__ == "__main__":
    # Demo: Generate sample content
    engine = create_procedural_engine(seed=42)
    
    print("=== ZICORE Procedural Generation Engine v5.0.0 ===")
    print(f"Author: {__author__}\n")
    
    # Generate terrain
    print("Generating terrain...")
    terrain = engine.generate_terrain(64, 64)
    print(f"  Terrain: {len(terrain)}x{len(terrain[0])} heightmap")
    
    # Generate cave
    print("Generating cave...")
    cave = engine.cellular_cave(40, 20)
    print(f"  Cave: {cave.width}x{cave.height}")
    print(engine.grid_to_ascii(cave))
    
    # Generate dungeon
    print("\nGenerating dungeon...")
    dungeon = engine.generate_dungeon(30, 20, 5)
    print(f"  Dungeon: {dungeon.width}x{dungeon.height}")
    
    # Generate fractal
    print("Generating Mandelbrot...")
    mandelbrot = engine.mandelbrot(40, 20)
    for row in mandelbrot:
        print(''.join(['#' if v > 50 else '.' for v in row]))
    
    # Generate L-System plant
    print("\nGenerating plant L-System...")
    plant = engine.plant_l_system(3)
    print(f"  Plant instructions: {len(plant)} characters")
    
    print("\n=== Generation Complete ===")
