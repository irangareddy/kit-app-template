"""Mutable view state for the Boreas Operator panel.

Single source of truth for what the operator is looking at: which
datacenter room, which surrogate, which CFD field, and which display
modes are toggled. Replaces the six scattered ``self._current_*`` ivars
that previously crept across the extension class.
"""

from dataclasses import dataclass


@dataclass
class ViewState:
    """What the operator is currently viewing.

    The extension owns one instance (``self.state``). UI controls,
    tools, and the viewport reader/writer all consult this same object,
    so state changes are explicit (assign to ``state.field``) rather
    than implicit (mutate ``self._current_field``).
    """

    sample: int = 0
    model: str = "fno_pred"           # one of "fno_pred", "unet_pred"
    field: str = "T"                   # one of "T", "U_magnitude", "p"
    comparison_mode: bool = True       # GT vs Prediction side-by-side
    show_error: bool = False           # overlay error map
    show_isosurface: bool = False      # render isosurface instead of cloud
