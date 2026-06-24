"""
Color Harmony Generator
Generates color harmonies based on color theory principles.
Supports: Complementary, Triadic, Analogous, Split-Complementary, Tetradic, and more.
"""

import colorsys
from enum import Enum

# Import logger
try:
    from utils.logger import Logger
    logger = Logger("ColorHarmony")
except ImportError:
    logger = None


class HarmonyType(Enum):
    """Available color harmony types."""
    COMPLEMENTARY = "Complementary"
    TRIADIC = "Triadic"
    ANALOGOUS = "Analogous"
    SPLIT_COMPLEMENTARY = "Split-Complementary"
    TETRADIC = "Tetradic (Square)"
    COMPOUND = "Compound (Rectangle)"
    MONOCHROMATIC = "Monochromatic"


class ColorHarmony:
    """Generates color harmonies based on color theory."""
    
    @staticmethod
    def rgb_to_hsv(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
        """Convert RGB (0-255) to HSV (0-1, 0-1, 0-1)."""
        r, g, b = [x / 255.0 for x in rgb]
        return colorsys.rgb_to_hsv(r, g, b)
    
    @staticmethod
    def hsv_to_rgb(hsv: tuple[float, float, float]) -> tuple[int, int, int]:
        """Convert HSV (0-1, 0-1, 0-1) to RGB (0-255)."""
        r, g, b = colorsys.hsv_to_rgb(*hsv)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    @staticmethod
    def normalize_hue(hue: float) -> float:
        """Normalize hue to 0-1 range."""
        while hue < 0:
            hue += 1.0
        while hue >= 1.0:
            hue -= 1.0
        return hue
    
    @staticmethod
    def rotate_hue(base_hue: float, degrees: float) -> float:
        """Rotate hue by degrees (0-360)."""
        rotation = degrees / 360.0
        return ColorHarmony.normalize_hue(base_hue + rotation)
    
    @staticmethod
    def generate_complementary(base_color: tuple[int, int, int]) -> list[tuple[int, int, int]]:
        """
        Generate complementary color (opposite on color wheel).
        Returns: [base_color, complementary_color]
        """
        h, s, v = ColorHarmony.rgb_to_hsv(base_color)
        
        # Complementary is 180° opposite
        comp_h = ColorHarmony.rotate_hue(h, 180)
        
        colors = [
            base_color,
            ColorHarmony.hsv_to_rgb((comp_h, s, v))
        ]
        
        return colors
    
    @staticmethod
    def generate_triadic(base_color: tuple[int, int, int]) -> list[tuple[int, int, int]]:
        """
        Generate triadic harmony (3 colors evenly spaced 120° apart).
        Returns: [base_color, color2, color3]
        """
        h, s, v = ColorHarmony.rgb_to_hsv(base_color)
        
        # Triadic: 0°, 120°, 240°
        colors = [
            base_color,
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 120), s, v)),
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 240), s, v))
        ]
        
        return colors
    
    @staticmethod
    def generate_analogous(base_color: tuple[int, int, int], angle: float = 30) -> list[tuple[int, int, int]]:
        """
        Generate analogous harmony (adjacent colors on wheel).
        Default: ±30° from base color.
        Returns: [left_color, base_color, right_color]
        """
        h, s, v = ColorHarmony.rgb_to_hsv(base_color)
        
        # Analogous: typically ±30°
        colors = [
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, -angle), s, v)),
            base_color,
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, angle), s, v))
        ]
        
        return colors
    
    @staticmethod
    def generate_split_complementary(base_color: tuple[int, int, int]) -> list[tuple[int, int, int]]:
        """
        Generate split-complementary harmony.
        Base color + two colors adjacent to its complement.
        Returns: [base_color, split1, split2]
        """
        h, s, v = ColorHarmony.rgb_to_hsv(base_color)
        
        # Split-complementary: 0°, 150°, 210° (or 180° ± 30°)
        colors = [
            base_color,
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 150), s, v)),
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 210), s, v))
        ]
        
        return colors
    
    @staticmethod
    def generate_tetradic(base_color: tuple[int, int, int]) -> list[tuple[int, int, int]]:
        """
        Generate tetradic/square harmony (4 colors evenly spaced 90° apart).
        Returns: [base_color, color2, color3, color4]
        """
        h, s, v = ColorHarmony.rgb_to_hsv(base_color)
        
        # Tetradic: 0°, 90°, 180°, 270°
        colors = [
            base_color,
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 90), s, v)),
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 180), s, v)),
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 270), s, v))
        ]
        
        return colors
    
    @staticmethod
    def generate_compound(base_color: tuple[int, int, int]) -> list[tuple[int, int, int]]:
        """
        Generate compound/rectangle harmony.
        Base + complement + two intermediate colors.
        Returns: [base_color, color2, complement, color4]
        """
        h, s, v = ColorHarmony.rgb_to_hsv(base_color)
        
        # Compound: 0°, 60°, 180°, 240° (rectangle pattern)
        colors = [
            base_color,
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 60), s, v)),
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 180), s, v)),
            ColorHarmony.hsv_to_rgb((ColorHarmony.rotate_hue(h, 240), s, v))
        ]
        
        return colors
    
    @staticmethod
    def generate_monochromatic(base_color: tuple[int, int, int], count: int = 5) -> list[tuple[int, int, int]]:
        """
        Generate monochromatic harmony (same hue, varying saturation/value).
        Returns: List of colors with same hue but different brightness/saturation.
        """
        h, s, v = ColorHarmony.rgb_to_hsv(base_color)
        
        colors = []
        
        # Generate variations by adjusting value and saturation
        for i in range(count):
            factor = (i + 1) / (count + 1)  # 0.16, 0.33, 0.5, 0.66, 0.83
            
            # Vary both saturation and value
            new_s = max(0.2, min(1.0, s * (0.5 + factor)))
            new_v = max(0.3, min(1.0, v * (0.5 + factor)))
            
            colors.append(ColorHarmony.hsv_to_rgb((h, new_s, new_v)))
        
        return colors
    
    @staticmethod
    def generate_harmony(base_color: tuple[int, int, int], 
                        harmony_type: HarmonyType) -> list[tuple[int, int, int]]:
        """
        Generate harmony of specified type.
        
        Args:
            base_color: RGB tuple (0-255, 0-255, 0-255)
            harmony_type: Type of harmony to generate
            
        Returns:
            List of RGB color tuples
        """
        if harmony_type == HarmonyType.COMPLEMENTARY:
            return ColorHarmony.generate_complementary(base_color)
        elif harmony_type == HarmonyType.TRIADIC:
            return ColorHarmony.generate_triadic(base_color)
        elif harmony_type == HarmonyType.ANALOGOUS:
            return ColorHarmony.generate_analogous(base_color)
        elif harmony_type == HarmonyType.SPLIT_COMPLEMENTARY:
            return ColorHarmony.generate_split_complementary(base_color)
        elif harmony_type == HarmonyType.TETRADIC:
            return ColorHarmony.generate_tetradic(base_color)
        elif harmony_type == HarmonyType.COMPOUND:
            return ColorHarmony.generate_compound(base_color)
        elif harmony_type == HarmonyType.MONOCHROMATIC:
            return ColorHarmony.generate_monochromatic(base_color)
        else:
            return [base_color]
    
    @staticmethod
    def get_harmony_description(harmony_type: HarmonyType) -> str:
        """Get human-readable description of harmony type."""
        descriptions = {
            HarmonyType.COMPLEMENTARY: "Two colors opposite on the color wheel. Creates high contrast and vibrant combinations.",
            HarmonyType.TRIADIC: "Three colors evenly spaced around the color wheel. Creates balanced and vibrant palettes.",
            HarmonyType.ANALOGOUS: "Colors adjacent to each other on the wheel. Creates harmonious and serene combinations.",
            HarmonyType.SPLIT_COMPLEMENTARY: "Base color plus two colors adjacent to its complement. Offers contrast with less tension.",
            HarmonyType.TETRADIC: "Four colors evenly spaced (90° apart). Creates rich, dynamic palettes with lots of variety.",
            HarmonyType.COMPOUND: "Four colors in a rectangular pattern. Offers variety while maintaining balance.",
            HarmonyType.MONOCHROMATIC: "Variations of a single hue with different brightness and saturation. Creates cohesive, sophisticated looks."
        }
        return descriptions.get(harmony_type, "Unknown harmony type")
    
    @staticmethod
    def get_harmony_count(harmony_type: HarmonyType) -> int:
        """Get number of colors in harmony."""
        counts = {
            HarmonyType.COMPLEMENTARY: 2,
            HarmonyType.TRIADIC: 3,
            HarmonyType.ANALOGOUS: 3,
            HarmonyType.SPLIT_COMPLEMENTARY: 3,
            HarmonyType.TETRADIC: 4,
            HarmonyType.COMPOUND: 4,
            HarmonyType.MONOCHROMATIC: 5
        }
        return counts.get(harmony_type, 1)


# Convenience function for external use
def generate_harmony(base_color: tuple[int, int, int], 
                     harmony_name: str) -> list[tuple[int, int, int]]:
    """
    Generate harmony by name string.
    
    Args:
        base_color: RGB tuple
        harmony_name: Name of harmony type (case-insensitive)
        
    Returns:
        List of RGB color tuples
    """
    # Convert string to enum
    harmony_map = {
        "complementary": HarmonyType.COMPLEMENTARY,
        "triadic": HarmonyType.TRIADIC,
        "analogous": HarmonyType.ANALOGOUS,
        "split-complementary": HarmonyType.SPLIT_COMPLEMENTARY,
        "split complementary": HarmonyType.SPLIT_COMPLEMENTARY,
        "tetradic": HarmonyType.TETRADIC,
        "square": HarmonyType.TETRADIC,
        "compound": HarmonyType.COMPOUND,
        "rectangle": HarmonyType.COMPOUND,
        "monochromatic": HarmonyType.MONOCHROMATIC,
    }
    
    harmony_type = harmony_map.get(harmony_name.lower())
    if not harmony_type:
        return [base_color]
    
    return ColorHarmony.generate_harmony(base_color, harmony_type)