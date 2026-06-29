# AAS Gazebo Simulation Pipeline

This folder contains the ROS 2 and Gazebo implementation of the AAS-driven UR3 simulation pipeline.

## Purpose

The pipeline demonstrates how AAS-defined robot parameters can be represented in a Gazebo-based UR3 simulation and used to generate performance KPI results.

## AAS Parameters Used

### MotionCommand

- TargetJointPositions
- SpeedScaling
- PayloadMass

### DynamicsParameters

- FrictionCoefficient
- CurrentNoiseLevel
- ControlLatency
- DampingFactor

In this version, the AAS values are hardcoded inside `pipeline3.py`. The next step is to replace these hardcoded values with live reads from the BaSyx AAS server.

## Performance KPIs Produced

- CycleTime
- RMSCurrent
- RMSCurrentPerJoint
- EnergyConsumption
- PositionError

## Latest Validation Run

The latest successful run produced:

- Total trajectory time: 107.61 s
- Cycle time: 35.538 s
- RMSCurrent: 0.38665 A
- EnergyConsumption: 500.02450
- PositionError: 1.505907 rad

The output files are included in `sample_results/`.

## Build

```bash
cd ~/ros2_ws
colcon build --packages-select ur3_trajectory_runner
source install/setup.bash
