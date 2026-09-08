import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ais2adsb  # noqa: E402


class AltConversionTests(unittest.TestCase):
    def test_none_returns_none(self):
        self.assertIsNone(ais2adsb.alt_meters_to_feet(None))

    def test_sentinel_4095_returns_none(self):
        self.assertIsNone(ais2adsb.alt_meters_to_feet(4095))

    def test_zero_metres_is_zero_feet(self):
        self.assertEqual(ais2adsb.alt_meters_to_feet(0), 0)

    def test_500m_to_feet(self):
        # 500 m * 3.28084 = 1640.42 -> rounded to 1640
        self.assertEqual(ais2adsb.alt_meters_to_feet(500), 1640)


class ICAOGenerationTests(unittest.TestCase):
    def setUp(self):
        ais2adsb.ICAOmap.clear()

    def test_generated_icao_in_F_range(self):
        icao = ais2adsb.generateICAO(244012345)
        self.assertEqual(icao & 0xF00000, 0xF00000)
        self.assertLessEqual(icao, 0xFFFFFF)

    def test_existing_mapping_preserved(self):
        ais2adsb.ICAOmap[111232512] = 0x406C79
        self.assertEqual(ais2adsb.generateICAO(111232512), 0x406C79)

    def test_collision_skipped(self):
        # Pre-occupy the ICAO that mmsi=1 would normally get
        proposed = 0xF00000 | (1 & 0xFFFFF)
        ais2adsb.ICAOmap[999999999] = proposed
        new_icao = ais2adsb.generateICAO(1)
        self.assertNotEqual(new_icao, proposed)


class FilterTests(unittest.TestCase):
    def setUp(self):
        ais2adsb.ICAOmap.clear()

    def _settings(self, sar=True, ships=False):
        return {"sar": sar, "ships": ships, "callsign": True,
                "sbs_ip": "x", "sbs_port": 0, "save_file": None, "print_dict": False}

    def test_empty_payload_is_not_forwarded(self):
        decoder = ais2adsb.aiscat.Decoder()
        decoder.feed(b"!AIVDM,1,1,,A,,0*26\r\n")
        decoded = decoder.next()
        # Newer decoders may reject the empty payload before it reaches us.
        if decoded is not None:
            for sar in (False, True):
                for ships in (False, True):
                    with self.subTest(sar=sar, ships=ships):
                        self.assertFalse(ais2adsb.shouldForward(
                            decoded, self._settings(sar=sar, ships=ships)))

    def test_missing_type_is_not_forwarded_even_for_known_mmsi(self):
        ais2adsb.ICAOmap[42] = 0x123456
        self.assertFalse(ais2adsb.shouldForward(
            {"mmsi": 42}, self._settings(sar=True, ships=True)))

    def test_sar_passes_when_sar_on(self):
        self.assertTrue(ais2adsb.shouldForward({"type": 9, "mmsi": 1}, self._settings()))

    def test_ship_blocked_by_default(self):
        self.assertFalse(ais2adsb.shouldForward({"type": 1, "mmsi": 1}, self._settings()))

    def test_ship_passes_when_ships_on(self):
        self.assertTrue(ais2adsb.shouldForward({"type": 1, "mmsi": 1},
                                                self._settings(ships=True)))

    def test_known_mmsi_treated_as_sar(self):
        ais2adsb.ICAOmap[42] = 0x123456
        self.assertTrue(ais2adsb.shouldForward({"type": 1, "mmsi": 42}, self._settings()))


class CLIParseTests(unittest.TestCase):
    def test_minimal(self):
        a = ais2adsb.parseArgs(["1.2.3.4", "4002", "5.6.7.8", "30003"])
        self.assertEqual(a.udp_ip, "1.2.3.4")
        self.assertEqual(a.udp_port, 4002)
        self.assertTrue(a.sar)
        self.assertFalse(a.ships)
        self.assertTrue(a.callsign)

    def test_no_sar_disables(self):
        a = ais2adsb.parseArgs(["1.2.3.4", "4002", "5.6.7.8", "30003", "--no-sar", "--ships"])
        self.assertFalse(a.sar)
        self.assertTrue(a.ships)

    def test_metrics_port(self):
        a = ais2adsb.parseArgs(["1.2.3.4", "4002", "5.6.7.8", "30003", "--metrics-port", "8080"])
        self.assertEqual(a.metrics_port, 8080)


class SendBaseStationTests(unittest.TestCase):
    def setUp(self):
        ais2adsb.ICAOmap.clear()
        ais2adsb.client_socket = None
        ais2adsb.state["sent"] = 0

    def _settings(self):
        return {"sar": True, "ships": True, "callsign": True,
                "sbs_ip": "x", "sbs_port": 0, "save_file": None, "print_dict": False}

    def test_rejects_lat_sentinel(self):
        msg = {"type": 1, "mmsi": 1, "lat": 91.0, "lon": 0.0, "speed": 1.0, "course": 0.0}
        ais2adsb.sendBaseStation(msg, self._settings())
        self.assertEqual(ais2adsb.state["sent"], 0)

    def test_rejects_speed_none(self):
        msg = {"type": 1, "mmsi": 1, "lat": 0.0, "lon": 0.0, "speed": None, "course": 0.0}
        ais2adsb.sendBaseStation(msg, self._settings())
        self.assertEqual(ais2adsb.state["sent"], 0)


if __name__ == "__main__":
    unittest.main()
