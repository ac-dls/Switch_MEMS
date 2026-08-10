#LayerMap_MS
# Project at hand: MEMS-actuated directional coupler optical switch process (cantilever + movable coupler + waveguide crossing)
# This file consists of Stage 0: here I define a Layer Map with all of the processes 

import gdsfactory as gf
from gdsfactory.gpdk import PDK
 
# Let's start 
 
Layer = tuple[int, int]
 
class LAYER(gf.LayerEnum):
 
    layout= gf.constant(gf.kcl.layout)
 
    Wafer: Layer=(999, 0)
 
    # ---- Mask layers ----
 
    Shallow_Etch: Layer=(1, 0)
 
    Deep_Etch: Layer=(2, 0)
 
    Metal_Pad: Layer=(3, 0)
 
    Box: Layer=(4, 0)
 
    Col_Metal: Layer = (5, 0)
 
    # ---- DRC-aid layers ----
 
    Etch_hole: Layer=(10, 0)
 
    Anchor: Layer=(11, 0)
 
    # ---- Floorplan and keep-out layers ----
 
    Unit_Cell: Layer=(90, 0)
 
    Floor_Plan: Layer=(99, 0)
 
    # ---- Useful layers gdsfactory wants ----
 
    Port: Layer=(1, 10)
 
    PortE: Layer=(1, 11)
 
    DEVREC: Layer=(68, 0)
 
    Text: Layer=(66, 0)
 
 
# Checkpoint for all the defined layers
 
if __name__ == "__main__": 
 
    for member in LAYER: 
        print(f"{member.name:12s} - {(member.layer, member.datatype)}")
 
 
 
print("Done, dude!")