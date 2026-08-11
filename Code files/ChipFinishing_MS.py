import gdsfactory as gf
import kfactory as kf
 
import PDK_MS
from LayerMap_MS import LAYER
from ElectricalAddressing_MS import addressed_array, ROW_TRACE_WIDTH, COL_TRACE_WIDTH
from ChipArray_MS import ARRAY_ROWS, ARRAY_COLS, UNIT_CELL_SIZE, DIE_SIZE, _get_local_port_table
 
PDK_MS.activate()
 
DICING_STREET_WIDTH = 100.0  # um, sits inside a standard order of magnitude 
 
N_GRATING_IO = 8  # subset of the 50 rows wired to optical I/O
 
# ---- Grating coupler geometry (placeholder for now) ----
GRATING_PERIOD = 0.63      
GRATING_DUTY = 0.5          # fraction of period that is etched
GRATING_N_PERIODS = 20
GRATING_TAPER_LENGTH = 15.0  
GRATING_COUPLER_WIDTH = 12.0  
 
BOND_PAD_SIZE = 80.0  # wire-bond pad size
BOND_PAD_GAP = 10.0   # gap between bus end and pad edge
 
 
@gf.cell
def simple_grating_coupler(
    waveguide_width: float = 0.35,
    taper_length: float = GRATING_TAPER_LENGTH,
    period: float = GRATING_PERIOD,
    duty: float = GRATING_DUTY,
    n_periods: int = GRATING_N_PERIODS,
    coupler_width: float = GRATING_COUPLER_WIDTH,
) -> gf.Component:
    
    c = gf.Component()
    c.add_polygon(
        [
            (0, -waveguide_width / 2),
            (0, waveguide_width / 2),
            (taper_length, coupler_width / 2),
            (taper_length, -coupler_width / 2),
        ],
        layer=LAYER.Deep_Etch,
    )
    tooth_width = period * duty
    x = taper_length
    for _ in range(n_periods):
        c.add_polygon(
            [
                (x, -coupler_width / 2),
                (x + tooth_width, -coupler_width / 2),
                (x + tooth_width, coupler_width / 2),
                (x, coupler_width / 2),
            ],
            layer=LAYER.Deep_Etch,
        )
        x += period
    c.add_port(name="o1", center=(0, 0), width=waveguide_width, orientation=180,
               layer=LAYER.Deep_Etch, port_type="optical")
    return c

# ---- Bond pad --- 
 
@gf.cell
def bond_pad(size: float = BOND_PAD_SIZE, layer: tuple = None) -> gf.Component:
    
    if layer is None:
        layer = LAYER.Metal_Pad
    c = gf.Component()
    c.add_polygon([(0, 0), (size, 0), (size, size), (0, size)], layer=layer)
    return c
 

# --- Alignment mark (lithography mask) ---
@gf.cell
def alignment_mark(arm_length: float = 25.0, arm_width: float = 5.0) -> gf.Component:
   
    c = gf.Component()
    c.add_polygon(
        [(-arm_length, -arm_width / 2), (arm_length, -arm_width / 2),
         (arm_length, arm_width / 2), (-arm_length, arm_width / 2)],
        layer=LAYER.Deep_Etch,
    )
    c.add_polygon(
        [(-arm_width / 2, -arm_length), (arm_width / 2, -arm_length),
         (arm_width / 2, arm_length), (-arm_width / 2, arm_length)],
        layer=LAYER.Deep_Etch,
    )
    return c
 
 
def _select_evenly_spaced(n_total: int, n_select: int) -> list[int]:
   
    if n_select >= n_total:
        return list(range(n_total))
    step = n_total / n_select
    return sorted({int(i * step) for i in range(n_select)})
 

# ---- Bringing the ElectricalAddressing_MS info to finish the chip ----
@gf.cell
def finished_chip(
    rows: int = ARRAY_ROWS,
    cols: int = ARRAY_COLS,
    die_size: float = DIE_SIZE,
    n_io: int = N_GRATING_IO,
) -> gf.Component:
   
    c = gf.Component()
    array_ref = c << addressed_array(rows=rows, cols=cols, die_size=die_size)
 
    array_width = cols * UNIT_CELL_SIZE
    array_height = rows * UNIT_CELL_SIZE
    margin_x = (die_size - array_width) / 2
    margin_y = (die_size - array_height) / 2
    local_table = _get_local_port_table()
 
    # Edge I/O: grating couplers on the left edge
    io_rows = _select_evenly_spaced(rows, n_io)
    for r in io_rows:
        gc_ref = c << simple_grating_coupler(waveguide_width=local_table["bus_W"]["width"])
        gc_ref.connect("o1", array_ref.ports[f"bus_W_{r}"])
 
    # Bond pads: row pads on the right edge (wired to each row bus's left end), column pads on the top edge
    for r in range(rows):
        row_y = margin_y + r * UNIT_CELL_SIZE + local_table["e_row"]["y"]
        bus_end_x = margin_x + array_width  # real east end of that row's bus
        pad_ref = c << bond_pad(size=BOND_PAD_SIZE, layer=LAYER.Metal_Pad)
        pad_ref.dcenter = (bus_end_x + BOND_PAD_GAP + BOND_PAD_SIZE / 2, row_y)

        # Connecting trace
        c.add_polygon(
            [
                (bus_end_x, row_y - ROW_TRACE_WIDTH / 2),
                (bus_end_x + BOND_PAD_GAP, row_y - ROW_TRACE_WIDTH / 2),
                (bus_end_x + BOND_PAD_GAP, row_y + ROW_TRACE_WIDTH / 2),
                (bus_end_x, row_y + ROW_TRACE_WIDTH / 2),
            ],
            layer=LAYER.Metal_Pad,
        )
 
    for cc in range(cols):
        col_x = margin_x + cc * UNIT_CELL_SIZE + local_table["e_col"]["x"]
        bus_end_y = margin_y + array_height  # real north end of that column's bus
        pad_ref = c << bond_pad(size=BOND_PAD_SIZE, layer=LAYER.Col_Metal)
        pad_ref.dcenter = (col_x, bus_end_y + BOND_PAD_GAP + BOND_PAD_SIZE / 2)
        c.add_polygon(
            [
                (col_x - COL_TRACE_WIDTH / 2, bus_end_y),
                (col_x + COL_TRACE_WIDTH / 2, bus_end_y),
                (col_x + COL_TRACE_WIDTH / 2, bus_end_y + BOND_PAD_GAP),
                (col_x - COL_TRACE_WIDTH / 2, bus_end_y + BOND_PAD_GAP),
            ],
            layer=LAYER.Col_Metal,
        )
 
    # Alignment marks: 3 of 4 corners 
    mark_offset = DICING_STREET_WIDTH + 50.0
    for x, y in (
        (mark_offset, mark_offset),                          
        (die_size - mark_offset, mark_offset),                
        (mark_offset, die_size - mark_offset),                
        # NE deliberately skipped
    ):
        mark_ref = c << alignment_mark()
        mark_ref.dcenter = (x, y)
 
    # --- Dicing street keep-out check ---

    _verify_dicing_street_clearance(c, die_size)
 
    # ---- Die floorplan / dicing street outlines ---
    c.add_polygon(
        [(0, 0), (die_size, 0), (die_size, die_size), (0, die_size)],
        layer=LAYER.Floor_Plan,
    )
    c.add_polygon(
        [
            (DICING_STREET_WIDTH, DICING_STREET_WIDTH),
            (die_size - DICING_STREET_WIDTH, DICING_STREET_WIDTH),
            (die_size - DICING_STREET_WIDTH, die_size - DICING_STREET_WIDTH),
            (DICING_STREET_WIDTH, die_size - DICING_STREET_WIDTH),
        ],
        layer=LAYER.Floor_Plan,
    )
 
    return c
 

# ---- Confirming the produced geometry ---- 
def _verify_dicing_street_clearance(c: gf.Component, die_size: float) -> None:
   
    real_layers = [LAYER.Shallow_Etch, LAYER.Deep_Etch, LAYER.Metal_Pad, LAYER.Col_Metal]
    dbu = c.kcl.dbu
    inner = DICING_STREET_WIDTH / dbu
    outer = (die_size - DICING_STREET_WIDTH) / dbu
 
    for layer in real_layers:
        li = c.kcl.layout.layer(*layer)
        region = kf.kdb.Region(c.begin_shapes_rec(li))
        if region.is_empty():
            continue
        bbox = region.bbox()
        if bbox.left < inner or bbox.bottom < inner or bbox.right > outer or bbox.top > outer:
            raise RuntimeError(
                f"Layer {layer.name} has geometry at bbox "
                f"{[v * dbu for v in (bbox.left, bbox.bottom, bbox.right, bbox.top)]} "
                f"um, intrudes into the {DICING_STREET_WIDTH} um dicing "
                f"street keep-out (must stay within "
                f"[{DICING_STREET_WIDTH}, {die_size - DICING_STREET_WIDTH}] "
                "on both axes)."
            )
 

# ---- Output section ---- 

if __name__ == "__main__":
    import os
    import socket
    import time
 
    t0 = time.time()
    c = finished_chip()
    elapsed = time.time() - t0
    print(f"built + verified in {elapsed:.2f}s")
    print(f"bbox={c.bbox()}")
 
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    gds_path = os.path.join(out_dir, "finished_chip.gds")
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
            f"klive not reachable on localhost:{KLIVE_PORT} - nothing, dude. "

        )