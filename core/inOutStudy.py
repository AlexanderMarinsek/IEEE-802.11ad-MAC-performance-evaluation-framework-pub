"""

In-out study class definitions.

There are two definitions:
- `DescriptiveInOutStudy` which generates and saves all timeslots, not just data. These feature a duration, start time,
  unique ID, and optionally a parent or one or more children. Its further development was abandoned after noticing slow
  execution times and large amounts of output data.
- `FastInOutStudy` which generates only the data transmission time slots, and supports both storage of the raw data
  (needed for the M2P performance analysis) or only storage of the main statistical descriptors.

The name `InOutStudy` was used to reflect the methodology for allocating airtime - first, individual MSDU times are
determined, followed by the network and M2P performance derivation during post-processing.

Disclaimer:
- A small discrepancy can be noticed between the descriptive and the fast study. It is caused by the difference in when
  guard intervals are inserted. That causes the BFT-SPs to take up slightly different positions. The results should not
  differ for more than several microseconds (latency distribution) and Kbps (throughput).
- The 'descriptive' study does not include multi-user support. The parent study class only allocates additional BFT-SP
  slots per user, while the DATA-SP slots stay proportionate to those (X + 1). The 'fast' study takes multiple users
  into account by dividing the combined DATA-SP and including the corresponding GI during runtime. To take into account
  multi-users in the 'descriptive' study, it must diferentiate between timeslot owners (needs timeslot class extension).

"""


import numpy as np

from .timeslot import *
from .constants import *
from .duration_generator import DurationGenerator
from .helpers import get_optimal_mcs
from .helpers import calc_a_msdu_length, calc_a_mpdu_length, calc_data_mpdu_length, calc_max_a_mpdu_subframes
from .helpers import get_number_of_bft_allocations

# TODO: Correct `sector_width = 360 / num_of_antenna_sectors` by further dividing by the DMG antenn count


class InOutStudy():
    """In-out study parent. Defines common setup methods."""

    def __init__(self, bi_duration=100*10**6, num_of_observed_bi= 10):
        """
        :param bi_duration: Beacon interval durations in nanoseconds (default 100 ms).
        :type bi_duration: int
        :param num_of_observed_bi: Number of beacond intervals included in the calculations.
        :type num_of_observed_bi: int
        """
        self.bi_duration = bi_duration
        self.num_of_observed_bi = num_of_observed_bi
        self.dg = DurationGenerator()
        self.tig = TimeslotIdGenerator()
        self.dg.generate_cts_duration()


    # def set_mcs(self, Eb_N0, max_ber):
    def set_mcs(self, Eb_N0, max_ber, ber_results_abs_path):
        """Set the optimal MCS for transmission.

        :param Eb_N0: Energy per bit over noise spectral density.
        :type Eb_N0: float
        :param max_ber: Highest allowed BER.
        :type max_ber: float
        :param ber_results_abs_path: Absolute path to simulation BER results csv file (including filename).
        :type ber_results_abs_path: str
        """

        Eb_N0 = Eb_N0
        max_ber = max_ber
        # self.mcs = get_optimal_mcs(Eb_N0, max_ber)
        self.mcs = get_optimal_mcs(Eb_N0, max_ber, ber_results_abs_path)


    def set_num_of_users(self, num_of_users):
        """Set the number of users. Equally divide all DATA SPs among them.
        :param num_of_users: Number of equally prioritised users.
        :type num_of_users: int
        """
        self.num_of_users = num_of_users


    def set_bft_duration(self, num_of_ue_antennas, num_of_antenna_sectors, enalbe_sls, enable_ap_ss):
        """Set BFT duration based on BFT param config.

        :param num_of_ue_antennas: Number of user equipment antennas (initiator).
        :type num_of_ue_antennas: int
        :param num_of_antenna_sectors: Number of antenna sectors, same for both UE and AP.
        :type num_of_antenna_sectors: int
        :param enalbe_sls: Flag informing whether or not to include SLS (otherwise just BRP).
        :type enalbe_sls: bool
        :param enable_ap_ss: Flag informing whether to conduct AP sector sweep (RXSS).
        :type enable_ap_ss: bool
        """

        self.dg.generate_bft_duration(
            num_of_ue_antennas, num_of_antenna_sectors,
            1, num_of_antenna_sectors,
            enalbe_sls,
            enable_ap_ss
        )


    # def set_bft_period(self, v, w):


    # def set_num_of_data_sp_allocations(self, num_of_antenna_sectors, speed, angular_velocity):
    def set_num_of_data_sp_allocations(self, num_of_antenna_sectors, mobility):
        """Set number of DATA and BFT allocations per BI.

        BFT-SP allocations are made per user. DATA-SP allocations are just the timeslots between BFT-SPs. Therefore,
        they are per group of users and must be further split among the users during later usage. GIs are also not yet present.

        :param num_of_antenna_sectors: Number of antenna sectors, both for UE and AP.
        :type num_of_antenna_sectors: int
        :param speed: User speed while moving in a circle around the AP, meters per second.
        :type speed: int
        :param angular_velocity: XR user head turning rate in degrees per second.
        :type angular_velocity: int
        """

        # sector_width = ANTENNA_AZIMUTH_COVERAGE_DEG / num_of_antenna_sectors
        sector_width = 360 / num_of_antenna_sectors # Sectors devide entire circle

        # # Calc BFT period based on angular velocity and movement speed. If 0, no BFT is required.
        # if speed > 0:   t_bft_spd = int(((np.pi * UE_TO_AP_DISTANCE_M * sector_width * 10**9) / 180) / speed)
        # else:           t_bft_spd = self.num_of_observed_bi * self.bi_duration # Will not spawn any BFT
        # if angular_velocity > 0:   t_bft_ang = int(sector_width * 10**9 / angular_velocity)
        # else:           t_bft_ang = self.num_of_observed_bi * self.bi_duration # Will not spawn any BFT

        # Use the shorter of the two BFT periods
        # bft_period = min(t_bft_spd, t_bft_ang)

        # if mobility is None:
        if mobility == 0 or mobility == '0':
            # bft_period = self.num_of_observed_bi * self.bi_duration
            bft_period = self.num_of_observed_bi * self.bi_duration + 1 # Will apply one BFT per observed period
        elif mobility[0] == 's':
            bft_period = int(((np.pi * UE_TO_AP_DISTANCE_M * sector_width * 10 ** 9) / 180) / int(mobility[1:]))
        elif mobility[0] == 'a':
            bft_period = int(sector_width * 10**9 / int(mobility[1:]))

        # Calculate number of needed BFT allocations for each of the observed BIs
        self.num_of_bft_allocations = get_number_of_bft_allocations(
            self.num_of_observed_bi,
            self.bi_duration,
            bft_period,
            self.num_of_users
        )

        self.num_of_data_allocations = self.num_of_bft_allocations + 1


    def set_mpdu_length(self, msdu_length_bytes, msdu_max_agg):
        """Calc and set A-MPDU subframe or just MPDU length.

        :param msdu_length_bytes: Length of individual frames in octets.
        :type msdu_length_bytes: int
        :param msdu_max_agg: Flag indicating whether to opt for maximal aggregation (True) or no aggregation (False).
        :type msdu_max_agg: bool
        """

        self.msdu_length_bytes = msdu_length_bytes # Save for later calculating the performancem etrics
        if msdu_max_agg:
            self.num_of_a_msdu_subframes = int(MAX_A_MSDU_LENGTH / msdu_length_bytes)
        else:
            self.num_of_a_msdu_subframes = 1 # 1 means no aggregation
        self.a_msdu_length_bytes = calc_a_msdu_length( self.num_of_a_msdu_subframes, msdu_length_bytes )
        self.mpdu_length_bytes = calc_data_mpdu_length(self.a_msdu_length_bytes)


    def set_psdu_length(self, mpdu_max_agg):
        """Calc and set the PSDU length. Must be preceeded by MPDU length setting.

        :param mpdu_max_agg: Flag indicating whether to opt for maximal aggregation (True) or no aggregation (False).
        :type mpdu_max_agg: bool
        """

        if mpdu_max_agg:
            self.num_of_a_mpdu_subframes = calc_max_a_mpdu_subframes(self.mcs, self.mpdu_length_bytes)
        else:
            self.num_of_a_mpdu_subframes = 1 # 1 means no aggregation
        self.psdu_length_bytes = calc_a_mpdu_length( self.num_of_a_mpdu_subframes, self.mpdu_length_bytes )


    def set_ack_duration(self):
        """Set ACK duration based on pre-calculated A-MSDU subframe count."""
        self.dg.generate_ack_duration(self.num_of_a_mpdu_subframes)


    def set_cts_enabled_flag(self, enable_cts):
        """Set self-CTS flag.

        :param enable_cts: Flag indicating the usage of self-CTS.
        :type enable_cts: bool
        """
        # self.dg.enable_cts = enable_cts
        self.enable_cts = enable_cts


    def set_ack_enabled_flag(self, enable_ack):
        """Set ACK flag.

        :param enable_ack: Flag indicating the usage of ACK.
        :type enable_ack: bool
        """
        # self.dg.enable_ack = enable_ack
        self.enable_ack = enable_ack


    def set_data_ppdu_duration(self):
        """Set data PPDU duration."""
        self.dg.generate_data_ppdu_duration(self.psdu_length_bytes, self.mcs)


    def set_data_with_overhead_duration(self, enable_cts, enable_ack):
        """Set duration of data PPDU + self-cts + ack, including all SIFS and  final DIFS.

        :param enable_cts: Flag indicating the usage of self-CTS.
        :type enable_cts: bool
        :param enable_ack: Flag indicating the usage of acknowledgements.
        :type enable_ack: bool
        """
        self.dg.generate_data_with_overhead_duration(enable_cts, enable_ack)


    def get_performance_metrics(self):
        return (self.throughput, self.msdu_latency_offset)


    def get_msdu_times(self):
        return (self.t_msdu_generated, self.t_msdu_arrival)


    def get_mcs(self):
        return self.mcs



class DescriptiveInOutStudy(InOutStudy):
    """In-out study based on time slot generation for easier debugging and a better overview of the allocated time."""


    def __init__(self):
        super().__init__()


    def run(self):
        """Run single in-out study iteration."""

        self.dg.generate_guard_time_duration(self.bi_duration)

        self.ch = ResponsibleTimeslot(self.tig.get_new_id(), 'CH', 0, self.num_of_observed_bi * self.bi_duration)
        self.total_data_blocks = 0 # Save number of data blocks for later processing

        for i, (noa, noa_bft) in enumerate(zip(self.num_of_data_allocations, self.num_of_bft_allocations)):

            self.dg.generate_bti_duration(noa)

            bi = ResponsibleTimeslot(self.tig.get_new_id(), 'BI', i * self.bi_duration, self.bi_duration)
            self.ch.add_child(bi)

            bti = Timeslot(self.tig.get_new_id(), 'BTI', i * self.bi_duration, self.dg.get_bti_duration())
            bi.add_child(bti)

            # Add BFT-SP timeslots to BI
            if noa_bft != 0:
                t_start, t_end = bi.get_available_time()[0][0], bi.get_available_time()[0][1]
                t_step = (t_end - t_start) / (noa_bft + 1)
                for idx_bft in range(noa_bft):
                    timestamp = (idx_bft + 1) * t_step - self.dg.get_bft_duration() / 2 + t_start
                    sp_bft = Timeslot(self.tig.get_new_id(), 'SP-BFT', timestamp, self.dg.get_bft_duration())
                    bi.add_child(sp_bft)

            # Add SP-DATA timeslots to BI
            at_list = bi.get_available_time()
            for at in at_list:
                # gi = Timeslot(self.tig.get_new_id(), 'GI', at[0], GI_DURATION)
                # bi.add_child(gi)

                sp_data = ResponsibleTimeslot(
                    self.tig.get_new_id(),
                    'SP-DATA',
                    at[0] + self.dg.get_guard_time_duration(), # Add GT at beginning
                    at[1] - at[0] - 2 * self.dg.get_guard_time_duration() # Subtract GI at the end (and include the one at the beginning)
                )
                # sp_data = ResponsibleTimeslot(self.tig.get_new_id(), 'SP-DATA', at[0], at[1] - at[0])
                bi.add_child(sp_data)

                # gi = Timeslot(self.tig.get_new_id(), 'GI', at[1] - GI_DURATION, GI_DURATION)
                # bi.add_child(gi)

            # Populate SP-DATA timeslots with DATA-PPDU (+ self-cts, ack, and IFS overhead) timeslots
            bi_children = bi.get_list_of_children()
            for bi_child in bi_children:
                if not isinstance(bi_child, ResponsibleTimeslot): continue
                if not bi_child.name == 'SP-DATA': continue

                num_of_tx_slots = int(bi_child.duration / self.dg.get_data_with_overhead_duration())
                self.total_data_blocks += num_of_tx_slots

                for i in range(num_of_tx_slots):  # Parallelizable

                    # tx_block = Timeslot(
                    #     self.tig.get_new_id(),
                    #     'TX',
                    #     bi_child.timestamp + i * self.dg.get_data_with_overhead_duration(),
                    #     self.dg.get_data_with_overhead_duration()
                    # )
                    # bi_child.add_child(tx_block)

                    timestamp = bi_child.timestamp + i * self.dg.get_data_with_overhead_duration()

                    # Add selt-CTS
                    if self.enable_cts:
                        cts = Timeslot(
                            self.tig.get_new_id(),
                            'self-CTS',
                            timestamp,
                            self.dg.get_cts_duration()
                        )
                        bi_child.add_child(cts)
                        timestamp += (self.dg.get_cts_duration() + SIFS_NS)

                    # Add data PPDU
                    tx_block = Timeslot(
                        self.tig.get_new_id(),
                        'TX',
                        timestamp,
                        self.dg.get_data_ppdu_duration()
                    )
                    bi_child.add_child(tx_block)
                    # timestamp += self.dg.get_data_ppdu_duration()
                    timestamp += self.dg.get_data_ppdu_duration() + SIFS_NS

                    # Add ACK
                    if self.enable_ack:
                        ack = Timeslot(
                            self.tig.get_new_id(),
                            'ACK',
                            # SIFS_NS + timestamp,
                            timestamp,
                            self.dg.get_ack_duration()
                        )
                        bi_child.add_child(ack)
                        # timestamp += ( SIFS_NS + self.dg.get_ack_duration() )

                    # timestamp += DIFS_NS


    def calc_performance_metrics(self):
        """Calculate throughput and MSDU latency performance metrics."""

        # num_of_data_ppdu = 0
        # ch_children = self.ch.get_list_of_children()
        # for bi in ch_children:
        #     bi_children = bi.get_list_of_children()
        #     for bi_child in bi_children:
        #         if not isinstance(bi_child, ResponsibleTimeslot): continue
        #         num_of_data_ppdu += len(bi_child.get_list_of_children())
        # self.throughput = self.total_data_blocks * self.psdu_length_bytes * 8 / (self.bi_duration * self.num_of_observed_bi)


        num_of_msdu_in_psdu = self.num_of_a_mpdu_subframes * self.num_of_a_msdu_subframes
        num_of_msdu = self.total_data_blocks * num_of_msdu_in_psdu

        self.throughput = num_of_msdu * self.msdu_length_bytes * 8 / (self.bi_duration * self.num_of_observed_bi)

        # num_of_msdu = self.total_data_blocks * num_of_msdu_in_psdu * self.num_of_observed_bi
        # num_of_msdu = num_of_data_ppdu  # Also influenced by MSDU/MPDU AGG

        # msdu_latency = np.zeros(num_of_msdu)
        self.t_msdu_generated = np.zeros(num_of_msdu)
        self.t_msdu_arrival = np.zeros(num_of_msdu)

        self.msdu_generation_period = (self.bi_duration * self.num_of_observed_bi) / num_of_msdu

        msdu_idx = 0
        ch_children = self.ch.get_list_of_children()
        for bi in ch_children:
            bi_children = bi.get_list_of_children()
            for bi_child in bi_children:
                if not isinstance(bi_child, ResponsibleTimeslot): continue
                if not bi_child.name == 'SP-DATA': continue
                data_ppdus = bi_child.get_list_of_children()
                for dp in data_ppdus:
                    if dp.name != 'TX': continue
                    if num_of_msdu_in_psdu == 1:
                        self.t_msdu_generated[msdu_idx] = msdu_idx * self.msdu_generation_period
                        self.t_msdu_arrival[msdu_idx] = dp.timestamp + dp.duration
                    else:
                        _begin = msdu_idx*num_of_msdu_in_psdu
                        _end = (msdu_idx+1)*num_of_msdu_in_psdu
                        self.t_msdu_generated[_begin:_end] = np.arange(_begin, _end, 1) * self.msdu_generation_period
                        self.t_msdu_arrival[_begin:_end] = dp.timestamp + dp.duration
                        # for msdu_sub_idx in range(num_of_msdu_in_psdu):
                        #     abs_idx = msdu_idx*num_of_msdu_in_psdu + msdu_sub_idx
                        #     self.t_msdu_generated[abs_idx] = (abs_idx) * self.msdu_generation_period
                        #     self.t_msdu_arrival[abs_idx] = dp.timestamp + dp.duration
                    msdu_idx += 1

        msdu_latency = self.t_msdu_arrival - self.t_msdu_generated
        _min = msdu_latency.min()
        if _min < 0: self.t_msdu_generated += _min
        if self.enable_cts:
            self.t_msdu_generated -= (self.dg.get_cts_duration() + SIFS_NS)
        self.t_msdu_generated -= self.dg.get_data_ppdu_duration()
        # self.t_msdu_generated -= ( self.dg.get_data_ppdu_duration() + int(self.enable_cts)*(self.dg.get_cts_duration() + SIFS_NS) )

        self.msdu_latency_offset = self.t_msdu_arrival - self.t_msdu_generated


    def get_intermediate_data(self):
        intermediate = {
            'bi_duration': self.bi_duration,
            'num_of_observed_bi': self.num_of_observed_bi,
            'mcs': self.mcs,
            'bft_duration': self.dg.get_bft_duration(),
            'num_of_bft_allocations': self.num_of_bft_allocations,
            'num_of_data_allocations': self.num_of_data_allocations,
            'num_of_a_msdu_subframes': self.num_of_a_msdu_subframes,
            'a_msdu_length_bytes': self.a_msdu_length_bytes,
            'mpdu_length_bytes': self.mpdu_length_bytes,
            'num_of_a_mpdu_subframes': self.num_of_a_mpdu_subframes,
            'psdu_length_bytes': self.psdu_length_bytes,
            'cts_duration': self.dg.get_cts_duration(),
            'ack_duration': self.dg.get_ack_duration(),
            'data_ppdu_duration': self.dg.get_data_ppdu_duration(),
            'data_with_overhead_duration': self.dg.get_data_with_overhead_duration(),
            'msdu_generation_period': self.msdu_generation_period
        }
        return intermediate


    def get_raw_channel_timeslots(self):
        return self.ch



class FastInOutStudy(InOutStudy):
    """In-out study focusing only on perf. metric extraction and leveraging Numpy built-in functions where possible."""


    def __init__(self):
        super().__init__()


    def run(self):

        # bft_sp_allocations = np.tile(np.array([2, 1]), int(self.num_of_observed_bi / 2)) * self.num_of_users
        # data_sp_allocations = bft_sp_allocations + 1
        # data_sp_allocations = self.num_of_data_allocations

        self.dg.generate_guard_time_duration(self.bi_duration)

        # Generate the BTI based on number of allocations (15 bytes overhead for each)
        self.dg.generate_bti_duration(self.num_of_data_allocations)

        # Calculate the begin offset for AT in individual BIs (governed by variable BTI duration).
        begin = self.dg.get_bti_duration()
        begin += self.dg.get_guard_time_duration() # Include initial GT
        end = self.bi_duration
        end -= self.dg.get_guard_time_duration() # Include final GT

        # data_sp = np.zeros((data_sp_allocations.sum(), 2))

        # Period between consecutive PSDUs during DATA-SP
        psdu_arrival_period = \
            int(self.enable_cts)*(self.dg.get_cts_duration() + SIFS_NS) + \
            self.dg.get_data_ppdu_duration() + \
            int(self.enable_ack)*(SIFS_NS + self.dg.get_ack_duration()) + \
            DIFS_NS
        # msdu_arrival_period = self.dg.get_data_with_overhead_duration(self.enable_cts, self.enable_ack)

        # First MSDU arrival does not include SIFS+ACK and DIFS
        first_psdu_arrival_offset = \
            int(self.enable_cts) * (self.dg.get_cts_duration() + SIFS_NS) + \
            self.dg.get_data_ppdu_duration()

        # Store relative MSDU arrval times for each unique BI (unique amount of DATA SP allocations)
        t_msdu_arrival_rel = {}

        # Calc MSDU arrival times within BI for each unique number of DATA SP allocations
        for num_of_alloc, unique_idx in zip(*np.unique(self.num_of_data_allocations, return_index=True)):

            # Calc DATA SP timeslots within BI (governed by BFT within the BI)
            inter = np.repeat(np.linspace(begin[unique_idx], end, num_of_alloc, False)[1:], 2)  # Retrieve AT slicing points
            inter += np.resize([-1, 1], inter.size) * self.dg.get_bft_duration() * 0.5  # Chip away BFT duration from AT slices
            inter += np.resize([-1, 1], inter.size) * self.dg.get_guard_time_duration() # Further substract GT duration
            data_sp = np.concatenate((
                [begin[unique_idx]], inter, [end]
            ))  # Re-include AT start and end points
            data_sp.resize(int(data_sp.size / 2), 2)  # Convert to an array of timeslots with a beginning and an end

            num_of_msdu_per_psdu = self.num_of_a_msdu_subframes * self.num_of_a_mpdu_subframes

            # Calc MSDU arrival times within BI (governed by transmission times and number of users)
            t_msdu_arrival = None
            for ds in data_sp:

                first_msdu_arrival = ds[0] + first_psdu_arrival_offset
                last_possible_msdu_arrival = ds[1]

                if self.num_of_users > 1:
                    multi_user_shortening = (ds[1] - ds[0]) * (1 - 1 / self.num_of_users)  # Equally divide the DATA-SP (net, between GIs)
                    multi_user_shortening += self.dg.get_guard_time_duration() / 2 # Subtract half-a-GI, shared with neighbour DATA-SP
                    last_possible_msdu_arrival -= multi_user_shortening # Populate only the remaining time
                    # if last_possible_msdu_arrival < multi_user_shortening:
                    #     raise RuntimeError('Negative DATA-SP duration.')
                    if last_possible_msdu_arrival < first_msdu_arrival:
                        raise RuntimeError('Negative user DATA-SP duration.')

                inter_sp_t_msdu_arrival = np.arange(
                    first_msdu_arrival,
                    last_possible_msdu_arrival,
                    psdu_arrival_period
                )  # Arrival within DATA-SP
                inter_sp_t_msdu_arrival = np.repeat(inter_sp_t_msdu_arrival, num_of_msdu_per_psdu) # Each PSDU may bear multiple MSDUs

                if t_msdu_arrival is None:
                    t_msdu_arrival = inter_sp_t_msdu_arrival
                else:
                    t_msdu_arrival = np.concatenate((t_msdu_arrival, inter_sp_t_msdu_arrival))

            t_msdu_arrival_rel[num_of_alloc] = t_msdu_arrival

        self.t_msdu_arrival = None

        # Generate final MSDU arrival times by adding BI time offset
        for bi_idx, num_of_alloc in enumerate(self.num_of_data_allocations):
            bi_offset = bi_idx * self.bi_duration
            tmp_val = t_msdu_arrival_rel[num_of_alloc] + bi_offset
            if self.t_msdu_arrival is None:
                self.t_msdu_arrival = tmp_val
            else:
                self.t_msdu_arrival = np.concatenate((self.t_msdu_arrival, tmp_val))


    def calc_performance_metrics(self):
        """Calculate and store throughput and MSDU latency."""

        num_of_msdu = self.t_msdu_arrival.size

        self.throughput = num_of_msdu * self.msdu_length_bytes * 8 / (self.bi_duration * self.num_of_observed_bi)

        self.t_msdu_generated = np.linspace( 0, self.bi_duration * self.num_of_observed_bi, num_of_msdu, endpoint=False )

        msdu_latency = self.t_msdu_arrival - self.t_msdu_generated
        _min = msdu_latency.min()
        if _min < 0: self.t_msdu_generated += _min
        if self.enable_cts:
            self.t_msdu_generated -= (self.dg.get_cts_duration() + SIFS_NS)
        self.t_msdu_generated -= self.dg.get_data_ppdu_duration()

        self.msdu_latency_offset = self.t_msdu_arrival - self.t_msdu_generated
