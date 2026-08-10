# Here I'm defining the different processes that make the system as Leaf Components 

import gdsfactory as gf 
import PDK_MS
from LayerMap_MS import LAYER
 
PDK_MS.activate()
 
 
# ---- Waveguide crossing ----

@gf.cell
def waveguide_crossing(
    width: float = 0.35,
    arm_length: float = 3.0,
) -> gf.Component:
 
    c = gf.Component()
 
    half_w = width / 2
    # Horizontal bar (W-E arm)
    c.add_polygon(
        [
            (-arm_length, -half_w),
            (arm_length, -half_w),
            (arm_length, half_w),
            (-arm_length, half_w),
        ],
        layer=LAYER.Deep_Etch,
    )
    # Vertical bar (N-S arm)
    c.add_polygon(
        [
            (-half_w, -arm_length),
            (half_w, -arm_length),
            (half_w, arm_length),
            (-half_w, arm_length),
        ],
        layer=LAYER.Deep_Etch,
    )
 
    c.add_port(name="o1", center=(-arm_length, 0), width=width, orientation=180,
               layer=LAYER.Deep_Etch, port_type="optical")  # West
    c.add_port(name="o2", center=(arm_length, 0), width=width, orientation=0,
               layer=LAYER.Deep_Etch, port_type="optical")  # East
    c.add_port(name="o3", center=(0, arm_length), width=width, orientation=90,
               layer=LAYER.Deep_Etch, port_type="optical")  # North
    c.add_port(name="o4", center=(0, -arm_length), width=width, orientation=270,
               layer=LAYER.Deep_Etch, port_type="optical")  # South
    return c
 
 

# --- Movable directional coupler (this part has two parallel waveguides) ----

@gf.cell
def movable_directional_coupler(
    width: float = 0.35,
    gap: float = 0.25,
    length: float = 11.9,
) -> gf.Component:
    
    c = gf.Component()
    pitch = width + gap
 
    # Bus 1 (bottom waveguide)
    c.add_polygon(
        [(0, 0), (length, 0), (length, width), (0, width)],
        layer=LAYER.Deep_Etch,
    )
    # Bus 2 (top waveguide, offset by pitch)
    c.add_polygon(
        [
            (0, pitch),
            (length, pitch),
            (length, pitch + width),
            (0, pitch + width),
        ],
        layer=LAYER.Deep_Etch,
    )
 
    c.add_port(name="o1", center=(0, width / 2), width=width, orientation=180,
               layer=LAYER.Deep_Etch, port_type="optical")
    c.add_port(name="o2", center=(length, width / 2), width=width, orientation=0,
               layer=LAYER.Deep_Etch, port_type="optical")
    c.add_port(name="o3", center=(0, pitch + width / 2), width=width, orientation=180,
               layer=LAYER.Deep_Etch, port_type="optical")
    c.add_port(name="o4", center=(length, pitch + width / 2), width=width, orientation=0,
               layer=LAYER.Deep_Etch, port_type="optical")
    return c
 
 

# ---- MEMS cantilever (released beam + etch holes) ----

@gf.cell
def etch_hole_unit(size: float = 2.0) -> gf.Component:
    """Single etch-hole square (Etch_hole layer). Tiled by mems_cantilever."""
    c = gf.Component()
    c.add_polygon(
        [(0, 0), (size, 0), (size, size), (0, size)],
        layer=LAYER.Etch_hole,
    )
    return c
 
 
@gf.cell
def mems_cantilever(
    length: float = 40.0,
    width: float = 10.0,
    etch_hole_size: float = 2.0,
    etch_hole_pitch: float = 5.0,
    etch_hole_margin: float = 1.5,
) -> gf.Component:
  
    c = gf.Component()
 
    c.add_polygon(
        [(0, 0), (length, 0), (length, width), (0, width)],
        layer=LAYER.Deep_Etch,
    )
 
    # Etch-hole array goes here (inset from the edges by etch_hole_margin)
    usable_length = length - 2 * etch_hole_margin
    usable_width = width - 2 * etch_hole_margin
    n_cols = max(int(usable_length // etch_hole_pitch), 1)
    n_rows = max(int(usable_width // etch_hole_pitch), 1)
 
    hole = etch_hole_unit(size=etch_hole_size)
    ref = c.add_ref(
        hole,
        columns=n_cols,
        rows=n_rows,
        column_pitch=etch_hole_pitch,
        row_pitch=etch_hole_pitch,
    )
    ref.move((etch_hole_margin, etch_hole_margin))
 
    # Base port: connects to the anchor_structure's tip port.
    c.add_port(name="o1", center=(0, width / 2), width=width, orientation=180,
               layer=LAYER.Deep_Etch, port_type="optical")

    # Tip port A: connects to the first movable_directional_coupler
    c.add_port(name="o2", center=(length, width / 2), width=width, orientation=0,
               layer=LAYER.Deep_Etch, port_type="optical")

    # Tip port B: connects to a second movable_directional_coupler,
    # This one is offset in y from o2 so the two coupling interfaces sit side by
    c.add_port(name="o3", center=(length, width * 0.25), width=width * 0.25,
               orientation=0, layer=LAYER.Deep_Etch, port_type="optical")
    return c
 

# ---- Width taper ----

@gf.cell
def width_taper(
    width1: float = 0.35,
    width2: float = 10.0,
    length: float = 5.0,
) -> gf.Component:
  
    c = gf.Component()
    c.add_polygon(
        [
            (0, -width1 / 2),
            (0, width1 / 2),
            (length, width2 / 2),
            (length, -width2 / 2),
        ],
        layer=LAYER.Deep_Etch,
    )
    c.add_port(name="o1", center=(0, 0), width=width1, orientation=180,
               layer=LAYER.Deep_Etch, port_type="optical")
    c.add_port(name="o2", center=(length, 0), width=width2, orientation=0,
               layer=LAYER.Deep_Etch, port_type="optical")
    return c
 

# ---- Metal actuator pad ----

@gf.cell
def metal_actuator_pad(
    width: float = 20.0,
    length: float = 20.0,
    col_tap_size: float = 4.0,
) -> gf.Component:
 
    c = gf.Component()
    c.add_polygon(
        [(0, 0), (length, 0), (length, width), (0, width)],
        layer=LAYER.Metal_Pad,
    )
    c.add_port(name="e_row", center=(0, width / 2), width=width, orientation=180,
               layer=LAYER.Metal_Pad, port_type="electrical")
 

    # Col_Metal via-landing patch, centered on the pad 
    tap_cx, tap_cy = length / 2, width / 2
    half = col_tap_size / 2
    c.add_polygon(
        [
            (tap_cx - half, tap_cy - half),
            (tap_cx + half, tap_cy - half),
            (tap_cx + half, tap_cy + half),
            (tap_cx - half, tap_cy + half),
        ],
        layer=LAYER.Col_Metal,
    )
    c.add_port(name="e_col", center=(tap_cx, tap_cy + half), width=col_tap_size,
               orientation=90, layer=LAYER.Col_Metal, port_type="electrical")
    return c
 
 

# ---- Anchor structure ----

@gf.cell
def anchor_structure(
    width: float = 10.0,
    length: float = 15.0,
) -> gf.Component:
  
    c = gf.Component()
    footprint = [(0, 0), (length, 0), (length, width), (0, width)]
    c.add_polygon(footprint, layer=LAYER.Deep_Etch)
    c.add_polygon(footprint, layer=LAYER.Anchor)
 
    # Substrate-side reference so that I have a "documentation" anchor point
    c.add_port(name="anchor_ref", center=(0, width / 2), width=width,
               orientation=180, layer=LAYER.Anchor, port_type="electrical")

    # Connects to mems_cantilever's base port.
    c.add_port(name="o1", center=(length, width / 2), width=width,
               orientation=0, layer=LAYER.Deep_Etch, port_type="optical")
    return c

# ---- Output generation section now ----
 
if __name__ == "__main__":
    import os
    import socket
 
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
 
    cells = {
        "waveguide_crossing": waveguide_crossing(),
        "movable_directional_coupler": movable_directional_coupler(),
        "mems_cantilever": mems_cantilever(),
        "width_taper": width_taper(),
        "metal_actuator_pad": metal_actuator_pad(),
        "anchor_structure": anchor_structure(),
    }
    last_comp = None
    for name, comp in cells.items():
        gds_path = os.path.join(out_dir, f"{name}.gds")
        comp.write_gds(gds_path)
        print(f"{name:28s} bbox={comp.bbox()}  ports={[p.name for p in comp.ports]}")
        print(f"  -> {gds_path}")
        last_comp = comp
 
    KLIVE_PORT = 8082
    try:
        with socket.create_connection(("localhost", KLIVE_PORT), timeout=0.5):
            klive_reachable = True
    except OSError:
        klive_reachable = False
 
    if klive_reachable:
        last_comp.show()
        print(f"Sent '{list(cells.keys())[-1]}' to KLayout via klive.")
    else:
        print(
            f"\nklive not reachable on localhost:{KLIVE_PORT} - nothing, dude "
        )

print("Done, dude!")
