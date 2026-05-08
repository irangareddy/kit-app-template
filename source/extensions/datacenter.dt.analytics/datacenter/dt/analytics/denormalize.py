"""Single source of truth for denormalizing the PhysicsNeMo-Datacenter-CFD
target arrays back to physical units.

The dataset stores each sample as a (5, D, H, W) numpy array of z-score
normalized fields. To get usable physical-unit values for operator-grade
display the agent needs the original mean/std per field (taken from the
dataset's denormalization metadata).

Use ``denormalize_field(target, field)`` instead of inlining these
constants anywhere else.
"""

import numpy as np

# Per-field denormalization (value = z * SCALE + OFFSET).
# Source: PhysicsNeMo-Datacenter-CFD dataset card.
T_SCALE, T_OFFSET = 4.0,    39.0     # Temperature -> degrees Celsius
U_SCALE, U_OFFSET = 1.3656, 1.5984   # Velocity component -> meters per second
P_SCALE, P_OFFSET = 4.1660, 6.1227   # Pressure -> Pascals

# Channel layout in the (5, D, H, W) target array.
# Index 0..2 -> Ux, Uy, Uz (z-scored). Index 3 -> T (z-scored). Index 4 -> p (z-scored).
_CHANNEL_T = 3
_CHANNEL_P = 4
_CHANNEL_U_SLICE = slice(0, 3)


def denormalize_field(target, field):
    """Denormalize one field of a target array to physical units.

    Parameters
    ----------
    target : np.ndarray
        Shape (5, D, H, W). Z-score normalized CFD fields.
    field : str
        One of "T", "U_magnitude", "p".

    Returns
    -------
    (array, unit) : (np.ndarray, str)
        ``array`` has shape (D, H, W). ``unit`` is the physical unit string.
    """
    if field == "T":
        return target[_CHANNEL_T] * T_SCALE + T_OFFSET, "°C"
    if field == "U_magnitude":
        u = target[_CHANNEL_U_SLICE] * U_SCALE + U_OFFSET
        return np.sqrt(np.sum(u * u, axis=0)), "m/s"
    if field == "p":
        return target[_CHANNEL_P] * P_SCALE + P_OFFSET, "Pa"
    raise ValueError(f"unknown field {field!r}; expected one of 'T', 'U_magnitude', 'p'")
