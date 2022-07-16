"""

Time slot definitions.

The working principles are:
 - Each time slot has a unique ID
 - It is defined using a timestamp (start time) and a duration.
 - A time slot may have a parent.
 - Correspondingly, an extended time slot ('ResponsibleTimeslot') may have one or more children (nested time slots).

An independent class is defined for allocating new IDs.

Parent time slots keep track of unoccupied time through the 'AvailableTime' class.

"""


class Timeslot():
    """Universal timeslot with id, name, start time, duration, and potentially parent and children."""

    def __init__(self, id, name, timestamp, duration):
        """Generate new timeslot.

        :param id: Unique identifier.
        :type id: int
        :param name: Timeslot name.
        :type name: str
        :param timestamp: Start time (ns).
        :type timestamp: int
        :param duration: Duration (ns).
        :type duration: int
        """

        self.id = id
        self.name = name
        self.timestamp = timestamp
        self.duration = duration

    def set_parent(self, parent):
        """Set parent slot.
        :param parent: Timeslot's hierarchical parent.
        :type parent: TImeslot object.
        """
        self.parent_id = parent.id


class ResponsibleTimeslot(Timeslot):
    """Timeslot that may have children.

    Features additional property for keeping track of available time.
    """

    def __init__(self, id, name, timestamp, duration):
        """Generate new timeslot, capable of having children.

        :param id: Unique identifier.
        :type id: int
        :param name: Timeslot name.
        :type name: str
        :param timestamp: Start time (ns).
        :type timestamp: int
        :param duration: Duration (ns).
        :type duration: int
        """

        super().__init__(id, name, timestamp, duration)
        self.at = AvailableTime(timestamp, timestamp + duration)
        self.children = []

    def add_children(self, children):
        """Add multiple children.
        :param children: Timeslots.
        :type children: list of Timeslot objects
        """
        for child in children: self.add_child(child)

    def add_child(self, child):
        """Add child timeslot.
        :param child: Orphan timeslot.
        :type child: Timeslot object
        """
        self.at.allocate_available_time(child.timestamp, child.timestamp + child.duration)
        self.children.append(child)
        child.set_parent(self)

    def get_list_of_children(self):
        """Get child timeslots.
        :return: List of children.
        :rtype: List of Timeslot objects
        """
        return self.children

    def get_available_time(self):
        """Get available time slots (unoccupied).
        :return: Available time slots.
        :rtype: List containing start-stop (ns) tuples or single tuple
        """
        times = self.at.get_available_time()
        # if len(times) == 1: return times[0]
        return times.copy()


class AvailableTime():
    """Object for keeping track of available time slots in ResponsibleTimeslot objects."""

    def __init__(self, t_start, t_end):
        """Generate new available time.
        :param t_start: Start time (ns).
        :type t_start: int
        :param t_end: Stop time (ns).
        :type t_end: int
        """
        self.available_time = [(t_start, t_end)]

    def get_available_time(self):
        """Get the available times.
        :return: Available time slots.
        :rtype: List containing start-stop (ns)
        """
        return self.available_time

    def allocate_available_time(self, t_start, t_end):
        """Occupy given amount of time.

        :param t_start: Start time to occupy (ns).
        :type t_start: int
        :param t_end: Stop time to occupy (ns).
        :type t_end: int
        """

        idx = self.get_available_time_idx(t_start, t_end) # Get index and check if a corresponding time slot is available

        # Occupies entire available time slot
        if t_start == self.available_time[idx][0] and t_end == self.available_time[idx][1]:
            self.available_time.pop(idx)
            return
        # Starts at the beginning of the available time slot
        elif t_start == self.available_time[idx][0]:
            self.available_time[idx] = (t_end, self.available_time[idx][1])
            return
        # Stops at the end of the available time slot
        elif t_end == self.available_time[idx][1]:
            self.available_time[idx] = (self.available_time[idx][0], t_start)
            return
        # None of the above: nested somewhere in the middle of the available time slot
        update = [(self.available_time[idx][0], t_start), (t_end, self.available_time[idx][1])]
        # self.available_time = self.available_time[:idx - 1] + update + self.available_time[idx+1:]
        self.available_time = self.available_time[:idx] + update + self.available_time[idx+1:]

    def get_available_time_idx(self, t_start, t_end):
        """Get the available time slot index, based on the time that will be occupied.

        :param t_start: Start time to occupy (ns).
        :type t_start: int
        :param t_end: Stop time to occupy (ns).
        :type t_end: int
        :return: Available time slot index.
        :rtype: int
        """

        for at_idx, at in enumerate(self.available_time):
            check = (t_start >= at[0] and t_start <= at[1], t_end >= at[0] and t_end <= at[1])
            if check[0] and check[1]:  # Nested within available time
                # self.split_available_time(at_idx, t_start, t_end)
                return at_idx
            elif check[0] or check[1]: # Only partially overlaps with available time slot
                raise RuntimeError('Tried fitting overlapping timeslot')
            # Continue looking if NAND
        raise RuntimeError('Insufficient time') # Did not find available time slot


class TimeslotIdGenerator():
    """Keeps tract of timeslot IDs and generates new ones."""

    def __init__(self):
        self.id_counter = 0

    def get_new_id(self):
        """Generate new ID.
        :return: Unique ID.
        :rtype: int
        """
        tmp_id_counter = self.id_counter
        self.id_counter += 1
        return tmp_id_counter

