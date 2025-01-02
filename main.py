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

ARRIVAL_DEPARTURE_ERR_MSG = '''--{0} value specified incorrectly.
Correct format is YYYY-MM-DD HH:MM:SS and optionally YYYY-MM-DD HH:MM:SS+HH:MM to specify timezone.
Enter your {0} date and time:'''

HELP_MSG = f'''Script to create an event on google calendar regarding your travel bookings.
{os.path.basename(__file__)} [options]

All options are optional. If [REQUIRED] options are not specified or are specified incorrectly, they will be asked from you in an interactive mode. Here's a list:
--help: Prints this help message and exits the program

--departure='YYYY-MM-DD HH:MM:SS' or --departure='YYYY-MM-DD HH:MM:SS+HH:MM': [REQUIRED] Specifies the beginning date and time of your journey along with utc offset if necessary.
--arrival='YYYY-MM-DD HH:MM:SS' or --arrival='YYYY-MM-DD HH:MM:SS+HH:MM': [REQUIRED] Specifies the ending date and time of your journey along with utc offset if necessary.'''


def init_service(user_creds_file='token.json'):
    creds = None

    if os.path.exists('token.json'):
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


def get_date_time_interactive(verb: str) -> Callable[[], datetime]:
    def logic():
        def ensure_input(code):
            while True:
                try:
                    data = code()
                except ValueError as e:
                    print(f'Please enter an integer only!!')
                else:
                    return data

        year = ensure_input(lambda: int(input(f'Enter year of {verb}: ')))
        month = ensure_input(lambda: int(
            input(f'Enter the number of the month of {verb} [1 for January and so on]: ')))
        date = ensure_input(lambda: int(input(f'Enter the date: ')))
        hour = ensure_input(lambda: int(
            input(f'Enter the hour of {verb} in 24-hour format: ')))
        minute = ensure_input(lambda: int(
            input(f'Enter the minute of {verb}: ')))

        # TODO: Do more error checking while creating datetime object
        try:
            return datetime(year, month, date, hour, minute).astimezone()
        except ValueError as e:
            print(f'Ivalid date entered: {e}. Exiting...')
            exit(1)
    return logic


class ValuefulFlag:
    _T = TypeVar('_T')

    def __init__(self, name: str, err_msg: str, interactive_getter: Callable[[], _T]):
        self.flag_name = f'--{name}'
        self.err_msg = err_msg
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
            err_msg=ARRIVAL_DEPARTURE_ERR_MSG.format('departure'),
            interactive_getter=get_date_time_interactive('departure')
        ),
        ValuefulFlag(
            name='arrival',
            err_msg=ARRIVAL_DEPARTURE_ERR_MSG.format('arrival'),
            interactive_getter=get_date_time_interactive('arrival')
        ),
    ]

    for i, arg in enumerate(args):
        # TODO: Add option to interpret --flag value
        # TODO: Do some checks to see data is correct
        # TODO: See if you can move common functionality between arrival and departure into a function
        # TODO: If the travel mode is specified then 'Enter your arrival/departure' date and time should be replaced by respective transport vehicle
        # TODO: Instead of specifying departure date time, give user the option to specify journey duration

        for flag in valueful_flags:
            if arg.startswith(flag.flag_name + '='):
                try:
                    flag.value = datetime.fromisoformat(
                        arg[len(flag.flag_name) + 1:]).astimezone()
                except ValueError:
                    print(flag.err_msg)
                    flag.value = flag.interactive_getter()
                break

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
