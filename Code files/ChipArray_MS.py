# Here I create the chip array structure (again, pulling from files down the hierarchy)

import gdsfactory as gf 
import PDK_MS
from LayerMap_MS import LAYER
from UnitCell_MS import switch_unit_cell, UNIT_CELL_SIZE
import random
 
PDK_MS.activate()
 
ARRAY_ROWS = 50
ARRAY_COLS = 50
DIE_SIZE = 9000.0  # 9x9 mm^2 chip area per spec
 
_OPTICAL_PORT_NAMES = ("bus_W", "bus_E", "bus_N", "bus_S")
_ELECTRICAL_PORT_NAMES = ("e_row", "e_col")
_ALL_PORT_NAMES = _OPTICAL_PORT_NAMES + _ELECTRICAL_PORT_NAMES
 
# --- Chip Array constituents ----
 
@gf.cell
def padded_unit_cell(cell_size: float = UNIT_CELL_SIZE, **kwargs) -> gf.Component:
    
    inner = switch_unit_cell(cell_size=cell_size, **kwargs)
    c = gf.Component()
    ref = c << inner
 
    for name in _OPTICAL_PORT_NAMES:
        port = ref.ports[name]
        x, y = port.dcenter
        orientation = port.orientation
        width = port.dwidth
 
        if orientation == 180.0:
            length = x
        elif orientation == 0.0:
            length = cell_size - x
        elif orientation == 90.0:
            length = cell_size - y
        elif orientation == 270.0:
            length = y
        else:
            raise ValueError(f"Unexpected orientation {orientation} for port {name}")
 
        xs = gf.cross_section.cross_section(width=width, layer=LAYER.Deep_Etch)
        stub_ref = c << gf.components.straight(length=length, cross_section=xs)
        stub_ref.connect("o1", port)
        c.add_port(name=name, port=stub_ref.ports["o2"])
 
    for name in _ELECTRICAL_PORT_NAMES:
        c.add_port(name=name, port=ref.ports[name])
 
    return c
 
# --- Port allocation from one local reading (using one port as reference) ---
 
def _get_local_port_table() -> dict[str, dict]:
    
    ref_cell = padded_unit_cell()
    table = {}
    for p in ref_cell.ports:
        x, y = p.dcenter
        table[p.name] = {
            "x": x,
            "y": y,
            "orientation": p.orientation,
            "width": p.dwidth,
            "layer": p.layer,
            "port_type": p.port_type,
        }
    return table
 
 
def _analytical_port_position(
    row: int, col: int, port_name: str, margin_x: float, margin_y: float,
    local_table: dict[str, dict],
) -> dict:
    """Compute cell (row, col)'s absolute port position purely from
    the cell's known LOCAL offset plus its row/col tiling offset --
    no dependency on any array-instance .ports enumeration order.
    """
    local = local_table[port_name]
    return {
        "x": margin_x + col * UNIT_CELL_SIZE + local["x"],
        "y": margin_y + row * UNIT_CELL_SIZE + local["y"],
        "orientation": local["orientation"],
        "width": local["width"],
        "layer": local["layer"],
        "port_type": local["port_type"],
    }
 
 
def _cross_validate_analytical_positions(
    array_ref, local_table: dict[str, dict], margin_x: float, margin_y: float,
    rows: int, cols: int, n_samples: int = 25,
) -> None:
    """Check the analytical formula against the real tiled geometry,
    order-independently.
    """
    real_positions = {
        (round(p.dcenter[0], 3), round(p.dcenter[1], 3)) for p in array_ref.ports
    }
 
    import random
 
    rng = random.Random(0)
    for _ in range(n_samples):
        r = rng.randint(0, rows - 1)
        cc = rng.randint(0, cols - 1)
        name = rng.choice(_ALL_PORT_NAMES)
        computed = _analytical_port_position(r, cc, name, margin_x, margin_y, local_table)
        key = (round(computed["x"], 3), round(computed["y"], 3))
        if key not in real_positions:
            raise RuntimeError(
                f"Analytical position for cell ({r},{cc}) port '{name}' "
                f"{key} was not found among the real tiled array's actual "
                "port positions - analytical formula does not match "
            )
 

# ---- Full crossbar array ---
 
@gf.cell
def switch_array(
    rows: int = ARRAY_ROWS,
    cols: int = ARRAY_COLS,
    die_size: float = DIE_SIZE,
) -> gf.Component:
  
    array_width = cols * UNIT_CELL_SIZE
    array_height = rows * UNIT_CELL_SIZE
    if array_width > die_size or array_height > die_size:
        raise ValueError(
            f"{cols}x{rows} array ({array_width}x{array_height} um) "
            f"does not fit inside the {die_size}x{die_size} um die."
        )
 
    c = gf.Component()
    cell = padded_unit_cell()
 
    # Center the array within the die, leaving margin for I/O, bond
    margin_x = (die_size - array_width) / 2
    margin_y = (die_size - array_height) / 2
 
    array_ref = c.add_ref(
        cell,
        columns=cols,
        rows=rows,
        column_pitch=UNIT_CELL_SIZE,
        row_pitch=UNIT_CELL_SIZE,
    )
    array_ref.dmove((margin_x, margin_y))
 
    local_table = _get_local_port_table()
 
    # Cross-validate the analytical formula against the real tiled geometry
    _cross_validate_analytical_positions(
        array_ref, local_table, margin_x, margin_y, rows, cols
    )
 
    def ports_of(row: int, col: int) -> dict[str, dict]:
        return {
            name: _analytical_port_position(row, col, name, margin_x, margin_y, local_table)
            for name in _ALL_PORT_NAMES
        }
 
    # Spot-check internal tiling on a few random joins rather
 
    rng = random.Random(0)
    for _ in range(20):
        r = rng.randint(0, rows - 2)
        cc = rng.randint(0, cols - 2)
        east = ports_of(r, cc)["bus_E"]
        west_neighbor = ports_of(r, cc + 1)["bus_W"]
        if (round(east["x"], 3), round(east["y"], 3)) != (round(west_neighbor["x"], 3), round(west_neighbor["y"], 3)):
            raise RuntimeError(
                f"Cell ({r},{cc}) bus_E does not match with cell "
                f"({r},{cc+1}) bus_W - tiling assumption broken."
            )
        north = ports_of(r, cc)["bus_N"]
        south_neighbor = ports_of(r + 1, cc)["bus_S"]
        if (round(north["x"], 3), round(north["y"], 3)) != (round(south_neighbor["x"], 3), round(south_neighbor["y"], 3)):
            raise RuntimeError(
                f"Cell ({r},{cc}) bus_N does not match with cell "
                f"({r+1},{cc}) bus_S - tiling assumption broken."
            )
 
    def _expose(name: str, info: dict) -> None:
        c.add_port(
            name=name,
            center=(info["x"], info["y"]),
            orientation=info["orientation"],
            width=info["width"],
            layer=info["layer"],
            port_type=info["port_type"],
        )
 
    # Expose perimeter (chip-edge) optical ports for the next stage
    for col in range(cols):
        _expose(f"bus_S_{col}", ports_of(0, col)["bus_S"])
        _expose(f"bus_N_{col}", ports_of(rows - 1, col)["bus_N"])
    for row in range(rows):
        _expose(f"bus_W_{row}", ports_of(row, 0)["bus_W"])
        _expose(f"bus_E_{row}", ports_of(row, cols - 1)["bus_E"])
 
    # Expose every cell's e_row/e_col for electrical_addressing 
    for row in range(rows):
        for col in range(cols):
            p = ports_of(row, col)
            _expose(f"e_row_{row}_{col}", p["e_row"])
            _expose(f"e_col_{row}_{col}", p["e_col"])
 
    # Die floorplan outline 
    c.add_polygon(
        [(0, 0), (die_size, 0), (die_size, die_size), (0, die_size)],
        layer=LAYER.Floor_Plan,
    )
 
    return c
 

# ---- Output generation section now ----

if __name__ == "__main__":
    import time
 
    t0 = time.time()
    c = switch_array()
    elapsed = time.time() - t0
    all_port_names = [p.name for p in c.ports]
    n_perimeter_optical = len([n for n in all_port_names if n.startswith(("bus_W_", "bus_E_", "bus_N_", "bus_S_"))])
    n_electrical = len([n for n in all_port_names if n.startswith(("e_row_", "e_col_"))])
    print(f"built in {elapsed:.2f}s")
    print(f"bbox={c.bbox()}")
    print(f"array footprint: {ARRAY_COLS * UNIT_CELL_SIZE} x {ARRAY_ROWS * UNIT_CELL_SIZE} um")
    print(f"die footprint: {DIE_SIZE} x {DIE_SIZE} um")
    print(f"total ports exposed: {len(all_port_names)}")
    print(f"perimeter optical bus ports: {n_perimeter_optical} (expected {2*ARRAY_ROWS + 2*ARRAY_COLS})")
    print(f"per-cell electrical taps: {n_electrical} (expected {2*ARRAY_ROWS*ARRAY_COLS})")
 
    import os
    import socket
 
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    gds_path = os.path.join(out_dir, "switch_array.gds")
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
print("Done dude!")