"""Visual design tokens for the Boreas Operator panel.

All colors, font sizes, and spacing live here so the panel stays
brand-consistent and easy to retheme. Type scale is a 5-step ladder
to avoid the 7-size sprawl that crept into the original monolith.
"""


class Color:
    """NVIDIA Omniverse palette + status semantics."""

    # Brand
    GREEN_PRIMARY = 0xFF00B140   # primary CTA + "winning" verdicts
    GREEN_ACCENT  = 0xFF76B900   # header bar + secondary CTA
    GREEN_BANNER  = 0xFF1E3320   # winner-banner background
    GREEN_ROW_HL  = 0xFF2F3A2F   # subtle row highlight in tables

    # Surface
    DARK_BG    = 0xFF1F1F28      # window background
    CARD_BG    = 0xFF2A2A32      # elevated card background
    NOTE_BG    = 0xFF242430      # muted footer / context-note background
    SECONDARY  = 0xFF3F3F48      # secondary button fill

    # Text
    WHITE = 0xFFEEEEEE           # primary text
    GRAY  = 0xFFA0A0A8           # secondary text

    # Status (R^2 quality bands)
    GREEN  = 0xFF00B140           # R^2 >= 0.9 (alias of GREEN_PRIMARY for status)
    YELLOW = 0xFFFFC107           # R^2 in [0.5, 0.9)
    RED    = 0xFFEF5350           # R^2 < 0.5 (was 0xFFE53935; bumped for WCAG ~5.4:1)

    # Accent reserved for the "current view" info strip (do not reuse).
    CYAN = 0xFF4FC3F7


class Font:
    """5-step type scale (down from the original 7)."""
    CAPTION = 11
    LABEL   = 12
    BODY    = 13
    SECTION = 15
    TITLE   = 20


class Spacing:
    """5-step spacing ladder for VStack / HStack / Spacer."""
    XS = 2
    SM = 4
    MD = 6
    LG = 10
    XL = 16


# ----------------------------------------------------------------- helpers


def r2_color(r2):
    """Map an R^2 value to a status color."""
    if r2 >= 0.9: return Color.GREEN
    if r2 >= 0.5: return Color.YELLOW
    return Color.RED


def r2_label(r2):
    """Map an R^2 value to a human-readable quality band."""
    if r2 >= 0.95: return "Excellent"
    if r2 >= 0.9:  return "Good"
    if r2 >= 0.7:  return "Fair"
    if r2 >= 0.0:  return "Poor"
    return "Negative"


def winner_arrow(fno_val, unet_val, lower_is_better=True):
    """Return 'FNO' / 'U-Net' / 'Tie' / '?' for a head-to-head metric."""
    try:
        fno_val = float(fno_val)
        unet_val = float(unet_val)
    except (TypeError, ValueError):
        return "?"
    if lower_is_better:
        if fno_val < unet_val:  return "FNO"
        if unet_val < fno_val:  return "U-Net"
    else:
        if fno_val > unet_val:  return "FNO"
        if unet_val > fno_val:  return "U-Net"
    return "Tie"
