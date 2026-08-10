# Construction of the Unit cell pulling directly from what I built in LayerMap and LeafComponents

import gdsfactory as gf 
import PDK_MS
from LayerMap_MS import LAYER
from LeafComponents_MS import (
    anchor_structure,
    mems_cantilever,
    metal_actuator_pad,
    movable_directional_coupler,
    waveguide_crossing,
    width_taper,
)
 
PDK_MS.activate()
 
UNIT_CELL_SIZE = 160.0  # 160x160 um^2 unit cell
 
# ---- Cross-section used only for the coupler_B -> cantilever routing bend (space was tight) ---- 
_ROUTE_XS = gf.cross_section.cross_section(
    width=0.35, layer=LAYER.Deep_Etch, radius=2.0, radius_min=1.0
)
 
# ---- Taper lengths ----
TAPER_A_LENGTH = 5.0  # um
TAPER_B_LENGTH = 3.0  # um

# ---- Unit Cell (one 160x160 um^2 MEMS switch unit cell with two couplers)----
 
@gf.cell
def switch_unit_cell(
    cell_size: float = UNIT_CELL_SIZE,
    crossing_arm_length: float = 10.0,
    coupler_length: float = 11.9,
    coupler_width: float = 0.35,
    coupler_gap: float = 0.25,
    cantilever_length: float = 40.0,
    cantilever_width: float = 10.0,
    anchor_length: float = 15.0,
    anchor_width: float = 10.0,
) -> gf.Component:
   
    c = gf.Component()
 
    # Fixed reference point: waveguide crossing at cell center 
    crossing_ref = c << waveguide_crossing(arm_length=crossing_arm_length)
    crossing_ref.dcenter = (cell_size / 2, cell_size / 2)
 
    #  Coupler A: west arm through-path, coupled line -> taper -> cantilever 
    coupler_a_ref = c << movable_directional_coupler(
        width=coupler_width, gap=coupler_gap, length=coupler_length
    )
    coupler_a_ref.connect("o2", crossing_ref.ports["o1"])  # bus line -> crossing west
 
    taper_a_ref = c << width_taper(
        width1=coupler_width, width2=cantilever_width, length=TAPER_A_LENGTH
    )
    taper_a_ref.connect("o1", coupler_a_ref.ports["o4"])  # coupled line (o4), width-matched
 
    cantilever_ref = c << mems_cantilever(
        length=cantilever_length, width=cantilever_width
    )
    cantilever_ref.connect("o2", taper_a_ref.ports["o2"])  # width-matched, no mismatch flag needed
 
    anchor_ref = c << anchor_structure(width=anchor_width, length=anchor_length)
    anchor_ref.connect("o1", cantilever_ref.ports["o1"])
 
    # --- Stack the metal pad onto the anchor footprint ----
    pad_ref = c << metal_actuator_pad(width=anchor_width, length=anchor_length)
    pad_ref.dxmin = anchor_ref.dxmin
    pad_ref.dymin = anchor_ref.dymin
 
    # --- Coupler B: south arm through-path, coupled line -> route ->  taper -> cantilever ----
    coupler_b_ref = c << movable_directional_coupler(
        width=coupler_width, gap=coupler_gap, length=coupler_length
    )
    coupler_b_ref.connect("o2", crossing_ref.ports["o4"])  # bus line - crossing south
 
    # ---- Taper_b is connected to cantilever.o3 first ----

    taper_b_ref = c << width_taper(
        width1=coupler_width, width2=cantilever_width * 0.25, length=TAPER_B_LENGTH
    )
    taper_b_ref.connect("o2", cantilever_ref.ports["o3"])
 
    gf.routing.route_single(
        c,
        coupler_b_ref.ports["o4"],
        taper_b_ref.ports["o1"],
        cross_section=_ROUTE_XS,
        auto_taper=False,  
    )
 
    # Check to see if everything fits inside 160um

    bbox = c.bbox()
    if bbox.left < 0 or bbox.bottom < 0 or bbox.right > cell_size or bbox.top > cell_size:
        raise ValueError(
            f"Unit cell contents {bbox} exceed the {cell_size}x{cell_size} "
            "um keep-out boundary - shrink a parameter or reposition."
        )
 
    # ---- Pitch-boundary reference frame ---
    c.add_polygon(
        [(0, 0), (cell_size, 0), (cell_size, cell_size), (0, cell_size)],
        layer=LAYER.Unit_Cell,
    )
 
    # --- Wafer blanket footprint ---
    c.add_polygon(
        [(0, 0), (cell_size, 0), (cell_size, cell_size), (0, cell_size)],
        layer=LAYER.Wafer,
    )
 
    # ---- Expose outward bus ports for the array stage ----
    c.add_port(name="bus_W", port=coupler_a_ref.ports["o1"])
    c.add_port(name="bus_E", port=crossing_ref.ports["o2"])
    c.add_port(name="bus_N", port=crossing_ref.ports["o3"])
    c.add_port(name="bus_S", port=coupler_b_ref.ports["o1"])

    # Electrical (row/column addressing) ports.
    c.add_port(name="e_row", port=pad_ref.ports["e_row"])
    c.add_port(name="e_col", port=pad_ref.ports["e_col"])
 
    return c
 

# ---- Output generation section now ----

if __name__ == "__main__":
    import os
    import socket
 
    c = switch_unit_cell()
    print(f"bbox={c.bbox()}  ports={[p.name for p in c.ports]}")
 
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    gds_path = os.path.join(out_dir, "switch_unit_cell.gds")
    c.write_gds(gds_path)
    print(f"GDS written to: {gds_path}")
 
    KLIVE_PORT = 8082
    try:
        with socket.create_connection(("localhost", KLIVE_PORT), timeout=0.5):
            klive_reachable = True
    except OSError:
        klive_reachable = False
 
    if klive_reachable:
        c.show()
        print("Sent to KLayout via klive.")
    else:
        print(
            f"klive not reachable on localhost:{KLIVE_PORT} - nothing, dude "
        )

print("Done, dude!")