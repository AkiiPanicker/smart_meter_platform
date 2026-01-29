import time
import numpy as np
import random

class PIDController:
    """A standard PID controller implementation."""
    def __init__(self, Kp, Ki, Kd, setpoint, output_limits=(-10, 10)):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        
        self._integral = 0
        self._last_error = 0
        self._last_time = time.time()

    def update(self, process_variable):
        current_time = time.time()
        dt = current_time - self._last_time
        if dt <= 0: return 0 

        error = self.setpoint - process_variable
        
        # P Term
        proportional = self.Kp * error
        
        # I Term
        self._integral += self.Ki * error * dt
        self._integral = max(self.output_limits[0], min(self._integral, self.output_limits[1])) 
        
        # D Term
        derivative = (error - self._last_error) / dt
        
        # Output
        output = proportional + self._integral + (self.Kd * derivative)
        output = max(self.output_limits[0], min(output, self.output_limits[1]))
        
        self._last_error = error
        self._last_time = current_time
        
        return output

class SystemSimulation:
    def __init__(self):
        # Slightly more aggressive tuning so it reaches 100 strictly
        self.pid = PIDController(Kp=1.2, Ki=0.5, Kd=0.1, setpoint=100)
        self.process_variable = 100.0
        self.last_step_time = time.time()
        
        # Store history
        self.history = {
            "time": [],
            "process_variable": [],
            "setpoint": [],
            "controller_output": []
        }
        self._max_history = 60 

    def step(self):
        current_time = time.time()
        dt = current_time - self.last_step_time
        if dt < 0.05: return 
        self.last_step_time = current_time

        control_output = self.pid.update(self.process_variable)
        
        # Physics: System naturally wants to fall to 80 without intervention
        natural_decay = -0.3 * (self.process_variable - 80)
        
        self.process_variable += (natural_decay + control_output) * dt
        
        # REDUCED NOISE: From 0.2 down to 0.02. 
        # This will make the graph a straight line, making dips clearly visible.
        self.process_variable += np.random.uniform(-0.02, 0.02) 

        self._update_history(control_output)

    def trigger_disturbance(self):
        print("💥 PID Simulation: Disturbance Triggered!")
        # Big instant drop to visualy show the red line spiking to fix it
        self.process_variable -= 40 
        self.pid._integral = 0 

    def _update_history(self, output):
        self.history["time"].append(time.time())
        self.history["process_variable"].append(round(self.process_variable, 2))
        self.history["setpoint"].append(self.pid.setpoint)
        # We assume baseline correction is 0 visually for cleaner graph
        self.history["controller_output"].append(round(output, 2) + 80) 
        
        if len(self.history["time"]) > self._max_history:
            for k in self.history:
                self.history[k].pop(0)

    def get_history(self):
        return self.history

# Singleton instance
simulation = SystemSimulation()
