"""

Analysis helpers.

"""

def calc_norm_dist_mismatch( q1, q2, q3, mean, std_dev ):
    """Calculate mismatch between q1, q2, and q3 and the estimated normal distribution params.

    :param q1: First quartile.
    :type q1: float
    :param q2: Median.
    :type q2: float
    :param q3: Third quartile.
    :type q3: float
    :param mean: Distribution mean.
    :type mean: float
    :param std_dev: Estimated standard deviation.
    :type std_dev: float
    :return: Mismatch between quartiles and their expected values based on the normal distribution params.
    :rtype: list
    """

    return [
        q1 - (mean - 0.675 * std_dev),
        q2 - mean,
        q3 - (mean + 0.675 * std_dev)
    ]


def get_status_from_stdout(path):
    """Read stdout log and extract status. Unknown failure is represented by -1.

    :param path: Absoolute path to stdout.
    :type path: str
    :return: status
    :rtype: int
    """

    # Open stdout
    with open(path, 'r') as f:
        line = f.readlines()[-1]

        # Interpret output
        if 'BER' in line and 'unattainable' in line:
            return 1 # Expected, has status code
        else:
            return -1 # Unknown reason for failure

