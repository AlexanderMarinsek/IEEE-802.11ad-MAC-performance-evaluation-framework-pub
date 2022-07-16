import os
import re
import pickle as pkl

from tqdm import tqdm
import numpy as np
import pandas as pd

from .helpers import get_status_from_stdout


class Table():
    """Table for combining, indexig, and debugging results."""

    def __init__(self, table_name, analysis_sid_path):
        """Init new.

        :param table_name: IndexingTable name, including file extension (csv).
        :type table_name: str
        :param analysis_sid_path: Absolute path SID analysis sub-directory.
        :type analysis_sid_path: str
        """

        self.table_name = table_name
        self.analysis_sid_path = analysis_sid_path
        self.table_path = os.path.join(analysis_sid_path, table_name) # Path to table csv
        self.df = None

    def generate_df_and_csv(self, PID_values, cols):
        """Generate new table and store as csv.

        :param PID_values: PID values (csv indexes).
        :type PID_values: list or ndarray
        :param PID_values: csv columns.
        :type PID_values: list or ndarray
        """

        # Check for existence
        if self.table_name in os.listdir(self.analysis_sid_path):
            raise RuntimeError(f'{self.table_name} already exists in: {self.analysis_sid_path}')

        # Make new table and save as csv
        df = pd.DataFrame(
            columns=cols,
            index=PID_values
        )
        df.to_csv(self.table_path)

    def open(self):
        """Open table (load into memory)."""
        self.df = pd.read_csv(self.table_path, index_col=0)

    def add_entry(self, pid, vals):
        """Add entry to table.

        :param pid: Process ID.
        :type pid: int
        :param vals: Values (row) to write at PID (index).
        :type vals: list or ndarray
        """

        self.df.iloc[pid] = vals

    def save_and_close(self):
        """Save and close the table (release from memory)."""
        self.df.to_csv(self.table_path)
        self.df = None

    def get_df(self):
        """Get table as dataframe.

        :return: Table as dataframe.
        :rtype: object
        """
        return self.df


class ResultManipulator():
    """For debugging, indexing and combining individual simulation results."""

    def __init__(self, log_sid_path, analysis_sid_path):
        """
        :param log_sid_path: Absolute path to study log directory.
        :type log_sid_path: str
        :param analysis_sid_path: Absolute path to study analysis directory.
        :type analysis_sid_path: str
        """
        self.log_sid_path = log_sid_path
        self.analysis_sid_path = analysis_sid_path

    def combine_index_and_debug_results(self):
        """Combine, index and extract completion status from results."""

        # Count and generate PIDs list
        with open(os.path.join(self.log_sid_path, 'config.pkl'), 'rb') as f:
            study_config = pkl.load(f)
        max_pid = 1
        for v in study_config.values():
            max_pid *= len(v)
        pid_list = [*range(max_pid)]

        # Generate column names
        study_config_cols = study_config.keys()
        msdu_latency_cols = [ 'mean', 'var', 'min', 'q1', 'q2', 'q3', 'max' ]

        # Generate new tables
        results_directory_table = Table('results_directory_table.csv', self.analysis_sid_path)
        results_status_table = Table('results_status_table.csv', self.analysis_sid_path)
        msdu_latency_table = Table('msdu_latency_table.csv', self.analysis_sid_path)
        throughput_table = Table('throughput_table.csv', self.analysis_sid_path)

        results_directory_table.generate_df_and_csv(pid_list, study_config_cols)
        results_status_table.generate_df_and_csv(pid_list, ['status'])
        msdu_latency_table.generate_df_and_csv( pid_list , msdu_latency_cols )
        throughput_table.generate_df_and_csv( pid_list, ['throughput'] )

        results_directory_table.open()
        results_status_table.open()
        msdu_latency_table.open()
        throughput_table.open()

        # dirs = os.listdir(self.log_sid_path)
        rg = [*range(max_pid)]

        log_depth = len(str(max_pid//1000))

        # Populate tables
        # for name in tqdm(rg):
        for pid in tqdm(rg):

            # if not re.match('^[0-9]+$', name):
            #     print(f'Skipping name {name}')
            #     continue
            # pid = int(name)
            name = f'{pid:012d}'

            dirpath = os.path.join(
                self.log_sid_path,
                *list(f'{pid//1000:0{log_depth}d}'),
                f'{pid%1000:04d}'
            )

            # Link PID (directory name) to single config
            # with open(os.path.join(self.log_sid_path, name, 'config.pkl'), 'rb') as f:
            with open(os.path.join(dirpath, 'config.pkl'), 'rb') as f:
                single_config = pkl.load(f)
            results_directory_table.add_entry( pid, single_config.values() )

            # Extract simulation status (completed, expected, or unexpected failure)
            # with open(os.path.join(self.log_sid_path, name, 'metadata.pkl'), 'rb') as f:
            with open(os.path.join(dirpath, 'metadata.pkl'), 'rb') as f:
                single_metadata = pkl.load(f)
                if not single_metadata['t_end'] is None:
                    status = 0
                else:
                    # status = get_status_from_stdout( os.path.join(self.log_sid_path, name, 'std.out') )
                    status = get_status_from_stdout( os.path.join(dirpath, 'std.out') )
            results_status_table.add_entry( pid, [status] )
            if status != 0: continue # Quit if there aren't any performance metrics

            # Get performance metrics, given they exist
            try:
                # with open(os.path.join(self.log_sid_path, name, 'msdu_latency.pkl'), 'rb') as f:
                with open(os.path.join(dirpath, 'msdu_latency.pkl'), 'rb') as f:
                    msdu_latency = list(pkl.load(f).values())
                msdu_latency_table.add_entry( pid, msdu_latency )
                # with open(os.path.join(self.log_sid_path, name, 'throughput.pkl'), 'rb') as f:
                with open(os.path.join(dirpath, 'throughput.pkl'), 'rb') as f:
                    throughput = pkl.load(f)
                throughput_table.add_entry( pid, throughput )
            except Exception as e:
                pass


        # Save tables
        results_directory_table.save_and_close()
        results_status_table.save_and_close()
        msdu_latency_table.save_and_close()
        throughput_table.save_and_close()


    def generate_latency_distribution_check(self):
        """Generate table containing comparison between estimated normal distribution parameters and q1, q2, and q3.

        The results show how far off the normal distribution is from quartiles 1, 2, and 3.
        In the table, they are represented in absolute and relative (alongside, to the right) values.

        """

        msdu_latency_table = Table('msdu_latency_table.csv', self.analysis_sid_path)
        msdu_latency_table.open()
        msdu_latency_df = msdu_latency_table.get_df()

        data = [
            msdu_latency_df['q1'] - (msdu_latency_df['mean'] - 0.675 * msdu_latency_df['var'].pow(0.5)),
            msdu_latency_df['q2'] - msdu_latency_df['mean'],
            msdu_latency_df['q3'] - (msdu_latency_df['mean'] + 0.675 * msdu_latency_df['var'].pow(0.5))
        ]

        data = np.array([
            data[0],
            data[0] / msdu_latency_df['q1'],
            data[1],
            data[1] / msdu_latency_df['q2'],
            data[2],
            data[2] / msdu_latency_df['q3']
        ]).transpose()

        cols = [
            'q1 - (mean - 0.675 * std_dev)',
            '< relative',
            'q2 - mean',
            '< relative',
            'q3 - (mean + 0.675 * std_dev)',
            '< relative'
        ]

        dist_check_df = pd.DataFrame(
            index=msdu_latency_df.index.values,
            columns=cols,
            data=data
        )

        dist_check_df.to_csv( os.path.join(self.analysis_sid_path, 'latency_dist_check_table.csv') )
