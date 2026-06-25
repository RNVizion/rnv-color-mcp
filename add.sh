#!/bin/bash
# add_color_features.sh  -  add color_difference (Delta-E) + contrast_check (WCAG) to the server.
# Overwrites the code files, bumps server.json to 1.1.0, updates the README, pushes to GitHub + HF.
#     bash add_color_features.sh
set -e
git remote get-url origin 2>/dev/null | grep -q "rnv-color-mcp" || {
  echo "Run from the rnv-color-mcp repo root."; exit 1; }

echo "1/5  Engine + API + server + tests ..."
cat > engine/color_math.py << '__CMATH_EOF__'
"""
Color mixing algorithms and color space conversions.
Handles RGB/HSV blending, weighted mixing, and color calculations.
Optimized for Python 3.13.
"""
from __future__ import annotations

import colorsys
import math

# Type aliases for better readability (Python 3.12+ style)
type RGB = tuple[int, int, int]
type RGBFloat = tuple[float, float, float]
type ColorWeight = tuple[RGB, int]


class ColorMath:
    """Color mixing and manipulation utilities."""
    
    @staticmethod
    def rgb_to_hex(rgb: RGB) -> str:
        """Convert RGB tuple to hex string."""
        return "#{:02x}{:02x}{:02x}".format(*rgb)
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> RGB:
        """Convert hex string to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = ''.join(ch * 2 for ch in hex_color)
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hsv(rgb: RGB) -> RGBFloat:
        """Convert RGB to HSV."""
        r, g, b = (c / 255.0 for c in rgb)
        return colorsys.rgb_to_hsv(r, g, b)
    
    @staticmethod
    def hsv_to_rgb(hsv: RGBFloat) -> RGB:
        """Convert HSV to RGB."""
        h, s, v = hsv
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    @staticmethod
    def rgb_to_hsl(rgb: RGB) -> RGBFloat:
        """Convert RGB to HSL."""
        r, g, b = (c / 255.0 for c in rgb)
        return colorsys.rgb_to_hls(r, g, b)
    
    @staticmethod
    def hsl_to_rgb(hsl: RGBFloat) -> RGB:
        """Convert HSL to RGB."""
        h, l, s = hsl
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    @staticmethod
    def weighted_rgb_mix(colors_weights: list[ColorWeight]) -> RGB | None:
        """
        Mix colors using weighted RGB averaging.
        
        Args:
            colors_weights: List of (color, weight) tuples where color is (r, g, b)
            
        Returns:
            Mixed color as RGB tuple, or None if no valid colors
        """
        if not colors_weights:
            return None
        
        # Filter out zero weights
        weighted = [(color, weight) for color, weight in colors_weights if weight > 0]
        if not weighted:
            return None
            
        total_weight = sum(weight for _, weight in weighted)
        if total_weight == 0:
            return None
            
        # Weighted average
        avg_r = sum(color[0] * weight for color, weight in weighted) // total_weight
        avg_g = sum(color[1] * weight for color, weight in weighted) // total_weight
        avg_b = sum(color[2] * weight for color, weight in weighted) // total_weight
        
        return (
            max(0, min(255, avg_r)),
            max(0, min(255, avg_g)),
            max(0, min(255, avg_b))
        )
    
    @staticmethod
    def weighted_hsv_mix(colors_weights: list[ColorWeight]) -> RGB | None:
        """
        Mix colors using weighted HSV averaging.
        Better for perceptually uniform color mixing.
        
        Args:
            colors_weights: List of (color, weight) tuples where color is (r, g, b)
            
        Returns:
            Mixed color as RGB tuple, or None if no valid colors
        """
        if not colors_weights:
            return None
        
        # Filter out zero weights
        weighted = [(color, weight) for color, weight in colors_weights if weight > 0]
        if not weighted:
            return None
            
        total_weight = sum(weight for _, weight in weighted)
        if total_weight == 0:
            return None
        
        # Convert to HSV for mixing
        hsv_weighted = []
        for color, weight in weighted:
            h, s, v = ColorMath.rgb_to_hsv(color)
            hsv_weighted.append(((h, s, v), weight))
        
        # Handle hue averaging (circular values)
        # Convert to Cartesian coordinates for proper averaging
        x_sum = sum(weight * s * v * math.cos(h * 2 * math.pi) for (h, s, v), weight in hsv_weighted)
        y_sum = sum(weight * s * v * math.sin(h * 2 * math.pi) for (h, s, v), weight in hsv_weighted)
        
        # Simple weighted average for saturation and value
        avg_s = sum(s * weight for (h, s, v), weight in hsv_weighted) / total_weight
        avg_v = sum(v * weight for (h, s, v), weight in hsv_weighted) / total_weight
        
        # Convert back to hue
        if x_sum == 0 and y_sum == 0:
            avg_h = 0  # Undefined hue, use 0
        else:
            avg_h = math.atan2(y_sum, x_sum) / (2 * math.pi)
            if avg_h < 0:
                avg_h += 1
        
        # Convert back to RGB
        return ColorMath.hsv_to_rgb((avg_h, avg_s, avg_v))
    
    # ==========================================================================
    # PHASE 2: REALISTIC COLOR MIXING ALGORITHMS
    # ==========================================================================
    
    @staticmethod
    def rgb_to_lab(rgb: RGB) -> RGBFloat:
        """
        Convert RGB to CIE LAB color space.
        LAB is perceptually uniform - equal distances = equal perceived differences.
        
        Args:
            rgb: RGB tuple (0-255)
            
        Returns:
            LAB tuple (L: 0-100, a: -128 to 127, b: -128 to 127)
        """
        # RGB to XYZ (sRGB with D65 illuminant)
        r, g, b = (c / 255.0 for c in rgb)
        
        # Apply gamma correction (sRGB)
        def gamma_correct(c: float) -> float:
            return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
        
        r, g, b = gamma_correct(r), gamma_correct(g), gamma_correct(b)
        
        # RGB to XYZ matrix (sRGB, D65)
        x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
        y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
        z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
        
        # XYZ to LAB (D65 reference white)
        xn, yn, zn = 0.95047, 1.0, 1.08883
        x, y, z = x / xn, y / yn, z / zn
        
        def f(t: float) -> float:
            return t ** (1/3) if t > 0.008856 else (903.3 * t + 16) / 116
        
        fx, fy, fz = f(x), f(y), f(z)
        
        L = 116 * fy - 16
        a = 500 * (fx - fy)
        b_val = 200 * (fy - fz)
        
        return (L, a, b_val)
    
    @staticmethod
    def lab_to_rgb(lab: RGBFloat) -> RGB:
        """
        Convert CIE LAB to RGB color space.
        
        Args:
            lab: LAB tuple (L: 0-100, a: -128 to 127, b: -128 to 127)
            
        Returns:
            RGB tuple (0-255)
        """
        L, a, b_val = lab
        
        # LAB to XYZ
        fy = (L + 16) / 116
        fx = a / 500 + fy
        fz = fy - b_val / 200
        
        def f_inv(t: float) -> float:
            return t ** 3 if t > 0.206893 else (116 * t - 16) / 903.3
        
        # D65 reference white
        xn, yn, zn = 0.95047, 1.0, 1.08883
        x = xn * f_inv(fx)
        y = yn * f_inv(fy)
        z = zn * f_inv(fz)
        
        # XYZ to RGB matrix (inverse of sRGB matrix)
        r = x * 3.2404542 + y * -1.5371385 + z * -0.4985314
        g = x * -0.9692660 + y * 1.8760108 + z * 0.0415560
        b = x * 0.0556434 + y * -0.2040259 + z * 1.0572252
        
        # Apply inverse gamma correction
        def gamma_inverse(c: float) -> float:
            return 1.055 * (c ** (1/2.4)) - 0.055 if c > 0.0031308 else 12.92 * c
        
        r, g, b = gamma_inverse(r), gamma_inverse(g), gamma_inverse(b)
        
        # Clamp and convert to 0-255
        return (
            max(0, min(255, int(r * 255 + 0.5))),
            max(0, min(255, int(g * 255 + 0.5))),
            max(0, min(255, int(b * 255 + 0.5)))
        )
    
    @staticmethod
    def delta_e(rgb1: RGB, rgb2: RGB, method: str = "ciede2000") -> float:
        """Perceptual color difference between two RGB colors.

        method: "ciede2000" (modern standard, default) or "cie76" (Lab Euclidean).
        ~1.0 is the threshold of a just-noticeable difference to the human eye.
        """
        L1, a1, b1 = ColorMath.rgb_to_lab(rgb1)
        L2, a2, b2 = ColorMath.rgb_to_lab(rgb2)
        if method == "cie76":
            return math.sqrt((L2 - L1) ** 2 + (a2 - a1) ** 2 + (b2 - b1) ** 2)
        # CIEDE2000 (Sharma et al. formulation)
        kL = kC = kH = 1.0
        C1 = math.hypot(a1, b1)
        C2 = math.hypot(a2, b2)
        Cbar = (C1 + C2) / 2.0
        Cbar7 = Cbar ** 7
        G = 0.5 * (1 - math.sqrt(Cbar7 / (Cbar7 + 25.0 ** 7))) if Cbar7 else 0.0
        a1p = (1 + G) * a1
        a2p = (1 + G) * a2
        C1p = math.hypot(a1p, b1)
        C2p = math.hypot(a2p, b2)
        h1p = math.degrees(math.atan2(b1, a1p)) % 360.0
        h2p = math.degrees(math.atan2(b2, a2p)) % 360.0
        dLp = L2 - L1
        dCp = C2p - C1p
        if C1p * C2p == 0:
            dhp = 0.0
        else:
            diff = h2p - h1p
            if diff > 180:
                diff -= 360
            elif diff < -180:
                diff += 360
            dhp = diff
        dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2.0))
        Lbarp = (L1 + L2) / 2.0
        Cbarp = (C1p + C2p) / 2.0
        if C1p * C2p == 0:
            hbarp = h1p + h2p
        elif abs(h1p - h2p) > 180:
            hbarp = (h1p + h2p + 360) / 2.0 if (h1p + h2p) < 360 else (h1p + h2p - 360) / 2.0
        else:
            hbarp = (h1p + h2p) / 2.0
        T = (1 - 0.17 * math.cos(math.radians(hbarp - 30))
             + 0.24 * math.cos(math.radians(2 * hbarp))
             + 0.32 * math.cos(math.radians(3 * hbarp + 6))
             - 0.20 * math.cos(math.radians(4 * hbarp - 63)))
        dtheta = 30 * math.exp(-(((hbarp - 275) / 25.0) ** 2))
        Cbarp7 = Cbarp ** 7
        Rc = 2 * math.sqrt(Cbarp7 / (Cbarp7 + 25.0 ** 7)) if Cbarp7 else 0.0
        Sl = 1 + (0.015 * (Lbarp - 50) ** 2) / math.sqrt(20 + (Lbarp - 50) ** 2)
        Sc = 1 + 0.045 * Cbarp
        Sh = 1 + 0.015 * Cbarp * T
        Rt = -math.sin(math.radians(2 * dtheta)) * Rc
        return math.sqrt(
            (dLp / (kL * Sl)) ** 2
            + (dCp / (kC * Sc)) ** 2
            + (dHp / (kH * Sh)) ** 2
            + Rt * (dCp / (kC * Sc)) * (dHp / (kH * Sh))
        )

    @staticmethod
    def relative_luminance(rgb: RGB) -> float:
        """WCAG relative luminance of a color (0.0 black .. 1.0 white)."""
        def _lin(c: float) -> float:
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = rgb
        return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

    @staticmethod
    def contrast_ratio(rgb1: RGB, rgb2: RGB) -> float:
        """WCAG contrast ratio between two colors (1.0 .. 21.0)."""
        l1 = ColorMath.relative_luminance(rgb1)
        l2 = ColorMath.relative_luminance(rgb2)
        lighter, darker = max(l1, l2), min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def lab_perceptual_mix(colors_weights: list[ColorWeight]) -> RGB | None:
        """
        Mix colors in LAB color space for perceptually uniform blending.
        
        LAB mixing produces more natural-looking gradients and blends than RGB.
        Colors mixed in LAB won't have unexpected hue shifts or muddy transitions.
        
        Args:
            colors_weights: List of (color, weight) tuples where color is (r, g, b)
            
        Returns:
            Mixed color as RGB tuple, or None if no valid colors
        """
        if not colors_weights:
            return None
        
        # Filter out zero weights
        weighted = [(color, weight) for color, weight in colors_weights if weight > 0]
        if not weighted:
            return None
        
        total_weight = sum(weight for _, weight in weighted)
        if total_weight == 0:
            return None
        
        # Convert all colors to LAB and compute weighted average
        total_L = 0.0
        total_a = 0.0
        total_b = 0.0
        
        for color, weight in weighted:
            L, a, b = ColorMath.rgb_to_lab(color)
            total_L += L * weight
            total_a += a * weight
            total_b += b * weight
        
        avg_L = total_L / total_weight
        avg_a = total_a / total_weight
        avg_b = total_b / total_weight
        
        return ColorMath.lab_to_rgb((avg_L, avg_a, avg_b))
    
    @staticmethod
    def subtractive_cmy_mix(colors_weights: list[ColorWeight]) -> RGB | None:
        """
        Mix colors using subtractive CMY model (like inks/dyes).
        
        Subtractive mixing simulates how pigments absorb light:
        - Yellow + Cyan = Green
        - Yellow + Magenta = Red  
        - Cyan + Magenta = Blue
        - All colors = Black
        
        Args:
            colors_weights: List of (color, weight) tuples where color is (r, g, b)
            
        Returns:
            Mixed color as RGB tuple, or None if no valid colors
        """
        if not colors_weights:
            return None
        
        # Filter out zero weights
        weighted = [(color, weight) for color, weight in colors_weights if weight > 0]
        if not weighted:
            return None
        
        total_weight = sum(weight for _, weight in weighted)
        if total_weight == 0:
            return None
        
        # Convert RGB to CMY (subtractive primaries)
        # CMY = 1 - RGB (normalized)
        total_c = 0.0
        total_m = 0.0
        total_y = 0.0
        
        for color, weight in weighted:
            r, g, b = (c / 255.0 for c in color)
            # Convert to CMY
            c = 1.0 - r
            m = 1.0 - g
            y = 1.0 - b
            
            total_c += c * weight
            total_m += m * weight
            total_y += y * weight
        
        # Average CMY values
        avg_c = total_c / total_weight
        avg_m = total_m / total_weight
        avg_y = total_y / total_weight
        
        # Convert back to RGB
        r = (1.0 - avg_c) * 255
        g = (1.0 - avg_m) * 255
        b = (1.0 - avg_y) * 255
        
        return (
            max(0, min(255, int(r))),
            max(0, min(255, int(g))),
            max(0, min(255, int(b)))
        )
    
    @staticmethod
    def rgb_to_ryb(rgb: RGB) -> RGBFloat:
        """
        Convert RGB to RYB (Red-Yellow-Blue) artist's color space.
        
        RYB is the traditional artist's color wheel where:
        - Primary: Red, Yellow, Blue
        - Secondary: Orange, Green, Purple
        
        Args:
            rgb: RGB tuple (0-255)
            
        Returns:
            RYB tuple (0-1 range)
        """
        r, g, b = (c / 255.0 for c in rgb)
        
        # Remove whiteness
        w = min(r, g, b)
        r, g, b = r - w, g - w, b - w
        
        max_g = max(r, g, b)
        
        # Get yellow out of red + green
        y = min(r, g)
        r, g = r - y, g - y
        
        # If blue and green, cut each in half and add to yellow
        if b > 0 and g > 0:
            b /= 2.0
            g /= 2.0
        
        # Redistribute remaining green
        y += g
        b += g
        
        # Normalize
        max_y = max(r, y, b)
        if max_y > 0:
            n = max_g / max_y
            r, y, b = r * n, y * n, b * n
        
        # Add whiteness back
        r, y, b = r + w, y + w, b + w
        
        return (r, y, b)
    
    @staticmethod
    def ryb_to_rgb(ryb: RGBFloat) -> RGB:
        """
        Convert RYB (Red-Yellow-Blue) to RGB.
        
        Args:
            ryb: RYB tuple (0-1 range)
            
        Returns:
            RGB tuple (0-255)
        """
        r, y, b = ryb
        
        # Remove whiteness
        w = min(r, y, b)
        r, y, b = r - w, y - w, b - w
        
        max_y = max(r, y, b)
        
        # Get green from yellow + blue
        g = min(y, b)
        y, b = y - g, b - g
        
        # If blue and green, add to each other
        if b > 0 and g > 0:
            b *= 2.0
            g *= 2.0
        
        # Redistribute yellow to red and green
        r += y
        g += y
        
        # Normalize
        max_g = max(r, g, b)
        if max_g > 0:
            n = max_y / max_g
            r, g, b = r * n, g * n, b * n
        
        # Add whiteness back
        r, g, b = r + w, g + w, b + w
        
        return (
            max(0, min(255, int(r * 255))),
            max(0, min(255, int(g * 255))),
            max(0, min(255, int(b * 255)))
        )
    
    @staticmethod
    def weighted_ryb_mix(colors_weights: list[ColorWeight]) -> RGB | None:
        """
        Mix colors using RYB (artist's color wheel) model.
        
        RYB mixing produces results closer to traditional paint mixing:
        - Yellow + Blue = Green (not gray!)
        - Red + Yellow = Orange
        - Red + Blue = Purple
        
        This is ideal for artists and designers working with physical media.
        
        Args:
            colors_weights: List of (color, weight) tuples where color is (r, g, b)
            
        Returns:
            Mixed color as RGB tuple, or None if no valid colors
        """
        if not colors_weights:
            return None
        
        # Filter out zero weights
        weighted = [(color, weight) for color, weight in colors_weights if weight > 0]
        if not weighted:
            return None
        
        total_weight = sum(weight for _, weight in weighted)
        if total_weight == 0:
            return None
        
        # Convert all colors to RYB and compute weighted average
        total_r = 0.0
        total_y = 0.0
        total_b = 0.0
        
        for color, weight in weighted:
            r, y, b = ColorMath.rgb_to_ryb(color)
            total_r += r * weight
            total_y += y * weight
            total_b += b * weight
        
        avg_r = total_r / total_weight
        avg_y = total_y / total_weight
        avg_b = total_b / total_weight
        
        return ColorMath.ryb_to_rgb((avg_r, avg_y, avg_b))
    
    @staticmethod
    def kubelka_munk_mix(colors_weights: list[ColorWeight]) -> RGB | None:
        """
        Mix colors using Kubelka-Munk theory for realistic paint/pigment simulation.
        
        Kubelka-Munk models how light interacts with pigments, accounting for:
        - Light absorption (K coefficient)
        - Light scattering (S coefficient)
        
        This produces the most realistic paint mixing results:
        - Yellow + Blue = Green (natural, not muddy)
        - Colors darken when mixed (like real paint)
        - Handles opacity and coverage naturally
        
        Simplified implementation using reflectance model.
        
        Args:
            colors_weights: List of (color, weight) tuples where color is (r, g, b)
            
        Returns:
            Mixed color as RGB tuple, or None if no valid colors
        """
        if not colors_weights:
            return None
        
        # Filter out zero weights
        weighted = [(color, weight) for color, weight in colors_weights if weight > 0]
        if not weighted:
            return None
        
        total_weight = sum(weight for _, weight in weighted)
        if total_weight == 0:
            return None
        
        # Convert RGB to reflectance (0-1) and then to K/S ratios
        # K/S = (1-R)² / (2R) where R is reflectance
        def rgb_to_ks(rgb: RGB) -> list[float]:
            """Convert RGB to K/S ratio for each channel."""
            ks = []
            for c in rgb:
                # Normalize to 0-1 reflectance
                R = max(0.001, min(0.999, c / 255.0))  # Avoid division by zero
                # Kubelka-Munk K/S ratio
                ks_val = ((1 - R) ** 2) / (2 * R)
                ks.append(ks_val)
            return ks
        
        def ks_to_rgb(ks: list[float]) -> RGB:
            """Convert K/S ratio back to RGB."""
            rgb = []
            for ks_val in ks:
                # Inverse Kubelka-Munk: R = 1 + K/S - sqrt((K/S)² + 2*K/S)
                ks_val = max(0, ks_val)  # Ensure non-negative
                discriminant = ks_val * ks_val + 2 * ks_val
                R = 1 + ks_val - math.sqrt(discriminant) if discriminant >= 0 else 0
                R = max(0, min(1, R))
                rgb.append(int(R * 255))
            return tuple(rgb)
        
        # Mix K/S values (additive in K/S space = subtractive in color space)
        total_ks = [0.0, 0.0, 0.0]
        
        for color, weight in weighted:
            ks = rgb_to_ks(color)
            normalized_weight = weight / total_weight
            for i in range(3):
                total_ks[i] += ks[i] * normalized_weight
        
        return ks_to_rgb(total_ks)
    
    # ==========================================================================
    # END PHASE 2: REALISTIC COLOR MIXING ALGORITHMS
    # ==========================================================================
    
    @staticmethod
    def calculate_average_region_color(pixels: list[RGB]) -> RGB | None:
        """
        Calculate average color of a region from pixel data.
        
        Args:
            pixels: List of RGB tuples
            
        Returns:
            Average color as RGB tuple, or None if no pixels
        """
        if not pixels:
            return None
            
        total_r = sum(pixel[0] for pixel in pixels)
        total_g = sum(pixel[1] for pixel in pixels)
        total_b = sum(pixel[2] for pixel in pixels)
        count = len(pixels)
        
        return (
            total_r // count,
            total_g // count,
            total_b // count
        )
    
    @staticmethod
    def color_distance(color1: RGB, color2: RGB) -> float:
        """
        Calculate Euclidean distance between two RGB colors.
        
        Args:
            color1, color2: RGB tuples
            
        Returns:
            Distance as float
        """
        r1, g1, b1 = color1
        r2, g2, b2 = color2
        return math.sqrt((r2 - r1) ** 2 + (g2 - g1) ** 2 + (b2 - b1) ** 2)
    
    @staticmethod
    def generate_color_palette(base_color: RGB, count: int = 5) -> list[RGB]:
        """
        Generate a color palette based on a base color.
        
        Args:
            base_color: Base RGB color
            count: Number of colors to generate
            
        Returns:
            List of RGB color tuples
        """
        h, s, v = ColorMath.rgb_to_hsv(base_color)
        colors = []
        
        for i in range(count):
            # Vary hue while keeping saturation and value similar
            new_h = (h + (i / count)) % 1.0
            new_s = max(0.1, min(1.0, s + (i - count // 2) * 0.1))
            new_v = max(0.1, min(1.0, v + (i - count // 2) * 0.1))
            colors.append(ColorMath.hsv_to_rgb((new_h, new_s, new_v)))
            
        return colors
    
    @staticmethod
    def validate_rgb(rgb: RGB) -> RGB:
        """
        Validate and clamp RGB values to valid range.
        
        Args:
            rgb: RGB tuple (may contain invalid values)
            
        Returns:
            Valid RGB tuple with values clamped to 0-255
        """
        return tuple(max(0, min(255, int(c))) for c in rgb)
    
    @staticmethod
    def clamp_rgb(r: float, g: float, b: float) -> RGB:
        """
        Clamp individual RGB values to 0-255 range.
        
        Args:
            r, g, b: RGB values (may be float or out of range)
        
        Returns:
            Valid RGB tuple with values clamped to 0-255
        
        Example:
            r, g, b = ColorMath.clamp_rgb(300, -50, 128.7)
            # Returns: (255, 0, 129)
        """
        return (
            max(0, min(255, int(r))),
            max(0, min(255, int(g))),
            max(0, min(255, int(b)))
        )
    
    @staticmethod
    def clamp_value(value: float, min_val: float = 0, max_val: float = 255) -> int:
        """
        Clamp a single value to a range.
        
        Args:
            value: Value to clamp
            min_val: Minimum value (default: 0)
            max_val: Maximum value (default: 255)
        
        Returns:
            Clamped integer value
        
        Example:
            r = ColorMath.clamp_value(300)  # Returns 255
            g = ColorMath.clamp_value(-50)  # Returns 0
        """
        return max(int(min_val), min(int(max_val), int(value)))
    
    @staticmethod
    def safe_rgb(r: float, g: float, b: float, default: RGB = (0, 0, 0)) -> RGB:
        """
        Safely convert values to RGB, with fallback on error.
        
        Args:
            r, g, b: RGB values (may be invalid types)
            default: Default RGB to return on error
        
        Returns:
            Valid RGB tuple or default on error
        
        Example:
            rgb = ColorMath.safe_rgb("invalid", 128, 200)
            # Returns: (0, 0, 0) - the default
        """
        try:
            return ColorMath.clamp_rgb(r, g, b)
        except (TypeError, ValueError, AttributeError):
            return default
    
    @staticmethod
    def is_valid_rgb(r: int, g: int, b: int) -> bool:
        """
        Check if RGB values are valid (in 0-255 range).
        
        Args:
            r, g, b: RGB values to check
        
        Returns:
            True if all values are in valid range
        
        Example:
            if ColorMath.is_valid_rgb(r, g, b):
                use_color(r, g, b)
            else:
                r, g, b = ColorMath.clamp_rgb(r, g, b)
        """
        try:
            return (
                0 <= int(r) <= 255 and
                0 <= int(g) <= 255 and
                0 <= int(b) <= 255
            )
        except (TypeError, ValueError):
            return False
__CMATH_EOF__
cat > api.py << '__API_EOF__'
"""
RNV Color MCP - API surface

The seven locked tools, shaped as plain functions. This is the seam: Phase 2 wraps each
of these with @mcp.tool and a description; nothing else about the engine changes.

Color engine : mix_colors, convert_color, generate_harmony
Text         : transform_text
Palette store: save_palette, list_palettes, get_palette
"""
from __future__ import annotations

import os
from typing import Any

from engine.color_math import ColorMath
from engine.color_harmony import generate_harmony as _harmony_by_name
from engine.text_transform import TextTransformer
from engine.palette_store import PaletteStore
from engine.resolve import resolve_color

# ---- mix mode -> ColorMath method ---------------------------------------
_MIX_MODES = {
    "rgb": ColorMath.weighted_rgb_mix,     # additive average (blend like light)
    "hsv": ColorMath.weighted_hsv_mix,     # circular-hue average
    "lab": ColorMath.lab_perceptual_mix,   # perceptually uniform (default)
    "paint": ColorMath.kubelka_munk_mix,   # pigment physics (blend like real paint)
    "ryb": ColorMath.weighted_ryb_mix,     # artist's color wheel
    "cmy": ColorMath.subtractive_cmy_mix,  # subtractive (like printer inks)
}

# A single shared store instance; path is configurable for deployment (persistent
# storage on the Space). Defaults to a local file for dev / Codespace.
_store = PaletteStore(os.environ.get("RNV_PALETTE_STORE", "palettes.json"))


# ---- color engine -------------------------------------------------------
def mix_colors(
    colors: list[str],
    weights: list[int] | None = None,
    mode: str = "lab",
) -> dict[str, Any]:
    """Blend up to 12 colors. weights default to equal; mode is one of
    rgb | hsv | lab | paint | ryb | cmy. Returns the mixed color."""
    if not colors:
        raise ValueError("Provide at least one color to mix.")
    if mode not in _MIX_MODES:
        raise ValueError(f"Unknown mode '{mode}'. Choose from {sorted(_MIX_MODES)}.")
    if weights is None:
        weights = [1] * len(colors)
    if len(weights) != len(colors):
        raise ValueError("weights must match the number of colors.")

    rgb_list = [ColorMath.hex_to_rgb(resolve_color(c, _store)) for c in colors]
    colors_weights = list(zip(rgb_list, weights))
    mixed = _MIX_MODES[mode](colors_weights)
    if mixed is None:
        raise ValueError("Mixing produced no result (check colors and weights).")
    return {"hex": ColorMath.rgb_to_hex(mixed), "rgb": list(mixed), "mode": mode}


def convert_color(color: str, to: str | None = None) -> dict[str, Any]:
    """Convert a hex color between formats. With `to`, returns just that format;
    otherwise returns all of hex/rgb/hsv/hsl/lab."""
    rgb = ColorMath.hex_to_rgb(resolve_color(color, _store))
    all_formats = {
        "hex": ColorMath.rgb_to_hex(rgb),
        "rgb": list(rgb),
        "hsv": list(ColorMath.rgb_to_hsv(rgb)),
        "hsl": list(ColorMath.rgb_to_hsl(rgb)),
        "lab": list(ColorMath.rgb_to_lab(rgb)),
    }
    if to:
        key = to.lower()
        if key not in all_formats:
            raise ValueError(f"Unknown format '{to}'. Choose from {sorted(all_formats)}.")
        return {key: all_formats[key]}
    return all_formats


def generate_harmony(base: str, scheme: str) -> list[str]:
    """Generate a color harmony from a base hex color. scheme is one of
    complementary | analogous | triadic | split-complementary |
    tetradic/square | monochromatic | compound."""
    rgb = ColorMath.hex_to_rgb(resolve_color(base, _store))
    result = _harmony_by_name(rgb, scheme)
    return [ColorMath.rgb_to_hex(c) for c in result]


def color_difference(color1: str, color2: str, method: str = "ciede2000") -> dict[str, Any]:
    """Perceptual difference (Delta-E) between two colors.
    method: "ciede2000" (default, modern standard) or "cie76". A value near 1.0 is the
    threshold a human eye can just notice; larger means more different."""
    rgb1 = ColorMath.hex_to_rgb(resolve_color(color1, _store))
    rgb2 = ColorMath.hex_to_rgb(resolve_color(color2, _store))
    de = ColorMath.delta_e(rgb1, rgb2, method=method)
    if de < 1:
        note = "not perceptible by human eyes"
    elif de < 2:
        note = "perceptible on close inspection"
    elif de < 10:
        note = "perceptible at a glance"
    elif de < 50:
        note = "clearly different"
    else:
        note = "near-opposite colors"
    return {
        "delta_e": round(de, 4),
        "method": method,
        "interpretation": note,
        "color1": ColorMath.rgb_to_hex(rgb1),
        "color2": ColorMath.rgb_to_hex(rgb2),
    }


def contrast_check(foreground: str, background: str) -> dict[str, Any]:
    """WCAG contrast ratio between a foreground and background color, with pass/fail
    for each accessibility level. Ratio runs 1.0 (none) to 21.0 (black on white)."""
    fg = ColorMath.hex_to_rgb(resolve_color(foreground, _store))
    bg = ColorMath.hex_to_rgb(resolve_color(background, _store))
    ratio = ColorMath.contrast_ratio(fg, bg)
    return {
        "ratio": round(ratio, 2),
        "display": f"{round(ratio, 2)}:1",
        "foreground": ColorMath.rgb_to_hex(fg),
        "background": ColorMath.rgb_to_hex(bg),
        "wcag": {
            "AA_normal_text": ratio >= 4.5,
            "AA_large_text": ratio >= 3.0,
            "AAA_normal_text": ratio >= 7.0,
            "AAA_large_text": ratio >= 4.5,
            "AA_ui_components": ratio >= 3.0,
        },
    }


# ---- text ---------------------------------------------------------------
def transform_text(text: str, operation: str) -> dict[str, str]:
    """Apply an exact text transformation (case conversions, etc.)."""
    return {"result": TextTransformer.transform_text(text, operation)}


# ---- palette store ------------------------------------------------------
def save_palette(name: str, colors: list[str], notes: str = "") -> dict[str, Any]:
    """Save (or update) a named palette for later reuse."""
    return _store.save_palette(name, colors, notes)


def list_palettes() -> list[dict[str, Any]]:
    """List every saved palette as {name, colors}."""
    return _store.list_palettes()


def get_palette(name: str) -> dict[str, Any] | None:
    """Retrieve one saved palette by name, or None if it doesn't exist."""
    return _store.get_palette(name)


__all__ = [
    "mix_colors", "convert_color", "generate_harmony", "transform_text",
    "save_palette", "list_palettes", "get_palette",
]
__API_EOF__
cat > server.py << '__SERVER_EOF__'
"""
RNV Color MCP - server

Thin FastMCP wrapper over api.py. The tools are registered with descriptions written
for the model: the description is what an LLM reads to decide whether and how to call a tool,
so each one is a capability statement, not a label.

Run locally / in a Codespace:
    pip install -r requirements.txt
    python server.py                      # Streamable HTTP on PORT (default 7860)

Transport is Streamable HTTP ("http"); connect by URL. Set RNV_PALETTE_STORE to a persistent
path (e.g. /data/palettes.json on a Space with persistent storage) so saved palettes survive
restarts.
"""
from __future__ import annotations

import os

from fastmcp import FastMCP

import api

mcp = FastMCP(
    name="rnv-color",
    instructions=(
        "Color workflow for RNVizion: mix colors (digital and physical/paint models), "
        "convert formats, generate harmonies, transform text case, and remember named "
        "palettes. Color inputs accept hex, CSS names, RNV brand names (brand gold, "
        "near-black), or saved-palette references."
    ),
)

# ---- color engine -------------------------------------------------------
mcp.tool(
    api.mix_colors,
    description=(
        "Blend up to 12 colors into one. Each color may be a hex (#d2bc93), a CSS name "
        "(red), an RNV brand name (brand gold, near-black), or a saved-palette reference "
        "(Spring line, or 'Spring line:2' for its 2nd swatch). Optional integer weights "
        "bias the blend (defaults to equal). mode selects the model: rgb/hsv/lab are "
        "digital blends (lab is perceptual and the default); paint mixes pigments via "
        "Kubelka-Munk physics (colors darken like real paint); ryb is the artist's color "
        "wheel; cmy is subtractive like printer inks. Returns hex and rgb."
    ),
)

mcp.tool(
    api.convert_color,
    description=(
        "Convert a color between formats. Input accepts a hex, CSS name, RNV brand name, "
        "or saved-palette reference. With `to` set to one of hex/rgb/hsv/hsl/lab, returns "
        "just that format; otherwise returns all of them."
    ),
)

mcp.tool(
    api.generate_harmony,
    description=(
        "Generate a color harmony from a base color. base accepts a hex, CSS name, RNV "
        "brand name, or saved-palette reference (e.g. 'Spring line:2'). scheme is one of: "
        "complementary, analogous, triadic, split-complementary, tetradic (a.k.a. square), "
        "monochromatic, compound. Returns a list of hex colors."
    ),
)

mcp.tool(
    api.color_difference,
    description=(
        "Perceptual difference (Delta-E) between two colors. color1 and color2 accept a hex, "
        "CSS name, RNV brand name, or saved-palette reference. method is 'ciede2000' (default, "
        "modern standard) or 'cie76'. A value near 1.0 is the threshold the eye can just notice; "
        "larger means more different. Returns the value and a plain-language interpretation."
    ),
)

mcp.tool(
    api.contrast_check,
    description=(
        "WCAG contrast ratio between a foreground and background color, for accessibility. "
        "Both accept a hex, CSS name, RNV brand name, or saved-palette reference. Returns the "
        "ratio (1.0-21.0) plus pass/fail for AA and AAA at normal and large text sizes and for "
        "UI components. Use this to check if text will be readable on a background."
    ),
)

# ---- text ---------------------------------------------------------------
mcp.tool(
    api.transform_text,
    description=(
        "Apply an exact, deterministic text transformation. operation is one of: "
        "UPPERCASE, lowercase, 'Title Case', 'Sentence case', camelCase, PascalCase, "
        "snake_case, CONSTANT_CASE, kebab-case, dot.case, 'iNVERTED cASE'. Use this rather "
        "than converting case by hand."
    ),
)

# ---- palette memory -----------------------------------------------------
mcp.tool(
    api.save_palette,
    description=(
        "Save (or update) a named palette for later reuse, e.g. a launch line. colors is a "
        "list of hex values; optional notes are stored as the palette's description. Author "
        "is recorded as RNVizion."
    ),
)

mcp.tool(
    api.list_palettes,
    description="List every saved palette as name + colors.",
)

mcp.tool(
    api.get_palette,
    description=(
        "Retrieve one saved palette by name, returning its colors and metadata. Returns "
        "null if no palette by that name exists."
    ),
)


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 7860)),
    )
__SERVER_EOF__
cat > tests/server_test.py << '__STEST_EOF__'
"""
Phase 2 test: connect an in-memory client to the FastMCP server and exercise the tools
end to end (registration -> schema -> call -> result), no network or deploy required.

Run from repo root:  python tests/server_test.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastmcp import Client
from server import mcp

EXPECTED_TOOLS = {
    "mix_colors", "convert_color", "generate_harmony",
    "color_difference", "contrast_check", "transform_text",
    "save_palette", "list_palettes", "get_palette",
}


def _text(result):
    """Pull the first text/content payload out of a CallToolResult."""
    if getattr(result, "data", None) is not None:
        return result.data
    if getattr(result, "structured_content", None):
        return result.structured_content
    return result.content


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        print(f"tools registered ({len(names)}): {sorted(names)}")
        assert names == EXPECTED_TOOLS, f"tool set mismatch: {names ^ EXPECTED_TOOLS}"

        # a name-based mix, all the way through the server
        r = await client.call_tool("mix_colors", {"colors": ["red", "blue"], "mode": "rgb"})
        print("mix_colors(red, blue, rgb) ->", _text(r))

        # paint mode through the server (should darken)
        r = await client.call_tool(
            "mix_colors", {"colors": ["brand gold", "near-black"], "mode": "paint"}
        )
        print("mix_colors(brand gold, near-black, paint) ->", _text(r))

        # harmony off a brand name
        r = await client.call_tool(
            "generate_harmony", {"base": "brand gold", "scheme": "complementary"}
        )
        print("generate_harmony(brand gold, complementary) ->", _text(r))

        # delta-e between two brand-ish colors
        r = await client.call_tool(
            "color_difference", {"color1": "brand gold", "color2": "dark gold"}
        )
        print("color_difference(brand gold, dark gold) ->", _text(r))

        # contrast check: gold text on near-black
        r = await client.call_tool(
            "contrast_check", {"foreground": "brand gold", "background": "near-black"}
        )
        print("contrast_check(brand gold on near-black) ->", _text(r))

        # text transform
        r = await client.call_tool(
            "transform_text", {"text": "the honest machine", "operation": "snake_case"}
        )
        print("transform_text(snake_case) ->", _text(r))

        # palette save -> get round-trip via the client
        await client.call_tool(
            "save_palette",
            {"name": "Spring line", "colors": ["#0a0a0f", "#d2bc93"], "notes": "launch"},
        )
        r = await client.call_tool("get_palette", {"name": "Spring line"})
        print("get_palette(Spring line) ->", _text(r))

    print("\nPhase 2 OK: client sees all 9 tools and gets correct results through FastMCP.")


if __name__ == "__main__":
    asyncio.run(main())
__STEST_EOF__
cat > tests/smoke_test.py << '__SMOKE_EOF__'
"""
Phase 1 smoke test: prove the extracted engine + store run standalone (no Qt, no GUI),
and that all seven tools and all six mix modes behave.

Run from repo root:  python tests/smoke_test.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api
from engine.palette_store import PaletteStore

BRAND_NEAR_BLACK = "#1a1a1a"  # canonical brand black (charcoal)
BRAND_GOLD = "#d2bc93"


def main() -> None:
    failures = []

    # 1. mix_colors across all six modes
    print("mix_colors — all six modes:")
    for mode in ["rgb", "hsv", "lab", "paint", "ryb", "cmy"]:
        out = api.mix_colors([BRAND_NEAR_BLACK, BRAND_GOLD], mode=mode)
        assert out["hex"].startswith("#") and len(out["hex"]) == 7, f"bad hex in {mode}"
        print(f"  {mode:5} -> {out['hex']}")

    # weighted mix (mostly gold)
    w = api.mix_colors([BRAND_NEAR_BLACK, BRAND_GOLD], weights=[1, 4], mode="lab")
    print(f"  weighted [1,4] lab -> {w['hex']}")

    # 2. convert_color (all formats + single format)
    conv = api.convert_color(BRAND_GOLD)
    assert set(conv) == {"hex", "rgb", "hsv", "hsl", "lab"}, "convert missing formats"
    one = api.convert_color(BRAND_GOLD, to="rgb")
    print(f"convert_color {BRAND_GOLD} -> rgb {one['rgb']}")

    # 3. generate_harmony across schemes
    print("generate_harmony:")
    for scheme in ["complementary", "analogous", "triadic",
                   "split-complementary", "tetradic", "monochromatic", "compound"]:
        colors = api.generate_harmony(BRAND_GOLD, scheme)
        assert isinstance(colors, list) and colors, f"empty harmony for {scheme}"
        print(f"  {scheme:20} -> {colors}")

    # 4. transform_text across the 11 operations
    print("transform_text:")
    for op in ["UPPERCASE", "lowercase", "Title Case", "Sentence case",
               "camelCase", "PascalCase", "snake_case", "CONSTANT_CASE",
               "kebab-case", "dot.case", "iNVERTED cASE"]:
        r = api.transform_text("the honest machine", op)["result"]
        print(f"  {op:15} -> {r}")

    # 5. palette store round-trip (isolated temp file)
    with tempfile.TemporaryDirectory() as d:
        store = PaletteStore(Path(d) / "palettes.json")
        api._store = store  # point the API at the temp store for this test
        api.save_palette("Spring line", [BRAND_NEAR_BLACK, BRAND_GOLD], notes="launch palette")
        listed = api.list_palettes()
        got = api.get_palette("Spring line")
        assert any(p["name"] == "Spring line" for p in listed), "palette not listed"
        assert got and got["colors"] == [BRAND_NEAR_BLACK, BRAND_GOLD], "round-trip mismatch"
        assert got["metadata"]["author"] == "RNVizion", "author default missing"
        assert got["metadata"]["description"] == "launch palette", "notes->description failed"
        print(f"palette round-trip -> {got['name']} {got['colors']} "
              f"(author={got['metadata']['author']})")

    # 6. the fashion composition: get_palette -> generate_harmony
    with tempfile.TemporaryDirectory() as d:
        api._store = PaletteStore(Path(d) / "palettes.json")
        api.save_palette("Spring line", [BRAND_GOLD])
        base = api.get_palette("Spring line")["colors"][0]
        accents = api.generate_harmony(base, "complementary")
        print(f"compose (get->harmony) -> base {base} accents {accents}")

    # 7. plain-language resolution: CSS names, RNV brand, palette refs, refusal
    print("name resolution:")
    rb = api.mix_colors(["red", "blue"], mode="rgb")
    print(f"  mix red + blue (rgb)        -> {rb['hex']}")
    bg = api.convert_color("brand gold", to="hex")
    assert bg["hex"] == BRAND_GOLD, "RNV 'brand gold' should be #d2bc93"
    print(f"  convert 'brand gold'        -> {bg['hex']}")
    d = api.color_difference("brand gold", "dark gold")
    assert d["delta_e"] > 0, "distinct colors should differ"
    print(f"  color_difference(gold, dark gold)  -> dE {d['delta_e']}")
    c = api.contrast_check("brand gold", "near-black")
    assert c["ratio"] > 1 and c["wcag"]["AA_normal_text"], "gold on near-black should pass AA"
    print(f"  contrast_check(gold/near-black)    -> {c['display']} AA={c['wcag']['AA_normal_text']}")
    nb = api.convert_color("near-black", to="hex")
    assert nb["hex"] == BRAND_NEAR_BLACK, "RNV 'near-black' should be #1a1a1a"
    print(f"  convert 'near-black'        -> {nb['hex']}")
    # RNV layer beats CSS: bare 'gold' is RNV gold, 'css:gold' forces universal
    assert api.convert_color("gold", to="hex")["hex"] == BRAND_GOLD, "'gold' should be RNV"
    assert api.convert_color("css:gold", to="hex")["hex"] == "#ffd700", "'css:gold' should be CSS"
    print(f"  'gold' (RNV) vs 'css:gold'  -> {api.convert_color('gold')['hex']} vs "
          f"{api.convert_color('css:gold')['hex']}")
    # harmony from a brand name and from a saved-palette reference
    with tempfile.TemporaryDirectory() as d:
        api._store = PaletteStore(Path(d) / "palettes.json")
        api.save_palette("Spring line", [BRAND_NEAR_BLACK, BRAND_GOLD, "#ffffff"])
        h_name = api.generate_harmony("brand gold", "complementary")
        h_ref = api.generate_harmony("Spring line:2", "complementary")  # 2nd swatch = gold
        print(f"  harmony 'brand gold'        -> {h_name}")
        print(f"  harmony 'Spring line:2'     -> {h_ref}")
        assert h_name == h_ref, "brand gold and Spring line's 2nd swatch should match"
    # refusal: an unknown token is refused, not guessed
    from engine.resolve import UnknownColor
    try:
        api.convert_color("definitely-not-a-color")
        failures.append("expected UnknownColor for unknown token")
    except UnknownColor:
        print("  unknown token              -> refused (UnknownColor), not guessed")

    if failures:
        print("\nFAILURES:", failures)
        sys.exit(1)
    print("\nAll checks passed. Engine + store run Qt-free.")


if __name__ == "__main__":
    main()
__SMOKE_EOF__

echo "2/5  server.json -> 1.1.0 (namespace casing preserved) ..."
cat > server.json << '__JSON_EOF__'
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json",
  "name": "io.github.RNVizion/rnv-color-mcp",
  "description": "A complete color workflow over MCP: mix, convert, harmonize, measure, and remember palettes.",
  "version": "1.1.0",
  "repository": {
    "url": "https://github.com/RNVizion/rnv-color-mcp",
    "source": "github"
  },
  "remotes": [
    { "type": "streamable-http", "url": "https://rnvizion-rnv-color-mcp.hf.space/mcp" }
  ]
}
__JSON_EOF__
python3 -c "import json; json.load(open('server.json')); print('   server.json valid')"

echo "3/5  README tool table (marker untouched) ..."
python3 << '__READMEPY__'
import pathlib
p = pathlib.Path("README.md"); t = p.read_text(encoding="utf-8")
if "`color_difference`" not in t:
    out = []
    for line in t.split("\n"):
        out.append(line)
        if line.startswith("| `generate_harmony` |"):
            out.append("| `color_difference` | Perceptual difference (Delta-E, CIEDE2000 or CIE76) between two colors. |")
            out.append("| `contrast_check` | WCAG contrast ratio plus AA/AAA pass/fail for accessible text. |")
    t = "\n".join(out)
t = t.replace("all 7 tools", "all 9 tools")
p.write_text(t, encoding="utf-8")
print("   README updated")
__READMEPY__

echo "4/5  Sanity-check the build imports ..."
python3 -c "import api, server; print('   imports OK')" 2>&1 | tail -3

echo "5/5  Commit + push ..."
git add -A
git commit -q -m "Add color_difference (Delta-E) and contrast_check (WCAG); v1.1.0" || echo "   (nothing to commit)"
git push origin HEAD:main || echo "   origin push failed - check manually."
if [ -n "$HF_TOKEN" ]; then
  SPACE=$(git remote get-url space | sed 's|https://[^@]*@|https://|')
  SUSER=$(echo "$SPACE" | cut -d/ -f5)
  git push "$(echo "$SPACE" | sed "s|https://|https://${SUSER}:${HF_TOKEN}@|")" HEAD:main --force
fi
echo ""
echo "Done. Space rebuilds with 9 tools. To register v1.1.0 in the MCP registry, run:"
echo "    unset GITHUB_TOKEN GH_TOKEN && mcp-publisher login github && mcp-publisher publish"
