import time
import numpy as np

class PIDController:
    """A simple PID controller."""
    def __init__(self, Kp, Ki, Kd, setpoint, output_limits=(-10, 10)):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        
        self._proportional = 0
        self._integral = 0
        self._derivative = 0
        
        self._last_error = 0
        self._last_time = time.time()

    def update(self, process_variable):
        """Calculate PID output."""
        current_time = time.time()
        dt = current_time - self._last_time
        
        if dt <= 0:
            return 0
            
        error = self.setpoint - process_variable
        
        # Proportional term
        self._proportional = self.Kp * error
        
        # Integral term
        self._integral += self.Ki * error * dt
        self._integral = self._clamp(self._integral, self.output_limits)
        
        # Derivative term
        error_derivative = (error - self._last_error) / dt
        self._derivative = self.Kd * error_derivative
        
        # Calculate output
        output = self._proportional + self._integral + self._derivative
        output = self._clamp(output, self.output_limits)
        
        # Update state
        self._last_error = error
        self._last_time = current_time
        
        return output

    def _clamp(self, value, limits):
        """Clamp the value to be within the given limits."""
        lower, upper = limits
        return max(lower, min(value, upper))

class SystemSimulation:
    """Manages the state of the PID system simulation."""
    def __init__(self):
        # PID gains tuned for a reasonably quick and stable response
        self.pid = PIDController(Kp=0.2, Ki=0.05, Kd=0.1, setpoint=100)
        self.process_variable = 100.0  # Represents system stability
        self.last_step_time = time.time()
        
        # Store history for plotting
        self.history = {
            "time": [],
            "process_variable": [],
            "setpoint": [],
            "controller_output": []
        }
        self._max_history = 100

    def step(self):
        """Advance the simulation by one time step."""
        current_time = time.time()
        dt = current_time - self.last_step_time
        self.last_step_time = current_time

        # Get controller output
        control_output = self.pid.update(self.process_variable)
        
        # Simulate system response: controller action pushes it towards setpoint
        # Add some natural resistance/drag
        drag_factor = -0.05 * (self.process_variable - 100)
        self.process_variable += (control_output + drag_factor) * dt * 10
        
        # Add a little noise to make it look more realistic
        self.process_variable += np.random.normal(0, 0.1)

        # Update history
        self._update_history(control_output)

    def trigger_disturbance(self, severity=80):
        """Simulate a tamper event by introducing a large disturbance."""
        print(f"💥 PID Simulation: Disturbance triggered! Stability dropped by {severity} points.")
        self.process_variable -= severity
        # Reset integral to allow faster response to new, large error
        self.pid._integral = 0

    def _update_history(self, control_output):
        """Append current state to history and keep it at a max length."""
        self.history["time"].append(time.time())
        self.history["process_variable"].append(self.process_variable)
        self.history["setpoint"].append(self.pid.setpoint)
        self.history["controller_output"].append(control_output)
        
        # Trim history
        for key in self.history:
            self.history[key] = self.history[key][-self._max_history:]

    def get_history(self):
        """Return the current simulation history."""
        return self.history

# A global instance of the simulation
simulation = SystemSimulation()
