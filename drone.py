from dronekit import connect
import time
import logging
from collections import defaultdict

# so we can pickle default dict
# http://stackoverflow.com/questions/16439301/cant-pickle-defaultdict
def dd():
    return 0

class Drone:
    def __init__(self):
        self.url = "127.0.0.1:14550"
        self.cur_location = 0,0,0
        self.cur_attitude = 0,0,0
        self.cur_grpsinfo = 0,0,0,0
        self.cur_groundspeed = 0
        self.vehicle = None

        self._state = defaultdict(dd)
        self.log = logging.getLogger(__name__)


    def setup(self):

        self.log.info("Connecting to vehicle on: %s" % self.url)

        self.vehicle = connect(self.url,  wait_ready=True)
        self.vehicle.add_attribute_listener("location.global_frame", self._location_listener)
        self.vehicle.add_attribute_listener("location.global_relative_frame", self._location_listener)
        self.vehicle.add_attribute_listener("groundspeed", self._simple_listener)
        self.vehicle.add_attribute_listener("heading", self._simple_listener)
        self.vehicle.add_attribute_listener("attitude", self._attitude_listener)
        self.vehicle.add_attribute_listener("gps_0", self._gps_listener)

        if self.vehicle.mode.name == "INITIALISING":
            self.log.info("Waiting for vehicle to initialise")
            time.sleep(1)

        self.log.info("Accumulating vehicle attribute messages")

        while self.vehicle.attitude.pitch is None:
            # Attitude is fairly quick to propagate
            self.log.debug("...")
            time.sleep(1)

    def _location_listener(self, vehicle, attr_name, value):
        self._state["lat"] = value.lat
        self._state["lon"] = value.lon

        if attr_name == "location.global_relative_frame":
            self._state["relalt"] = value.alt
        else:
            self._state["alt"] = value.alt

    def _simple_listener(self, vehicle, attr_name, value):
        self._state[attr_name] = value

    def _gps_listener(self, vehicle, attr_name, value):
        if attr_name == "satellites_visible":
            an = "nsat"
        else:
            an = attr_name

        self._state["nsat"] = value.satellites_visible
        self._state["eph"] = value.eph
        self._state["epv"] = value.epv
        self._state["fix_type"] = value.fix_type

    def _attitude_listener(self, vehicle, attr_name, value):
        self._state["pitch"] = value.pitch
        self._state["roll"] = value.roll
        self._state["yaw"] = value.yaw

    def get_position(self):
        return self._state

    def print_state(self):
        for k, v in self._state.iteritems():
            print k, ": ", v

if __name__ == "__main__":
    d = Drone()
    d.setup()

    while True:
        d.print_state()
        time.sleep(4)

