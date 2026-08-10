# I needed PDK support so that everything ran smoothly with gdsfactory guidelines
import gdsfactory as gf
from gdsfactory.gpdk import get_generic_pdk
 
from LayerMap_MS import LAYER
from LayerStack_ms import get_layer_stack
 
PDK = gf.Pdk(
    name="mems_switch_pdk",
    layers=LAYER,
    # "through" state (0 V rest state) as the default reference stack --
    # switch to get_layer_stack("drop") if you need the actuated-state
    
    layer_stack=get_layer_stack("through"),
    base_pdks=[get_generic_pdk()],
)
 
 
def activate() -> None:
    """Activate this PDK (obviously). Call once, before building/opening any cell."""
    PDK.activate()
 
 
if __name__ == "__main__":
    activate()
    print(f"Activated PDK: {PDK.name}")

print("Done, dude")