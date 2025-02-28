import subprocess
import threading
import sys 

from qsi.helpers import numpy_to_json, json_to_numpy
from qsi.state import State, StateProp

class ModuleReference:
    def __init__(self, module: str, port: int, coordinator_port: int, runtime: str, coordinator: "Coordinator"):
        self.coordinator = coordinator
        self.module = module
        self.port = port
        self.runtime = runtime
        self.states = []
        self.params = []
        if runtime == "python":
            command = [sys.executable, module, str(port), str(coordinator_port)]
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.events = {
            "params_known": threading.Event()
        }
        
        # Start threads to capture stdout and stderr
        threading.Thread(target=self._capture_output, args=(self.process.stdout, "stdout")).start()
        threading.Thread(target=self._capture_output, args=(self.process.stderr, "stderr")).start()

    def notify_params(self, params):
        self.events["params_known"].set()
        self.params = params
        self.params = {name: {"value":None, "type": param_type} for name, param_type in params.items()}
        print(self.params)

    def _capture_output(self, stream, stream_name):
        for line in iter(stream.readline, ''):
            print(f"[{stream_name}] {line.strip()}")
        stream.close()

    def set_param(self, param, value):
        self.events["params_known"].wait()
        if self.params[param]["type"]=="complex":
            num = complex(value)
            self.params[param]["value"] = [num.real, num.imag]
        else:
            self.params[param]["value"] = value

    def send_params(self):
        message = {
            "msg_type":"param_set",
            "params":self.params
        }
        self.coordinator.send_to(self.port, message)

    def state_init(self):
        message = {
            "msg_type" : "state_init"
        }
        response = self.coordinator.send_and_return_response(self.port, message)
        states = []
        for s in response["states"]:
            states.append(State.from_message(s))
        return states
        
    def channel_query(self, state: "State", port_assign, time=0, signals=[]):
        """
        Queries the module for the Kraus channel
        """
        message = state.to_message(port_assign)
        message["msg_type"]="channel_query"
        message["signals"]=signals
        message["time"]=time
        response = self.coordinator.send_and_return_response(self.port, message)
        print(response)
        if "kraus_operators" in response:
            operators = [json_to_numpy(x) for x in response["kraus_operators"]]
        return response, operators


    def terminate(self):
        proc = self.process
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        except Exception as e:
            print(f"Exception while terinating subprocess: {e}")
                    

