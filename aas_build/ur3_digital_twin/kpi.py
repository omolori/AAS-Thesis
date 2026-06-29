import numpy as np


def calculate_rms_current(currents):

    currents = np.array(currents)

    rms = np.sqrt(np.mean(currents**2))

    return round(float(rms), 3)


def calculate_energy(currents,
                     voltage=48,
                     cycle_time=100):

    avg_current = np.mean(np.abs(currents))

    energy = voltage * avg_current * cycle_time

    return round(float(energy), 2)