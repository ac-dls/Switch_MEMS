# MEMS Silicon Photonic Switch — Layout Design in gdsfactory + KLayout

A code-driven physical layout of a large-scale MEMS-actuated silicon photonic
switch: unit cell → 50×50 crossbar array → electrical addressing → chip-level
finishing → 3D visualization. Built end-to-end in Python (gdsfactory) with
KLayout as the mask viewer.

**Scope note:** this project is a **layout and tooling exercise**, not a
device performance study. The goal was to get fluent with process-aware
photonic/MEMS mask design — layer stacks, parametric cells, DRC-style
sanity checks, array assembly, and 3D visualization — using a real published
device as a realistic reference geometry, not to re-derive or validate its
optical/mechanical performance.

## Reference

Geometry, process flow, and key dimensions are based on:

> S. Han, *"Large-Scale Silicon Photonic MEMS Switch,"* M.S. thesis,
> UC Berkeley, EECS-2015-42 (advisor: Ming C. Wu).

It describes a 3-mask SOI process (shallow etch, deep etch, metal liftoff)
for a cantilever-actuated directional-coupler switch, tested at unit-cell
scale with manual probing — no on-chip electrical addressing or packaging
was implemented in the original work. Everything past the unit cell
(50×50 array, electrical addressing, chip finishing) is this project's own
extension.

## Two deliberate deviations from the reference, and why

| Deviation | Why |
|---|---|
| **`Col_Metal`** — a 4th mask layer, added beyond the thesis's 3-mask process | Passive-matrix addressing (below) needs row and column bus lines to cross at all 2,500 array intersections *without* shorting together. Putting both on the single metal layer the thesis uses would tie the entire row/column network into one node. A second, electrically isolated metal layer is the standard fix (same principle ICs and LCD/DMD backplanes use). |
| **Passive-matrix (crossbar) row/column addressing** — not in the thesis at all (it used a manual tungsten probe, one cell at a time) | Individually wiring 2,500 actuators isn't realistic pad-count-wise. Row/column addressing needs only 2N = 100 electrodes for a 50×50 array. This is grounded in real published follow-on work for this exact device family (*"Scalable Row/Column Addressing of Silicon Photonic MEMS Switches"*), not invented for this project. |

## Electrical addressing: drive scheme

Each actuator sits between one row line and one column line. Selection
exploits the electrostatic actuator's pull-in **hysteresis** — a half-select
scheme biases every line so only the intersection of the addressed row and
column reaches full pull-in voltage:

| Line | Bias |
|---|---|
| Selected row | +V<sub>π</sub>/2 |
| Selected column | −V<sub>π</sub>/2 |
| All other rows/columns | 0 V |

| Cell | Voltage seen | Result |
|---|---|---|
| Selected row **and** selected column | V<sub>π</sub> | Actuates (drop state) |
| Selected row **or** selected column (not both) | V<sub>π</sub>/2 | Stays at rest (through state) |
| Neither | 0 V | Stays at rest |

**Worked example**, using the thesis's own reported pull-in range (~14–24 V,
Sec. 3.C): at an operating point of V<sub>π</sub> = 20 V, the half-select
voltage is 10 V — a 4 V margin below the *lower bound* of the reported
range, so half-selected cells stay safely below actuation even accounting
for device-to-device variation.

## Optical I/O: grating coupler parameters

Grating period is derived from the first-order grating equation rather than
picked arbitrarily:

Λ = m·λ₀ / (n_eff − n_clad·sinθ)

| Parameter | Value | Basis |
|---|---|---|
| Wavelength λ₀ | 1550 nm | C-band, standard for Si photonics |
| Fiber tilt θ | 10° | Standard choice to avoid 2nd-order back-reflection |
| n_eff | 2.85 | Literature value, 220 nm SOI slab, TE, 1550 nm |
| n_clad | 1.44 | SiO₂ top clad |
| **Period Λ** | **600 nm** | Solved from the equation above |
| Duty cycle | 50% | Standard starting point |
| Etch depth | 70 nm | Reuses the same shallow-etch mask already in the process (Sec 3.A) |

Consistent with published shallow-etched grating couplers on this platform —
not re-derived from a mode simulation of this specific waveguide (n_eff
is a literature value, not solved for here). No apodization/reflection
optimization was done.

## File architecture

Built in this order; each file imports only from files above it.

| File | Purpose |
|---|---|
| `LayerMap_MS.py` | GDS layer/datatype definitions — 3 real process masks + `Col_Metal` (deliberate addition) + documentation-only layers |
| `LayerStack_ms.py` | Per-layer thickness/z-position (real thesis values) for 3D extrusion; splits released vs. anchored silicon via boolean layer algebra |
| `PDK_MS.py` | Activates a gdsfactory `Pdk` combining the layer map + stack, based on the generic PDK for routing primitives |
| `LeafComponents_MS.py` | Independently-testable parametric cells: crossing, coupler, cantilever, metal pad, anchor, width taper |
| `UnitCell_MS.py` | Assembles the leaf cells into one 160×160 µm switch cell (two couplers, per the reference figure) |
| `ChipArray_MS.py` | Tiles 2,500 unit cells into a 50×50 crossbar on a 9×9 mm die; analytical (not order-dependent) port-position lookup |
| `ElectricalAddressing_MS.py` | Row/column bus traces implementing the addressing scheme above |
| `ChipFinishing_MS.py` | Grating-coupler edge I/O, wire-bond pads, alignment marks, dicing-street keep-out |
| `Render3D_MS.py` | 3D visualization via gdsfactory's native `to_3d()`, consuming `LayerStack_ms.py` directly |

## Running it

```bash
python UnitCell_MS.py        # single switch cell
python ChipArray_MS.py       # full 50x50 array
python ChipFinishing_MS.py   # complete chip
python Render3D_MS.py        # 3D render (needs pyglet<2; see script header)
```

Each script writes GDS to an `output/` folder next to it. For live viewing in
KLayout: install the **klive** package (KLayout → Tools → Manage Packages →
search "klive"), keep KLayout open, and each script will auto-display its
result there.

## Known simplifications

- Dimensions are placeholders sized to fit, not DRC-derived from a real
  foundry rule deck.
- Waveguides are simple full-etch strips — the shallow-etch (rib/slab) mask
  exists in the layer map but isn't used in any waveguide geometry.
- No insulator/via mask is modeled between the two metal layers — they're
  drawn as directly overlapping where a contact is intended.
- The addressing scheme above is a design description, not simulated drive
  electronics.
- 3D renders use a visualization-only z-exaggeration (the real actuation
  deflection is 1 µm — invisible at this device's lateral scale); the
  underlying `LayerStack_ms.py` itself is never altered.
