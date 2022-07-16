"""

Statistics helpers.

"""

import numpy as np

def describe_normal_distribution(samples):
    """Describe latency distribution. Use only Numpy built-in functionality.
    :return: Latency distribution described with (keys): mean, var, min, q1, q2, q3, and max.
    :rtype: dict
    """
    return {
        'mean': np.mean(samples), # Intermediate fast   (x*10 us for 10_000 points)
        'var': np.var(samples), # Intermediate fast     (x*10 us for 10_000 points)
        'min': np.min(samples), # Fast                  (x*1 us for 10_000 points)
        'q1': np.percentile(samples, 25), # Slow        (x*100 us for 10_000 points)
        'q2': np.median(samples), # Intermediate slow   (100 us for 10_000 points)
        'q3': np.percentile(samples, 75), # Slow        (x*100 us for 10_000 points)
        'max': np.max(samples) # Fast                   (x*1 us for 10_000 points)
    }
