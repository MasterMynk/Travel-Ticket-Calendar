# TODO: Add a flag to dyanmically set location of token.json file
# TODO: Remove the need for credentials.json file. Store the data in this python script itself

import os.path
import sys
from datetime import datetime, timedelta
from collections.abc import Callable
from typing import TypeVar, NoReturn, Self
from functools import reduce

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar']

ARRIVAL_DEPARTURE_VAL_ERR_MSG = '''
--{0} value specified incorrectly.
Correct format is YYYY-MM-DD HH:MM:SS and optionally YYYY-MM-DD HH:MM:SS+HH:MM to specify timezone.
'''
ARRIVAL_DEPARTURE_MISSING_ERR_MSG = '''
Date and time value for --{0} missing.
You can specify it with --{0}='YYYY-MM-DD HH:MM:SS' or --{0}='YYYY-MM-DD HH:MM:SS+HH:MM' to specify timezone
or specify it by doing --{0} 'YYYY-MM-DD HH:MM:SS' or --{0} 'YYYY-MM-DD HH:MM:SS+HH:MM'.
'''

DURATION_VAL_ERR_MSG = '''
Value for --duration specified incorrectly.
Correct format is 'HH:MM'.
'''
DURATION_MISSING_ERR_MSG = '''
Value for --duration missing.
You can specify it by using --duration='HH:MM' or --duration 'HH:MM'
'''

HELP_MSG = f'''Script to create an event on google calendar regarding your travel bookings.
{os.path.basename(__file__)} [options]

All options are optional. If [REQUIRED] options are not specified or are specified incorrectly, they will be asked from you in an interactive mode. Here's a list:
--help: Prints this help message and exits the program

Any 2 of the 3 below are required. If all 3 are specified. Only --departure and --arrival values are considered
--departure='YYYY-MM-DD HH:MM:SS' or --departure='YYYY-MM-DD HH:MM:SS+HH:MM': [REQUIRED] Specifies the beginning date and time of your journey along with utc offset if necessary.
--arrival='YYYY-MM-DD HH:MM:SS' or --arrival='YYYY-MM-DD HH:MM:SS+HH:MM': [REQUIRED] Specifies the ending date and time of your journey along with utc offset if necessary.
--duration='HH:MM': Specifies the duration of the journey
'''

PRETTY_DATETIME_FMT = '%A, %b %-d %Y %-I:%M%p'


def init_service(user_creds_file: str = 'token.json'):
    creds = None

    if os.path.exists(user_creds_file):
        creds = Credentials.from_authorized_user_file(user_creds_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            ).run_local_server(port=0)

        # Saving login tokens for next time
        with open(user_creds_file, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


def ensure_input(msg: str, default_val: int | None = None, constraint: Callable[[int], bool] = lambda _: True, constraint_err_msg: str = '') -> int:
    while True:
        try:
            # The space before [{default_value}] is intentional and simply there for formatting purposes
            if default_val == None:
                data = int(input(msg))
            else:
                data = input(msg.format(f' [{default_val}]'))
                data = default_val if data == '' else int(data)

            if not constraint(data):
                print(constraint_err_msg)
                continue

        except ValueError:
            print(f'Please enter an integer only!!')
        else:
            return data


def ask_datetime(verb: str) -> datetime:
    print(f'Enter your {verb} date and time below')
    while True:
        year = ensure_input(f'Enter year of {verb}{{}}: ', datetime.now().year)
        month = ensure_input(
            f'Enter the number of the month of {
                verb} (1 for January and so on){{}}: ',
            datetime.now().month,
            constraint=lambda month: 0 < month < 13,
            constraint_err_msg='1 represents January and 12 represents December. Please enter month number accordingly!')
        date = ensure_input(
            f'Enter the date{{}}: ', int(datetime.now().strftime('%-d')))
        hour = ensure_input(f'Enter the hour of {verb} in 24-hour format: ',
                            constraint=lambda hour: 0 <= hour < 24,
                            constraint_err_msg='0 represents 12am and 23 represents 11pm. Enter hour accordingly!')
        minute = ensure_input(f'Enter the minute of {verb}: ',
                              constraint=lambda minute: 0 <= minute < 60,
                              constraint_err_msg='Please ensure 0 <= minute < 60')

        try:
            return datetime(year, month, date, hour, minute).astimezone()
        except ValueError as e:
            print(f'Ivalid date entered: {e}. Let us try again!')


def ask_duration() -> timedelta:
    print('Enter your travel duration: ')
    while True:
        hours = ensure_input('How many hours is your journey? ')
        minutes = ensure_input('How many minutes is your journey? ')

        try:
            return timedelta(hours=hours, minutes=minutes)
        except ValueError as e:
            print(f'Invalid duration entered: {e}. Let us try again!')


def departure_arrival_duration_calc(departure: datetime, ask_departure: Callable[[], datetime], arrival: datetime, ask_arrival: Callable[[], datetime], duration: timedelta) -> tuple[datetime, datetime, timedelta]:
    if departure and arrival and duration:
        print('--departure, --arrival and --duration all 3 specified. Only considering --departure and --arrival')
        duration = arrival - departure
    elif departure and arrival:
        duration = arrival - departure
    elif departure and duration:
        arrival = departure + duration
    elif arrival and duration:
        departure = arrival - duration
    elif duration:
        departure = ask_departure()
        arrival = departure + duration
    else:
        if departure:
            arrival = ask_arrival()
        elif arrival:
            departure = ask_departure()
        else:
            departure = ask_departure()
            arrival = ask_arrival()
        duration = arrival - departure

    return departure, arrival, duration


class ValueFlag:
    _T = TypeVar('_T')

    def __init__(self, name: str, val_err_msg: str, missing_err_msg: str, with_data: Callable[[str], _T], ask: Callable[[], _T], as_str: Callable[[Self], str] = lambda _: 'TODO'):
        self.flag = f'--{name}'
        self.val_err_msg = val_err_msg
        self.missing_err_msg = missing_err_msg
        self.with_data = with_data
        self.ask = ask
        self.val: self._T | None = None
        self.as_str = as_str

    def __str__(self):
        return self.as_str(self)


def parse_args(args: list[str]) -> tuple[datetime, datetime] | NoReturn:
    # Special case if --help is specified
    if args.count('--help') >= 1:
        print(HELP_MSG)
        exit(0)

    val_flags: dict[str, ValueFlag] = {
        'departure': ValueFlag(
            name='departure',
            val_err_msg=ARRIVAL_DEPARTURE_VAL_ERR_MSG.format(
                'departure'),
            missing_err_msg=ARRIVAL_DEPARTURE_MISSING_ERR_MSG.format(
                'departure'),
            with_data=lambda data: datetime.fromisoformat(data).astimezone(),
            ask=lambda: ask_datetime('departure'),
            as_str=lambda self: f'Departure time: {
                self.val.strftime(PRETTY_DATETIME_FMT)}'
        ),
        'arrival': ValueFlag(
            name='arrival',
            val_err_msg=ARRIVAL_DEPARTURE_VAL_ERR_MSG.format(
                'arrival'),
            missing_err_msg=ARRIVAL_DEPARTURE_MISSING_ERR_MSG.format(
                'arrival'),
            with_data=lambda data: datetime.fromisoformat(data).astimezone(),
            ask=lambda: ask_datetime('arrival'),
            as_str=lambda self: f'Arrival time: {
                self.val.strftime(PRETTY_DATETIME_FMT)}'
        ),
        'duration': ValueFlag(
            name='duration',
            val_err_msg=DURATION_VAL_ERR_MSG,
            missing_err_msg=DURATION_MISSING_ERR_MSG,
            with_data=lambda data: timedelta(
                hours=int(data[:2]), minutes=int(data[3:])),
            ask=ask_duration,
            as_str=lambda self: f'Duration of journey: {self.val}'
        )
    }

    next_accounted_for = False
    for i, arg in enumerate(args):
        if next_accounted_for:
            next_accounted_for = False
            continue

        if not arg.startswith('--'):
            print(f'Unrecognized option: {arg}. Exiting...')
            exit(-1)

        if flag := val_flags.get(arg.split('=', maxsplit=1)[0][2:]):
            try:
                # Value specified as --departure '2025-01-14'
                if len(arg) == len(flag.flag):
                    # Cases where the flag is given but not its value
                    if len(args) - 1 <= i or args[i + 1].startswith('--'):
                        print(flag.missing_err_msg)
                        flag.val = flag.ask()
                    else:
                        next_accounted_for = True
                        flag.val = flag.with_data(args[i + 1])
                # Value specified as --departure='2025-01-14'
                elif arg[len(flag.flag)] == '=':
                    flag.val = flag.with_data(
                        arg[len(flag.flag) + 1:])
            # This ValueError will only occur when the specified data is garbled
            except ValueError:
                print(flag.val_err_msg)
                flag.val = flag.ask()
        else:
            print(f'Unrecognized option {arg}. Exiting...')
            exit(-1)

    val_flags['departure'].val, val_flags['arrival'].val, val_flags['duration'].val = departure_arrival_duration_calc(
        val_flags['departure'].val, val_flags['departure'].ask, val_flags['arrival'].val, val_flags['arrival'].ask, val_flags['duration'].val)

    # Summary printing and correcting erroneous data
    while True:
        print(f'''
{'-'*30}
Summary of your tickets...''')

        for flag in val_flags.values():
            print(flag)

        deets_ok = input(f'''{'-'*30}
Is all this information alright? [Y/n]: ''')

        if deets_ok.lower() == 'y' or deets_ok == '':
            return (val_flags['departure'].val, val_flags['arrival'].val)
        elif deets_ok.lower() == 'n':
            # Printing the choosing menu
            for i, flag in enumerate(flags := list(val_flags.keys())):
                print(f'{i + 1}. {flag.capitalize()}')

            faulty_entry = ensure_input('Enter index of incorrect entry: ', constraint=lambda x: 1 <= x <= len(
                flags), constraint_err_msg=f'Please ensure 0 < input < {len(flags) + 1}') - 1

            val_flags[flags[faulty_entry]
                      ].val = val_flags[flags[faulty_entry]].ask()

            # Changing one of the 3 values - departure, arrival or duration - must affect the another for them to remain in harmony
            if flags[faulty_entry] == 'duration':
                val_flags['arrival'].val = val_flags['departure'].val + \
                    val_flags['duration'].val
            elif flags[faulty_entry] in ['departure', 'arrival']:
                val_flags['duration'].val = val_flags['arrival'].val - \
                    val_flags['departure'].val
        else:
            print("Didn't get you. Try again.")


def main():
    # First element in argv is the name of the script itself
    departure, arrival = parse_args(sys.argv[1:])

    try:
        service = init_service()
        response = service.events().insert(calendarId='primary', body={
            'summary': 'Ticket',
            'start': {
                'dateTime': departure.isoformat()
            },
            'end': {
                'dateTime': arrival.isoformat()
            }
        }).execute()
        print(f"Added event at {response['htmlLink']}")

    except HttpError as error:
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()
