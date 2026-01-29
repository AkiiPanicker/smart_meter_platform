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
        
        # I Term with Anti-Windup (Important for stability)
        self._integral += self.Ki * error * dt
        self._integral = max(-5, min(self._integral, 5)) 
        
        # D Term
        derivative = (error - self._last_error) / dt
        
        # Output
        output = proportional + self._integral + (self.Kd * derivative)
        
        # Clamping
        output = max(self.output_limits[0], min(output, self.output_limits[1]))
        
        self._last_error = error
        self._last_time = current_time
        
        return output

class SystemSimulation:
    def __init__(self):
        # TUNED VALUES for smoother non-oscillating graph
        self.pid = PIDController(Kp=0.5, Ki=0.1, Kd=0.05, setpoint=100)
        self.process_variable = 100.0
        self.last_step_time = time.time()
        
        # Visual data history
        self.history = {
            "time": [],
            "process_variable": [],
            "setpoint": [],
            "controller_output": []
        }
        self._max_history = 60 # Keep 60 seconds

    def step(self):
        current_time = time.time()
        dt = current_time - self.last_step_time
        if dt < 0.05: return 
        self.last_step_time = current_time

        control_output = self.pid.update(self.process_variable)
        
        # Simulation Logic: 
        # The system naturally decays towards 80 if untouched. 
        # The PID output pushes it back up to 100.
        natural_decay = -0.3 * (self.process_variable - 80)
        
        self.process_variable += (natural_decay + control_output) * dt
        
        # Add very small noise for realism
        self.process_variable += np.random.uniform(-0.2, 0.2)

        self._update_history(control_output)

    def trigger_disturbance(self):
        """Called by the AI model when Tamper is detected."""
        print("💥 PID Simulation: Disturbance Triggered!")
        # Instant large drop to demonstrate controller recovery
        self.process_variable -= 35 
        # Reset integral to allow fresh recovery
        self.pid._integral = 0 

    def _update_history(self, output):
        self.history["time"].append(time.time())
        self.history["process_variable"].append(round(self.process_variable, 2))
        self.history["setpoint"].append(self.pid.setpoint)
        self.history["controller_output"].append(round(output, 2))
        
        if len(self.history["time"]) > self._max_history:
            for k in self.history:
                self.history[k].pop(0)

    def get_history(self):
        return self.history

# Singleton instance
simulation = SystemSimulation()
