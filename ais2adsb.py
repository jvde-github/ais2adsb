#!/usr/bin/python3

# Copyright (c) 2023-2026 jvde.github@gmail.com and jonboy1081

import argparse
import ast
import os
import signal
import socket
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import aiscat


VERSION = "0.15"
DEFAULT_ICAO_MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "icao_map.dict")
STALE_AFTER_SECONDS = 300

ICAOmap: dict[int, int] = {}

state = {
    "udp_received": 0,
    "decoded": 0,
    "sent": 0,
    "reconnects": 0,
    "last_recv_ts": 0.0,
    "last_send_ts": 0.0,
    "connected": False,
}

client_socket: socket.socket | None = None


def generateICAO(mmsi: int) -> int:
    if mmsi not in ICAOmap:
        proposedICAO = 0xF00000 | (mmsi & 0xFFFFF)
        print(f'New mmsi: {mmsi}, generated ICAO: {"%X" % proposedICAO}', file=sys.stderr)
        if proposedICAO in ICAOmap.values():
            while True:
                print(f'ICAO occupied, skipping to next', file=sys.stderr)
                proposedICAO = (proposedICAO + 1) & 0xFFFFFF
                if proposedICAO not in ICAOmap.values():
                    break
        ICAOmap[mmsi] = proposedICAO
    return ICAOmap[mmsi]


def loadMMSIdict(path: str) -> None:
    print(f'Reading MMSI->ICAO mapping from "{path}"', file=sys.stderr)
    try:
        with open(path) as f:
            d = ast.literal_eval(f.read())
        for key in d:
            if key in ICAOmap and ICAOmap[key] != d[key]:
                print(f'\tWarning: overwrite {key} -> {"%X" % ICAOmap[key]}', file=sys.stderr)
            ICAOmap[key] = d[key]
    except FileNotFoundError:
        print(f'\tWarning: file "{path}" not found.', file=sys.stderr)


def printDictionary(filename: str | None = None) -> None:
    output_stream = sys.stderr
    if filename is not None:
        output_stream = open(filename, "w")
        print("\tWriting to file", file=sys.stderr)

    print("{", end="", file=output_stream)
    for i, key in enumerate(ICAOmap):
        if i:
            print(",", end="", file=output_stream)
        print(f"{key}:0x{'%X' % ICAOmap[key]}", end="", file=output_stream)
    print("}", file=output_stream)

    if filename is not None:
        output_stream.close()


def alt_meters_to_feet(alt_m) -> int | None:
    """AIS type 9 altitude is metres (0..4094, 4095 = not available).
    SBS BaseStation wants altitude in feet."""
    if alt_m is None or alt_m == 4095:
        return None
    return round(alt_m * 3.28084)


def connectClient(server_ip: str, server_port: int) -> socket.socket:
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((server_ip, server_port))
            state["connected"] = True
            state["reconnects"] += 1
            print("Status: Connected to ADSB server", file=sys.stderr)
            return sock
        except (socket.error, OSError) as e:
            print(f"Error: failed to connect to server: {e}", file=sys.stderr)
            time.sleep(10)


def sendBaseStation(decoded: dict, settings: dict) -> None:
    global client_socket

    lat = decoded.get("lat")
    lon = decoded.get("lon")
    speed = decoded.get("speed")
    heading = decoded.get("course")

    if not (lat is not None and lon is not None and speed is not None and heading is not None
            and -90 <= lat <= 90 and -180 <= lon <= 180):
        return

    alt_ft = alt_meters_to_feet(decoded.get("alt"))
    ground_flag = 0 if alt_ft and alt_ft >= 1 else 1
    alt_str = str(alt_ft) if alt_ft and alt_ft >= 1 else ""

    ICAO = "%X" % generateICAO(decoded["mmsi"])
    now_utc = datetime.now()
    dstr = now_utc.strftime("%Y/%m/%d")
    tstr = now_utc.strftime("%H:%M:%S.%f")[:-3]
    callsign = "V:" + ("00000" + str(decoded["mmsi"]))[-6:]

    spos = f"MSG,2,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},,{alt_str},{speed},{heading},{lat},{lon},,,,,,{ground_flag}\n"
    scs = f"MSG,1,1,0,{ICAO},1,{dstr},{tstr},{dstr},{tstr},{callsign},,,,,,,,,,,\n"

    if client_socket is None:
        print(spos, end="")
        print(scs, end="")
        return

    try:
        client_socket.send(spos.encode())
        if settings["callsign"]:
            client_socket.send(scs.encode())
        state["sent"] += 1
        state["last_send_ts"] = time.time()
    except (socket.error, OSError):
        print("Connection lost. Reconnecting...", file=sys.stderr)
        client_socket.close()
        state["connected"] = False
        client_socket = connectClient(settings["sbs_ip"], settings["sbs_port"])


def shouldForward(decoded: dict, settings: dict) -> bool:
    if "type" not in decoded:
        return False
    is_sar = decoded["type"] == 9 or decoded["mmsi"] in ICAOmap
    if is_sar and settings["sar"]:
        return True
    if decoded["type"] != 9 and settings["ships"]:
        return True
    return False


# ---------------------------------------------------------------- metrics ----

class _MetricsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # silence access logs
        pass

    def do_GET(self):
        if self.path == "/health":
            stale = time.time() - state["last_recv_ts"] > STALE_AFTER_SECONDS
            ok = state["connected"] and not stale and state["last_recv_ts"] > 0
            self.send_response(200 if ok else 503)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok\n" if ok else b"degraded\n")
            return
        if self.path == "/metrics":
            body = (
                "# TYPE ais2adsb_messages_received_total counter\n"
                f"ais2adsb_messages_received_total {state['udp_received']}\n"
                "# TYPE ais2adsb_messages_decoded_total counter\n"
                f"ais2adsb_messages_decoded_total {state['decoded']}\n"
                "# TYPE ais2adsb_messages_sent_total counter\n"
                f"ais2adsb_messages_sent_total {state['sent']}\n"
                "# TYPE ais2adsb_tcp_reconnects_total counter\n"
                f"ais2adsb_tcp_reconnects_total {state['reconnects']}\n"
                "# TYPE ais2adsb_last_message_timestamp_seconds gauge\n"
                f"ais2adsb_last_message_timestamp_seconds {state['last_recv_ts']}\n"
                "# TYPE ais2adsb_last_send_timestamp_seconds gauge\n"
                f"ais2adsb_last_send_timestamp_seconds {state['last_send_ts']}\n"
                "# TYPE ais2adsb_unique_icaos gauge\n"
                f"ais2adsb_unique_icaos {len(ICAOmap)}\n"
                "# TYPE ais2adsb_connected gauge\n"
                f"ais2adsb_connected {1 if state['connected'] else 0}\n"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(body.encode())
            return
        self.send_response(404); self.end_headers()


def startMetricsServer(port: int) -> None:
    httpd = HTTPServer(("0.0.0.0", port), _MetricsHandler)
    t = threading.Thread(target=httpd.serve_forever, name="metrics", daemon=True)
    t.start()
    print(f"Metrics server listening on :{port} (/metrics, /health)", file=sys.stderr)


# ---------------------------------------------------------------- cli/main ----

def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="ais2adsb",
        description="Convert AIS NMEA (UDP) to BaseStation SBS (TCP) for ADS-B viewers.",
    )
    p.add_argument("udp_ip")
    p.add_argument("udp_port", type=int)
    p.add_argument("sbs_ip")
    p.add_argument("sbs_port", type=int)
    p.add_argument("--sar", action=argparse.BooleanOptionalAction, default=True,
                   help="forward SAR aircraft (type 9 + known MMSIs in mapping)")
    p.add_argument("--ships", action=argparse.BooleanOptionalAction, default=False,
                   help="forward ship positions")
    p.add_argument("--callsign", action=argparse.BooleanOptionalAction, default=True,
                   help="emit MSG,1 callsign records")
    p.add_argument("--print-dict", action="store_true",
                   help="periodically dump MMSI->ICAO map to stderr")
    p.add_argument("--map-file", help="load MMSI->ICAO map from file")
    p.add_argument("--save-file", help="save MMSI->ICAO map to file periodically and on exit")
    p.add_argument("--metrics-port", type=int,
                   help="expose Prometheus /metrics and /health on this port")
    p.add_argument("--no-default-map", action="store_true",
                   help="do not preload the bundled default ICAO map")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parseArgs(argv)
    print(f"AIS2ADSB v{VERSION} — see https://github.com/jvde-github/ais2adsb", file=sys.stderr)

    settings = {
        "sbs_ip": args.sbs_ip,
        "sbs_port": args.sbs_port,
        "sar": args.sar,
        "ships": args.ships,
        "callsign": args.callsign,
        "save_file": args.save_file,
        "print_dict": args.print_dict,
    }

    if not args.no_default_map and os.path.exists(DEFAULT_ICAO_MAP_PATH):
        loadMMSIdict(DEFAULT_ICAO_MAP_PATH)
    if args.map_file:
        loadMMSIdict(args.map_file)

    print(f"Input AIS        : {args.udp_ip}:{args.udp_port}", file=sys.stderr)
    print(f"Output SBS       : {args.sbs_ip}:{args.sbs_port}", file=sys.stderr)
    print(f"Include SAR      : {args.sar}", file=sys.stderr)
    print(f"Include ships    : {args.ships}", file=sys.stderr)
    print(f"Include callsign : {args.callsign}", file=sys.stderr)
    print(f"Print dictionary : {args.print_dict}", file=sys.stderr)
    print(f"Save dictionary  : {args.save_file}", file=sys.stderr)
    print(f"ICAO entries     : {len(ICAOmap)}", file=sys.stderr)

    def _shutdown(sig, frame):
        print(f"Signal {sig} received, exiting", file=sys.stderr)
        if args.print_dict or args.save_file:
            printDictionary(args.save_file)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    if args.metrics_port:
        startMetricsServer(args.metrics_port)

    global client_socket
    client_socket = connectClient(args.sbs_ip, args.sbs_port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.udp_ip, args.udp_port))

    decoder = aiscat.Decoder()
    next_update_time = time.monotonic() + 30 * 60
    interval_count = 0
    interval_sent = 0

    while True:
        data, _ = sock.recvfrom(2048)
        state["udp_received"] += 1
        state["last_recv_ts"] = time.time()
        decoder.feed(data)

        while (decoded := decoder.next()) is not None:
            state["decoded"] += 1
            if shouldForward(decoded, settings):
                before = state["sent"]
                sendBaseStation(decoded, settings)
                interval_count += 1
                interval_sent += state["sent"] - before

        if time.monotonic() >= next_update_time:
            t = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{t} Messages sent: {interval_sent}/{interval_count}", file=sys.stderr)
            if args.print_dict:
                printDictionary()
            if args.save_file:
                printDictionary(args.save_file)
            interval_count = 0
            interval_sent = 0
            next_update_time += 30 * 60


if __name__ == "__main__":
    sys.exit(main())
