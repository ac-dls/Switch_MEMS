# Here the electrical adressing of the chip is settled 

import gdsfactory as gf
import kfactory as kf
import PDK_MS
from LayerMap_MS import LAYER
from ChipArray_MS import (
    switch_array,
    ARRAY_ROWS,
    ARRAY_COLS,
    UNIT_CELL_SIZE,
    DIE_SIZE,
    _get_local_port_table,
)
 
PDK_MS.activate()
 
# ---- Trace widths (placeholders for now, each was kept smaller than its target tap) ----

ROW_TRACE_WIDTH = 8.0  # um, on Metal_Pad
COL_TRACE_WIDTH = 3.0  # um, on Col_Metal

 # ---- Addressing rows and columns to trace footprint ----
 
@gf.cell
def addressed_array(
    rows: int = ARRAY_ROWS,
    cols: int = ARRAY_COLS,
    die_size: float = DIE_SIZE,
) -> gf.Component:
    
    c = gf.Component()
    array_ref = c << switch_array(rows=rows, cols=cols, die_size=die_size)
 
    array_width = cols * UNIT_CELL_SIZE
    array_height = rows * UNIT_CELL_SIZE
    margin_x = (die_size - array_width) / 2
    margin_y = (die_size - array_height) / 2
 
    local_table = _get_local_port_table()
    e_row_local = local_table["e_row"]
    e_col_local = local_table["e_col"]
 
    # Row bus lines (Metal_Pad): one per row
    for r in range(rows):
        row_y = margin_y + r * UNIT_CELL_SIZE + e_row_local["y"]
        x0, x1 = margin_x, margin_x + array_width
        c.add_polygon(
            [
                (x0, row_y - ROW_TRACE_WIDTH / 2),
                (x1, row_y - ROW_TRACE_WIDTH / 2),
                (x1, row_y + ROW_TRACE_WIDTH / 2),
                (x0, row_y + ROW_TRACE_WIDTH / 2),
            ],
            layer=LAYER.Metal_Pad,
        )
 

    # Column bus lines (Col_Metal): one per column
    for cc in range(cols):
        col_x = margin_x + cc * UNIT_CELL_SIZE + e_col_local["x"]
        y0, y1 = margin_y, margin_y + array_height
        c.add_polygon(
            [
                (col_x - COL_TRACE_WIDTH / 2, y0),
                (col_x + COL_TRACE_WIDTH / 2, y0),
                (col_x + COL_TRACE_WIDTH / 2, y1),
                (col_x - COL_TRACE_WIDTH / 2, y1),
            ],
            layer=LAYER.Col_Metal,
        )
 
    _verify_electrical_contact(c, rows, cols, margin_x, margin_y, local_table)
 
    
    for p in array_ref.ports:
        c.add_port(name=p.name, port=p)
 
    return c
 

# --- Verifying the electrical contact by the rows/columns buses ---- 

def _verify_electrical_contact(
    c: gf.Component, rows: int, cols: int, margin_x: float, margin_y: float,
    local_table: dict, n_samples: int = 25,
) -> None:
    
    li_metal = c.kcl.layout.layer(*LAYER.Metal_Pad)
    li_col = c.kcl.layout.layer(*LAYER.Col_Metal)
    r_metal = kf.kdb.Region(c.begin_shapes_rec(li_metal))
    r_col = kf.kdb.Region(c.begin_shapes_rec(li_col))
    dbu = c.kcl.dbu
 
    import random
 
    rng = random.Random(0)
    for _ in range(n_samples):
        row = rng.randint(0, rows - 1)
        col = rng.randint(0, cols - 1)
 
        e_row_x = margin_x + col * UNIT_CELL_SIZE + local_table["e_row"]["x"]
        e_row_y = margin_y + row * UNIT_CELL_SIZE + local_table["e_row"]["y"]
        probe = kf.kdb.Region(kf.kdb.Box(
            round(e_row_x / dbu) - 1, round(e_row_y / dbu) - 1,
            round(e_row_x / dbu) + 1, round(e_row_y / dbu) + 1,
        ))
        if (r_metal & probe).is_empty():
            raise RuntimeError(
                f"Row bus doesnt electrically contact cell ({row},{col})'s "
                f"e_row tap at ({e_row_x:.2f}, {e_row_y:.2f}) - addressing "
                "geometry is broken for this cell."
            )
 
        e_col_x = margin_x + col * UNIT_CELL_SIZE + local_table["e_col"]["x"]
        e_col_y = margin_y + row * UNIT_CELL_SIZE + local_table["e_col"]["y"]
        probe2 = kf.kdb.Region(kf.kdb.Box(
            round(e_col_x / dbu) - 1, round(e_col_y / dbu) - 1,
            round(e_col_x / dbu) + 1, round(e_col_y / dbu) + 1,
        ))
        if (r_col & probe2).is_empty():
            raise RuntimeError(
                f"Column bus doesnt electrically contact cell ({row},{col})'s "
                f"e_col tap at ({e_col_x:.2f}, {e_col_y:.2f}) - addressing "
                "geometry is broken for this cell."
            )
 

 # ---- Output generation section now ---

if __name__ == "__main__":
    import os
 
    t0 = __import__("time").time()
    c = addressed_array()
    elapsed = __import__("time").time() - t0
    print(f"built + verified in {elapsed:.2f}s")
    print(f"bbox={c.bbox()}")
 

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    gds_path = os.path.join(out_dir, "addressed_array.gds")
    c.write_gds(gds_path)
    print(f"GDS written to: {gds_path}")

    import socket
 
    KLIVE_PORT = 8082
    klive_reachable = False
    try:
        with socket.create_connection(("localhost", KLIVE_PORT), timeout=0.5):
            klive_reachable = True
    except OSError:
        klive_reachable = False
 
    if klive_reachable:
        c.show()
        print("Sent to KLayout via klive (port 8082 responded).")
    else:
        print(
            f"klive is not reachable on localhost:{KLIVE_PORT} - nothing, dude "
        )

print("Done, dude!")