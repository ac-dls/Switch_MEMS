# LayerStack_MS

from gdsfactory.technology import LayerLevel, LayerStack, LogicalLayer
 
from LayerMap_MS import LAYER
 
nm = 1e-3  # a little conversion to nm
 
 
class MEMSSwitchStackParameters:
   
 
    # ---- SOI wafer  ----
    thickness_si_device: float = 220 * nm       # device Si layer
    thickness_box: float = 3.0                  # buried oxide = release gap z0 (um)
 
    # --- Establishing the process flow ----
    thickness_shallow_etch: float = 70 * nm     # Mask 1 partial-etch depth
    thickness_cr: float = 5 * nm                # Mask 3 liftoff: Cr adhesion layer
    thickness_au: float = 30 * nm               # Mask 3 liftoff: Au
 
    # ---- Cantilever behavior def ----
    cantilever_rest_deflection: float = 1.0     # um, natural upward bend at 0 V
 
    # --- generic SOI handle wafer (placeholder only) ----
    substrate_thickness: float = 500.0          # um
 
 
P = MEMSSwitchStackParameters
thickness_metal = P.thickness_cr + P.thickness_au
thickness_slab_after_shallow_etch = P.thickness_si_device - P.thickness_shallow_etch
 
# ---- Now, derived (boolean) layers: splitting the Deep_Etch silicon into the part ----
# that's mechanically anchored vs. the part that's released and moves

layer_deep_etch = LogicalLayer(layer=LAYER.Deep_Etch)
layer_anchor = LogicalLayer(layer=LAYER.Anchor)
layer_anchored_si = layer_deep_etch & layer_anchor
layer_released_si = layer_deep_etch - layer_anchor
 

 # ---- Building the mechanical states ("through", "drop") of the switch ----
def get_layer_stack(state: str = "through") -> LayerStack:
    
    if state not in ("through", "drop"):
        raise ValueError("state must be 'through' or 'drop'")
 
    released_si_z_offset = P.cantilever_rest_deflection if state == "through" else 0.0
 
    layers = dict(
        substrate=LayerLevel(
            layer=LogicalLayer(layer=LAYER.Wafer),
            thickness=P.substrate_thickness,
            zmin=-P.substrate_thickness - P.thickness_box,
            material="si",
            mesh_order=101,
            info={"note": "placeholder, dude"},
        ),
        box=LayerLevel(
            layer=LogicalLayer(layer=LAYER.Wafer),
            thickness=P.thickness_box,
            zmin=-P.thickness_box,
            material="sio2",
            mesh_order=9,
            info={"source": "BOX = release gap z0 = 3 um"},
        ),
        shallow_etch_slab=LayerLevel(
            layer=LogicalLayer(layer=LAYER.Shallow_Etch),
            thickness=thickness_slab_after_shallow_etch,
            zmin=0.0,
            material="si",
            mesh_order=1,
            info={"source": "70 nm partial etch of 220 nm device layer"},
        ),
        anchored_si=LayerLevel(
            layer=layer_anchored_si,
            derived_layer=layer_anchor,
            thickness=P.thickness_si_device,
            zmin=0.0,
            material="si",
            mesh_order=2,
            info={"note": "anchored to substrate, does not move"},
        ),
        released_si=LayerLevel(
            layer=layer_released_si,
            derived_layer=layer_deep_etch,
            thickness=P.thickness_si_device,
            zmin=released_si_z_offset,
            material="si",
            mesh_order=2,
            info={
                "note": "movable cantilever + coupler waveguide",
                "state": state,
                "source": "1 um rest deflection, 0 when actuated",
            },
        ),
        metal_pad=LayerLevel(
            layer=LogicalLayer(layer=LAYER.Metal_Pad),
            thickness=thickness_metal,
            zmin=P.thickness_si_device,
            material="Cr/Au",
            mesh_order=1,
            info={
                "source": "5 nm Cr + 30 nm Au liftoff",
                "note": "sits on the ANCHORED Si - doesn't move",
            },
        ),
    )
    return LayerStack(layers=layers)
 
 
LAYER_STACK_THROUGH = get_layer_stack("through")
LAYER_STACK_DROP = get_layer_stack("drop")
 
 
if __name__ == "__main__":
    for name, stack in (("through", LAYER_STACK_THROUGH), ("drop", LAYER_STACK_DROP)):
        print(f"- {name}-state stack-")
        for level_name, level in stack.layers.items():
            zmin, zmax = level.bounds
            print(f"  {level_name:16s} z=[{zmin:.4f}, {zmax:.4f}] um  ({level.material})")

print("Done, dude!")

    



