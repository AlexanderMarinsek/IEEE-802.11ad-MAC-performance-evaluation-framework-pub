"""

Module containing the Db class.

The Db includes mapping between process IDs, their input parameters, intermediate data (MCS), and results.

Note: `Db` saves data to the `log` directory. With regards to the process log `PLog` class, the `Db` class can be
regarded as a simulation log.

"""


import os

import pandas as pd


class Db():
    """Database abstraction class."""

    def __init__(self, indexes, config_columns, msdu_latency_columns):
        """Generate internal storage element (based on Pandas)."""

        self.config_table = pd.DataFrame( index=indexes, columns=config_columns)
        self.status_table = pd.DataFrame( index=indexes, columns=['status'])
        self.mcs_table = pd.DataFrame( index=indexes, columns=['mcs'])
        self.throughput_table = pd.DataFrame( index=indexes, columns=['throughput'])
        self.msdu_latency_table = pd.DataFrame( index=indexes, columns=msdu_latency_columns)


    def add_results(self, pid, config, status, mcs, throughput, msdu_latency):
    # def add_results(self, pid, config, status, throughput, msdu_latency):
        """Add results to database (in RAM).

        :param pid: Process ID.
        :type pid: int
        :param config: Single simulation configuration.
        :type config: list or dict
        :param mcs: Modulation and coding scheme used for obtaining the current result.
        :type mcs: float
        :param throughput: Reported throughput.
        :type throughput: float
        :param msdu_latency: Reported MSDU latency distribution values.
        :type msdu_latency: list or dict
        """

        self.config_table.iloc[pid] = config
        self.status_table.iloc[pid] = status
        self.mcs_table.iloc[pid] = mcs
        self.throughput_table.iloc[pid] = throughput
        self.msdu_latency_table.iloc[pid] = msdu_latency


    def save(self, dirpath):
        """Save DB tables.

        :param dirpath: Path to directory where the tables will reside.
        :type dirpath: str
        """

        self.config_table.to_csv(os.path.join(dirpath, 'config_table.csv'), index_label='pid')
        self.status_table.to_csv(os.path.join(dirpath, 'status_table.csv'), index_label='pid')
        self.mcs_table.to_csv(os.path.join(dirpath, 'mcs_table.csv'), index_label='pid')
        self.throughput_table.to_csv(os.path.join(dirpath, 'throughput_table.csv'), index_label='pid')
        self.msdu_latency_table.to_csv(os.path.join(dirpath, 'msdu_latency_table.csv'), index_label='pid')
