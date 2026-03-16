#!/usr/bin/env python
"""
OCPP 1.6-J Charger Simulator
=============================
A standalone tool that simulates a real EV charger connecting to your
OCPP management server over WebSocket. It walks through the full
charging lifecycle so you can verify everything works end-to-end.

Requirements:
    pip install websockets

Usage:
    python tools/charger_simulator.py                          # defaults
    python tools/charger_simulator.py --id MY-CP-01            # custom charger ID
    python tools/charger_simulator.py --host 192.168.1.10      # remote server
    python tools/charger_simulator.py --tag ABCD1234           # custom RFID tag
    python tools/charger_simulator.py --energy 5000            # deliver 5 kWh
    python tools/charger_simulator.py --interval 3             # meter every 3s
    python tools/charger_simulator.py --meter-steps 10         # 10 meter readings

Before running:
    1. Start the Django server:  python manage.py runserver
    2. Seed test data:           python manage.py setup_test_data
"""

import argparse
import asyncio
import json
import sys
import time
import uuid
from datetime import datetime, timezone


# ─── OCPP Message Types ─────────────────────────────────────────────
CALL = 2
CALL_RESULT = 3
CALL_ERROR = 4

# ─── Colors for terminal output ─────────────────────────────────────
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'


def log_send(action, payload):
    print(f'{CYAN}  >>> SEND  {action}{RESET}')
    for k, v in payload.items():
        print(f'          {k}: {v}')


def log_recv(msg_type, payload, error_code=None):
    if msg_type == CALL_RESULT:
        print(f'{GREEN}  <<< RECV  CallResult{RESET}')
        if isinstance(payload, dict):
            for k, v in payload.items():
                print(f'          {k}: {v}')
    elif msg_type == CALL_ERROR:
        print(f'{RED}  <<< RECV  CallError: {error_code}{RESET}')
        print(f'          {payload}')


def log_step(step, description):
    print(f'\n{BOLD}{YELLOW}[Step {step}]{RESET} {BOLD}{description}{RESET}')


def log_result(success, message):
    if success:
        print(f'  {GREEN}PASS{RESET} {message}')
    else:
        print(f'  {RED}FAIL{RESET} {message}')


class ChargerSimulator:
    """Simulates an OCPP 1.6-J charge point."""

    def __init__(self, ws, charge_point_id, id_tag, connector_id,
                 total_energy_wh, meter_steps, meter_interval):
        self.ws = ws
        self.charge_point_id = charge_point_id
        self.id_tag = id_tag
        self.connector_id = connector_id
        self.total_energy_wh = total_energy_wh
        self.meter_steps = meter_steps
        self.meter_interval = meter_interval
        self.transaction_id = None
        self.meter_start = 1000  # starting meter value in Wh
        self.results = []

    async def send_call(self, action, payload):
        """Send an OCPP CALL message and wait for the response."""
        unique_id = str(uuid.uuid4())[:8]
        message = [CALL, unique_id, action, payload]

        log_send(action, payload)
        await self.ws.send(json.dumps(message))

        # Wait for response
        raw = await asyncio.wait_for(self.ws.recv(), timeout=10)
        response = json.loads(raw)

        msg_type = response[0]
        resp_uid = response[1]

        if msg_type == CALL_RESULT:
            result_payload = response[2]
            log_recv(CALL_RESULT, result_payload)
            return True, result_payload
        elif msg_type == CALL_ERROR:
            error_code = response[2]
            error_desc = response[3] if len(response) > 3 else ''
            log_recv(CALL_ERROR, error_desc, error_code)
            return False, {'errorCode': error_code, 'errorDescription': error_desc}
        else:
            return False, {'error': 'Unexpected response type'}

    def now_iso(self):
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')

    async def step_boot_notification(self):
        log_step(1, 'BootNotification')

        ok, result = await self.send_call('BootNotification', {
            'chargePointVendor': 'SETEC',
            'chargePointModel': 'Power 60kW',
            'chargePointSerialNumber': 'SIM-SN-001',
            'firmwareVersion': '1.0.0-sim',
        })

        status = result.get('status', '')
        success = ok and status == 'Accepted'
        log_result(success, f'BootNotification status: {status}')
        self.results.append(('BootNotification', success))

        if not success:
            print(f'\n{RED}  Charger was rejected. Make sure "{self.charge_point_id}" '
                  f'is registered or OCPP_ACCEPT_UNKNOWN_CHARGERS=True{RESET}')
        return success

    async def step_heartbeat(self):
        log_step(2, 'Heartbeat')

        ok, result = await self.send_call('Heartbeat', {})

        has_time = ok and 'currentTime' in result
        log_result(has_time, f'Server time: {result.get("currentTime", "N/A")}')
        self.results.append(('Heartbeat', has_time))
        return has_time

    async def step_status_notification(self, status='Available'):
        log_step(3, f'StatusNotification (connector {self.connector_id} -> {status})')

        ok, result = await self.send_call('StatusNotification', {
            'connectorId': self.connector_id,
            'errorCode': 'NoError',
            'status': status,
            'timestamp': self.now_iso(),
        })

        log_result(ok, f'StatusNotification accepted')
        self.results.append(('StatusNotification', ok))
        return ok

    async def step_authorize(self):
        log_step(4, f'Authorize (idTag: {self.id_tag})')

        ok, result = await self.send_call('Authorize', {
            'idTag': self.id_tag,
        })

        status = result.get('idTagInfo', {}).get('status', 'Unknown')
        success = ok and status == 'Accepted'
        log_result(success, f'Authorization status: {status}')
        self.results.append(('Authorize', success))

        if not success:
            print(f'\n{RED}  RFID tag "{self.id_tag}" was not accepted.')
            print(f'  Check: card exists, is Active, assigned to a customer, customer is active,')
            print(f'  wallet has sufficient balance.{RESET}')
        return success

    async def step_start_transaction(self):
        log_step(5, f'StartTransaction (connector {self.connector_id}, meter={self.meter_start} Wh)')

        # First set connector to Preparing
        await self.send_call('StatusNotification', {
            'connectorId': self.connector_id,
            'errorCode': 'NoError',
            'status': 'Preparing',
            'timestamp': self.now_iso(),
        })

        ok, result = await self.send_call('StartTransaction', {
            'connectorId': self.connector_id,
            'idTag': self.id_tag,
            'meterStart': self.meter_start,
            'timestamp': self.now_iso(),
        })

        status = result.get('idTagInfo', {}).get('status', 'Unknown')
        self.transaction_id = result.get('transactionId')
        success = ok and status == 'Accepted' and self.transaction_id is not None

        log_result(success, f'Transaction ID: {self.transaction_id}, status: {status}')
        self.results.append(('StartTransaction', success))

        if success:
            # Set connector to Charging
            await self.send_call('StatusNotification', {
                'connectorId': self.connector_id,
                'errorCode': 'NoError',
                'status': 'Charging',
                'timestamp': self.now_iso(),
            })

        return success

    async def step_meter_values(self):
        log_step(6, f'MeterValues ({self.meter_steps} readings, '
                    f'{self.total_energy_wh} Wh total, '
                    f'every {self.meter_interval}s)')

        energy_per_step = self.total_energy_wh // self.meter_steps
        current_meter = self.meter_start

        for i in range(1, self.meter_steps + 1):
            current_meter += energy_per_step

            ok, result = await self.send_call('MeterValues', {
                'connectorId': self.connector_id,
                'transactionId': self.transaction_id,
                'meterValue': [{
                    'timestamp': self.now_iso(),
                    'sampledValue': [
                        {
                            'value': str(current_meter),
                            'measurand': 'Energy.Active.Import.Register',
                            'unit': 'Wh',
                            'context': 'Sample.Periodic',
                            'location': 'Outlet',
                        },
                        {
                            'value': str(30 + (i % 5) * 2),  # simulated power kW
                            'measurand': 'Power.Active.Import',
                            'unit': 'kW',
                            'context': 'Sample.Periodic',
                            'location': 'Outlet',
                        },
                    ],
                }],
            })

            energy_so_far = current_meter - self.meter_start
            print(f'          Reading {i}/{self.meter_steps}: '
                  f'{current_meter} Wh (delivered: {energy_so_far} Wh = '
                  f'{energy_so_far / 1000:.1f} kWh)')

            if i < self.meter_steps:
                await asyncio.sleep(self.meter_interval)

        log_result(True, f'Sent {self.meter_steps} meter readings')
        self.results.append(('MeterValues', True))
        self.final_meter = current_meter
        return True

    async def step_stop_transaction(self):
        log_step(7, f'StopTransaction (meter={self.final_meter} Wh)')

        # Set connector to Finishing
        await self.send_call('StatusNotification', {
            'connectorId': self.connector_id,
            'errorCode': 'NoError',
            'status': 'Finishing',
            'timestamp': self.now_iso(),
        })

        total_energy = self.final_meter - self.meter_start

        ok, result = await self.send_call('StopTransaction', {
            'transactionId': self.transaction_id,
            'meterStop': self.final_meter,
            'timestamp': self.now_iso(),
            'idTag': self.id_tag,
            'reason': 'Local',
            'transactionData': [{
                'timestamp': self.now_iso(),
                'sampledValue': [{
                    'value': str(self.final_meter),
                    'measurand': 'Energy.Active.Import.Register',
                    'unit': 'Wh',
                    'context': 'Transaction.End',
                }],
            }],
        })

        log_result(ok, f'Session stopped. Energy delivered: {total_energy} Wh '
                       f'({total_energy / 1000:.3f} kWh)')
        self.results.append(('StopTransaction', ok))

        # Set connector back to Available
        await self.send_call('StatusNotification', {
            'connectorId': self.connector_id,
            'errorCode': 'NoError',
            'status': 'Available',
            'timestamp': self.now_iso(),
        })

        return ok

    def print_summary(self):
        total_energy = self.total_energy_wh
        print(f'\n{BOLD}{"=" * 60}{RESET}')
        print(f'{BOLD}  SIMULATION SUMMARY{RESET}')
        print(f'{BOLD}{"=" * 60}{RESET}')
        print(f'  Charge Point    : {self.charge_point_id}')
        print(f'  RFID Tag        : {self.id_tag}')
        print(f'  Transaction ID  : {self.transaction_id}')
        print(f'  Energy Delivered: {total_energy} Wh ({total_energy / 1000:.3f} kWh)')
        print(f'  Meter Readings  : {self.meter_steps}')
        print()

        all_passed = True
        for name, passed in self.results:
            icon = f'{GREEN}PASS{RESET}' if passed else f'{RED}FAIL{RESET}'
            print(f'  [{icon}] {name}')
            if not passed:
                all_passed = False

        print()
        if all_passed:
            print(f'  {GREEN}{BOLD}ALL TESTS PASSED{RESET}')
            print()
            print(f'  Now check your dashboard:')
            print(f'    - http://127.0.0.1:8000/          (Dashboard with KPIs)')
            print(f'    - http://127.0.0.1:8000/sessions/  (Session list)')
            print(f'    - http://127.0.0.1:8000/chargers/  (Charger should be Online)')
        else:
            print(f'  {RED}{BOLD}SOME TESTS FAILED{RESET} - check the output above')
        print()


async def run_simulation(args):
    url = f'ws://{args.host}:{args.port}/ws/ocpp/{args.id}/'

    print(f'\n{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  OCPP 1.6-J Charger Simulator{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}')
    print(f'  Server    : {url}')
    print(f'  Charger ID: {args.id}')
    print(f'  RFID Tag  : {args.tag}')
    print(f'  Connector : {args.connector}')
    print(f'  Energy    : {args.energy} Wh ({args.energy / 1000:.1f} kWh)')
    print(f'  Steps     : {args.meter_steps} readings every {args.interval}s')

    try:
        import websockets
    except ImportError:
        print(f'\n{RED}  ERROR: websockets package not installed.{RESET}')
        print(f'  Run: pip install websockets')
        sys.exit(1)

    try:
        print(f'\n  Connecting to {url} ...')
        async with websockets.connect(
            url,
            subprotocols=['ocpp1.6'],
            open_timeout=10,
        ) as ws:
            print(f'  {GREEN}Connected!{RESET} (subprotocol: {ws.subprotocol})')

            sim = ChargerSimulator(
                ws=ws,
                charge_point_id=args.id,
                id_tag=args.tag,
                connector_id=args.connector,
                total_energy_wh=args.energy,
                meter_steps=args.meter_steps,
                meter_interval=args.interval,
            )

            # Run the full charge cycle
            if not await sim.step_boot_notification():
                sim.print_summary()
                return

            await sim.step_heartbeat()
            await sim.step_status_notification('Available')

            if not await sim.step_authorize():
                sim.print_summary()
                return

            if not await sim.step_start_transaction():
                sim.print_summary()
                return

            await sim.step_meter_values()
            await sim.step_stop_transaction()
            sim.print_summary()

    except ConnectionRefusedError:
        print(f'\n{RED}  ERROR: Connection refused at {url}{RESET}')
        print(f'  Make sure the server is running: python manage.py runserver')
    except asyncio.TimeoutError:
        print(f'\n{RED}  ERROR: Connection timed out{RESET}')
        print(f'  Check that the server is running and the URL is correct.')
    except Exception as e:
        print(f'\n{RED}  ERROR: {type(e).__name__}: {e}{RESET}')


def main():
    parser = argparse.ArgumentParser(
        description='OCPP 1.6-J Charger Simulator - tests your OCPP management server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/charger_simulator.py                         # run with defaults
  python tools/charger_simulator.py --id MY-CHARGER-01      # custom charger ID
  python tools/charger_simulator.py --tag MYCARD123         # custom RFID tag
  python tools/charger_simulator.py --energy 10000          # deliver 10 kWh
  python tools/charger_simulator.py --meter-steps 20 --interval 1

Before running:
  1.  python manage.py runserver          (start the server)
  2.  python manage.py setup_test_data    (create test charger/customer/card)
        """,
    )
    parser.add_argument('--host', default='127.0.0.1', help='Server host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8000, help='Server port (default: 8000)')
    parser.add_argument('--id', default='SIM-CHARGER-001', help='Charge Point ID (default: SIM-CHARGER-001)')
    parser.add_argument('--tag', default='TEST0001', help='RFID idTag to use (default: TEST0001)')
    parser.add_argument('--connector', type=int, default=1, help='Connector ID (default: 1)')
    parser.add_argument('--energy', type=int, default=3000, help='Total energy to deliver in Wh (default: 3000 = 3 kWh)')
    parser.add_argument('--meter-steps', type=int, default=5, help='Number of MeterValues readings (default: 5)')
    parser.add_argument('--interval', type=float, default=2, help='Seconds between MeterValues (default: 2)')

    args = parser.parse_args()
    asyncio.run(run_simulation(args))


if __name__ == '__main__':
    main()
