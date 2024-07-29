"""
Coordinator example
-------------------
Coordinator runs the example modules
"""
import numpy as np
import uuid
from qsi.coordinator import Coordinator
from qsi.state import State, StateProp

coordinator = Coordinator()
sps = coordinator.register_componnet(module="single_photon_source.py", runtime="python")
mem = coordinator.register_componnet(module="memory.py", runtime="python")
coordinator.run()

# Set the parameters of the devices
sps.set_param("test", 2+1j)

# Set all configured parameters to the device
sps.send_params()

# Initialize states
sps.state_init()
state_mem = mem.state_init()[0]
state_one = State(StateProp(
    state_type="light",
    truncation=3,
    wavelength=1550,
    polarization="R"
))

sps_kraus, error, retry= sps.channel_query(
    state_one, {"input": state_one.state_props[0].uuid}
)
state_one.apply_kraus_operators(sps_kraus)

state_one.merge(state_mem)
print(state_one.state_props)
print([x.uuid for x in state_one.state_props])

mem_kraus, error, retry = mem.channel_query(
    state_one, {"input": state_one.state_props[0].uuid}
)

state_one.apply_kraus_operators(mem_kraus)



coordinator.terminate()
