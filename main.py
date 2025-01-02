# TODO: Add a flag to dyanmically set location of token.json file
# TODO: Remove the need for credentials.json file. Store the data in this python script itself

import os.path
import sys
from datetime import datetime
from collections.abc import Callable
from typing import TypeVar, NoReturn

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar']

ARRIVAL_DEPARTURE_INCORRECT_ERR_MSG = '''--{0} value specified incorrectly.
Correct format is YYYY-MM-DD HH:MM:SS and optionally YYYY-MM-DD HH:MM:SS+HH:MM to specify timezone.
Enter your {0} date and time:'''
ARRIVAL_DEPARTURE_MISSING_ERR_MSG = '''Date and time value for --{0} missing.
You can specify it with --{0}='YYYY-MM-DD HH:MM:SS' or --{0}='YYYY-MM-DD HH:MM:SS+HH:MM' to specify timezone
or specify it by doing --{0} 'YYYY-MM-DD HH:MM:SS' or --{0} 'YYYY-MM-DD HH:MM:SS+HH:MM'
Enter your {0} date and time:'''

HELP_MSG = f'''Script to create an event on google calendar regarding your travel bookings.
{os.path.basename(__file__)} [options]

All options are optional. If [REQUIRED] options are not specified or are specified incorrectly, they will be asked from you in an interactive mode. Here's a list:
--help: Prints this help message and exits the program

--departure='YYYY-MM-DD HH:MM:SS' or --departure='YYYY-MM-DD HH:MM:SS+HH:MM': [REQUIRED] Specifies the beginning date and time of your journey along with utc offset if necessary.
--arrival='YYYY-MM-DD HH:MM:SS' or --arrival='YYYY-MM-DD HH:MM:SS+HH:MM': [REQUIRED] Specifies the ending date and time of your journey along with utc offset if necessary.'''


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


def get_date_time_interactive(verb: str) -> datetime | NoReturn:
    def ensure_input(msg: str, default_val: int | None = None) -> int:
        while True:
            try:
                # The space before [{default_value}] is intentional and simply there for formatting purposes
                data = input(msg.format(
                    f' [{default_val}]' if default_val != None else ''))
                data = default_val if default_val != None and data == '' else int(
                    data)
            except ValueError:
                print(f'Please enter an integer only!!')
            else:
                return data
    while True:
        year = ensure_input(f'Enter year of {verb}{{}}: ', datetime.now().year)
        month = ensure_input(
            f'Enter the number of the month of {verb} (1 for January and so on){{}}: ', datetime.now().month)
        date = ensure_input(
            f'Enter the date{{}}: ', int(datetime.now().strftime('%-d')))
        hour = ensure_input(
            f'Enter the hour of {verb} in 24-hour format{{}}: ')
        minute = ensure_input(f'Enter the minute of {verb}{{}}: ')

        try:
            return datetime(year, month, date, hour, minute).astimezone()
        except ValueError as e:
            print(f'Ivalid date entered: {e}. Let us retry!')


class ValuefulFlag:
    _T = TypeVar('_T')

    def __init__(self, name: str, value_err_msg: str, missing_err_msg: str, with_data: Callable[[str], _T], interactive_getter: Callable[[], _T]):
        self.flag_name = f'--{name}'
        self.value_err_msg = value_err_msg
        self.missing_err_msg = missing_err_msg
        self.with_data = with_data
        self.interactive_getter = interactive_getter
        self.value: self._T | None = None


def parse_args(args: list[str]) -> tuple[datetime, datetime] | NoReturn:
    # Special case if --help is specified
    if args.count('--help') >= 1:
        print(HELP_MSG)
        exit(0)

    valueful_flags: list[ValuefulFlag] = [
        ValuefulFlag(
            name='departure',
            value_err_msg=ARRIVAL_DEPARTURE_INCORRECT_ERR_MSG.format(
                'departure'),
            missing_err_msg=ARRIVAL_DEPARTURE_MISSING_ERR_MSG.format(
                'departure'),
            with_data=lambda data: datetime.fromisoformat(data).astimezone(),
            interactive_getter=lambda: get_date_time_interactive('departure')
        ),
        ValuefulFlag(
            name='arrival',
            value_err_msg=ARRIVAL_DEPARTURE_INCORRECT_ERR_MSG.format(
                'arrival'),
            missing_err_msg=ARRIVAL_DEPARTURE_MISSING_ERR_MSG.format(
                'arrival'),
            with_data=lambda data: datetime.fromisoformat(data).astimezone(),
            interactive_getter=lambda: get_date_time_interactive('arrival')
        ),
    ]

    next_accounted_for = False
    for i, arg in enumerate(args):
        # TODO: If the travel mode is specified then 'Enter your arrival/departure' date and time should be replaced by respective transport vehicle
        # TODO: Instead of specifying departure date time, give user the option to specify journey duration

        is_valid_arg = False

        if next_accounted_for:
            next_accounted_for = False
            continue

        for flag in valueful_flags:
            if arg.startswith(flag.flag_name):
                is_valid_arg = True
                try:
                    # Value specified as --departure '2025-01-14'
                    if len(arg) == len(flag.flag_name):
                        # Cases where the flag is given but not its value
                        if len(args) - 1 <= i or args[i + 1].startswith('--'):
                            print(flag.missing_err_msg)
                            flag.value = flag.interactive_getter()
                        else:
                            next_accounted_for = True
                            flag.value = flag.with_data(args[i + 1])
                    # Value specified as --departure='2025-01-14'
                    elif arg[len(flag.flag_name)] == '=':
                        flag.value = flag.with_data(
                            arg[len(flag.flag_name) + 1:])
                    # Some garbled value like --departure2025-01
                    else:
                        print(f'Unrecognized option: {arg}. Exiting...')
                        exit(-1)
                # This ValueError will only occur when the specified data is garbled
                except ValueError:
                    print(flag.value_err_msg)
                    flag.value = flag.interactive_getter()
                break

        if not is_valid_arg:
            print(f'Unrecognized option: {arg}. Exiting...')
            exit(-1)

    for flag in valueful_flags:
        if not flag.value:
            flag.value = flag.interactive_getter()

    return map(lambda flag: flag.value, valueful_flags)


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
