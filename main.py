import os.path
import sys
from datetime import datetime, timedelta
from collections.abc import Callable
from typing import NoReturn, Iterable, Any
import sys

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from flags import *
from ticket_parsers import read_tkt

SCOPES = ['https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/drive.file']

ARRIVAL_DEP_VAL_ERR_MSG = '''
--{0} value specified incorrectly.
Correct format is YYYY-MM-DD HH:MM:SS and optionally YYYY-MM-DD HH:MM:SS+HH:MM to specify timezone.
'''
ARRIVAL_DEP_MISSING_MSG = '''
Date and time value for --{0} missing.
You can specify it with --{0}='YYYY-MM-DD HH:MM:SS' or --{0}='YYYY-MM-DD HH:MM:SS+HH:MM' to specify timezone
or specify it by doing --{0} 'YYYY-MM-DD HH:MM:SS' or --{0} 'YYYY-MM-DD HH:MM:SS+HH:MM'.
'''

DURATION_VAL_ERR_MSG = '''
Value for --duration specified incorrectly.
Correct format is 'HH:MM'.
'''
DURATION_MISSING_MSG = '''
Value for --duration missing.
You can specify it by using --duration='HH:MM' or --duration 'HH:MM'
'''

COLORS = ['Lavendar', 'Sage', 'Grape', 'Flamingo', 'Banana',
          'Tangerine', 'Peacock', 'Graphite', 'Blueberry', 'Basil', 'Tomato']
COLOR_VAL_ERR_MSG = f'''
Value for --color specified incorrectly.
--color only accepts one of the following as value: {COLORS}
Eg: --color=lavendar or --color banana
'''
COLOR_MISSING_MSG = f'''
Value for --color option missing.
You can specify it by doing --color=banana or --color tangerine from the following list of colors:
{COLORS}
'''

TYPE_MISSING_MSG = f'''
Value for --type missing.
You can specify it by doing --type='type of travel' or --type 'type of travel'
Eg: --type 'Flight'
This will be added to the title in the form: 'Flight to [destination]'.
'''

FROM_MISSING_MSG = f'''
Value for --from missing. This represents the boarding location for your journey.
You can specify it by doing --from='Mopa Airport' or --from 'Dabolim Airport'
This will be added to the from field of the google calendar event.
'''
TO_MISSING_MSG = f'''
Value for --to missing. This represents your destination.
You can specify it by doing --to='Thivim Railway Station' or --to 'Madgaon Railway Station'
This will be added to the title in the form: '[Trip] to Madgaon Railway Station'.
'''

HELP_MSG = f'''Script to create an event on google calendar regarding your travel bookings.
{os.path.basename(__file__)} [location/to/ticket.pdf] [--departure='YYYY-MM-DD HH:MM:SS'] [--arrival 'YYYY-MM-DD HH:MM:SS'] ...

If ticket.pdf is provided then it will be uploaded to google drive and attached to the calendar event

If [REQUIRED] options are not specified or are specified incorrectly, they will be asked from you in an interactive mode unless --no-ask is specified.
For all options that take a value the value can be specified in 2 ways:
--opt='value' or --opt 'value'

Here's a list of all options:
--help: Prints this help message and exits the program

Any 2 of the 3 below are required. If all 3 are specified. Only --departure and --arrival values are considered
--departure='YYYY-MM-DD HH:MM:SS' or --departure='YYYY-MM-DD HH:MM:SS+HH:MM': [REQUIRED] Specifies the beginning date and time of your journey along with utc offset if necessary.
--arrival='YYYY-MM-DD HH:MM:SS' or --arrival='YYYY-MM-DD HH:MM:SS+HH:MM': [REQUIRED] Specifies the ending date and time of your journey along with utc offset if necessary.
--duration='HH:MM': Specifies the duration of the journey

--color='color name' Available options are: {COLORS}. Default is Banana.

--type='type of travel' This will appear in the title of the event as 'TYPE to DESTINATION'
Eg: --type=Flight then title could be 'Flight to New Delhi'

--from='boarding location' This will appear in the location section of the google event
--to='destination' This will appear in the title of the event as 'TYPE to DESTINATION'

--no-confirm Will not ask for confirmation after printing summary and will create event with given or default data.
--no-ask Nothing will be asked interactively. If there is insufficient data program will exit without creating event.
'''

PRETTY_DATETIME_FMT = '%A, %b %-d %Y %-I:%M%p'


def init_service(user_creds_file: str = 'token.json') -> tuple[Any, Any, bool]:
    to_upload_tkt = True
    creds = None

    try:
        if os.path.exists(user_creds_file):
            creds = Credentials.from_authorized_user_file(
                user_creds_file, SCOPES)
    except:
        os.remove(user_creds_file)

    try:
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
    except Warning:
        print('Required permissions not authorized! Exiting...')
        sys.exit(-1)

    return build('calendar', 'v3', credentials=creds), build('drive', 'v3', credentials=creds), to_upload_tkt


def ensure_input(msg: str, default_val: int | None = None, constraint: Callable[[int], bool] = lambda _: True, constraint_err_msg: str = '') -> int:
    while True:
        try:
            if default_val == None:
                data = int(input(msg))
            else:
                # The space before [{default_value}] is intentional and simply there for formatting purposes
                data = input(msg.format(f' [{default_val}]'))
                data = default_val if data == '' else int(data)

            if not constraint(data):
                print(constraint_err_msg)
                continue

        except ValueError:
            print(f'Please enter an integer only!!')
        else:
            return data


def ask_hour(verb: str) -> int:
    # This is a function because it's used in read_irctc_tkt and ask_datetime
    return ensure_input(f'Enter the hour of {verb} in 24-hour format: ',
                        constraint=lambda hour: 0 <= hour < 24,
                        constraint_err_msg='0 represents 12am and 23 represents 11pm. Enter hour accordingly!')


def ask_minute(verb: str) -> int:
    # This function also exists because of the same reason as ask_hour
    return ensure_input(f'Enter the minute of {verb}: ',
                        constraint=lambda minute: 0 <= minute < 60,
                        constraint_err_msg='Please ensure 0 <= minute < 60')


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
        hour = ask_hour(verb)
        minute = ask_minute(verb)

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


def ensure_fp() -> str:
    while True:
        fp = input('Enter the filepath to the ticket pdf: ')
        if os.path.isfile(fp):
            return fp
        print(f"{fp} doesn't exist. Enter a valid file path!!")


def menu(items: Iterable[str], msg: str) -> int:
    for i, item in enumerate(items):
        print(f'{i + 1}. {item.capitalize()}')

    return ensure_input(msg, constraint=lambda x: 1 <= x <= len(items),
                        constraint_err_msg=f'Please ensure 0 < input < {len(items) + 1}')


def parse_args(args: list[str], val_flags: dict[str, ValueFlag], bool_flags: dict[str, BoolFlag]) -> str | None | NoReturn:
    '''
    Goes through args passed by the user and modifies val_flags with any data
    found accordingly.
    '''

    # Special case if --help is specified
    if args.count('--help') >= 1:
        print(HELP_MSG)
        sys.exit(0)

    # Checking for bool flags
    for arg in args:
        flag_name = arg[2:]
        if flag := bool_flags.get(flag_name):
            flag.val = True

    # Getting the filepath for ticket if its specified
    tkt_fp = None
    if len(args) and not args[0].startswith('--'):
        tkt_fp = args[0]

        if not os.path.isfile(tkt_fp):
            print(f"{tkt_fp} doesn't exist. Enter a valid file path!!")

            if bool_flags['no-ask'].val:
                sys.exit(-1)

            tkt_fp = ensure_fp()

        val_flags['departure'].val, val_flags['arrival'].val, val_flags['duration'].val, val_flags['from'].val, val_flags['to'].val, val_flags['type'].val = read_tkt(
            tkt_fp)

        args.pop(0)

    # Checking for flags with value
    next_accounted_for = False
    for i, arg in enumerate(args):
        if next_accounted_for:
            next_accounted_for = False
            continue

        if not arg.startswith('--'):
            print(f'Unrecognized option: {arg}. Exiting...')
            sys.exit(-1)

        flag_name = arg.split('=', maxsplit=1)[0][2:]
        if flag := val_flags.get(flag_name):
            try:
                # Value specified as --departure '2025-01-14'
                if len(arg) == len(flag.flag):
                    # Cases where the flag is given but not its value
                    if len(args) - 1 <= i or args[i + 1].startswith('--'):
                        print(flag.missing_msg)
                        if bool_flags['no-ask'].val:
                            sys.exit(-1)

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
                if bool_flags['no-ask'].val:
                    sys.exit(-1)

                flag.val = flag.ask()
        elif not bool_flags.get(flag_name):
            print(f'Unrecognized option {arg}. Exiting...')
            sys.exit(-1)

    return tkt_fp


def departure_arrival_duration_calc(val_flags: dict[str, ValueFlag], to_ask: bool) -> None | NoReturn:
    '''
    Calculates or asks the required values from departure, arrival and duration
    to ensure all 3 are obtained
    '''

    # If all 3 exist departure and arrival are prioritized so duration is re-calculated
    if val_flags['departure'].val and val_flags['arrival'].val and val_flags['duration'].val:
        print('--departure, --arrival and --duration all 3 specified. Only considering --departure and --arrival')
        val_flags['duration'].val = val_flags['arrival'].val - \
            val_flags['departure'].val
    # If any 2 are present third is simply calculated
    elif val_flags['departure'].val and val_flags['arrival'].val:
        val_flags['duration'].val = val_flags['arrival'].val - \
            val_flags['departure'].val
    elif val_flags['departure'].val and val_flags['duration'].val:
        val_flags['arrival'].val = val_flags['departure'].val + \
            val_flags['duration'].val
    elif val_flags['arrival'].val and val_flags['duration'].val:
        val_flags['departure'].val = val_flags['arrival'].val - \
            val_flags['duration'].val
    elif not to_ask:
        print('Insufficient information. Any 2 of departure time, arrival time or duration required and can be supplied by using --departure, --arrival and --duration respectively.')
        sys.exit(-1)
    # If only one is present one more is asked for and then third is calculated
    elif val_flags['duration'].val:
        val_flags['departure'].val = val_flags['departure'].ask()
        val_flags['arrival'].val = val_flags['departure'].val + \
            val_flags['duration'].val
    else:
        if val_flags['departure'].val:
            val_flags['arrival'].val = val_flags['arrival'].ask()
        elif val_flags['arrival'].val:
            val_flags['departure'].val = val_flags['departure'].ask()
        # If none were given then departure and arrival are asked for to calculate duration
        else:
            val_flags['departure'].val = val_flags['departure'].ask()
            val_flags['arrival'].val = val_flags['arrival'].ask()
        val_flags['duration'].val = val_flags['arrival'].val - \
            val_flags['departure'].val


def summary_and_confirm(val_flags: dict[str, ValueFlag], tkt_fp: str | None, to_confirm: bool) -> str | None:
    while True:
        # Summary printing
        print(f'''
{'-'*30}
Summary of your ticket...''')

        for flag in val_flags.values():
            if flag.flag == '--type':
                print(f'Title: {flag} to {val_flags['to'].val or 'somewhere'}')
                continue

            print(flag)
        print(f'Location of ticket pdf: {tkt_fp or 'Unspecified'}')
        print(f'{'-'*30}')
        if not to_confirm:
            return tkt_fp

        deets_ok = input('Is all this information alright? [Y/n]: ')

        if deets_ok.lower() == 'y' or deets_ok == '':
            return tkt_fp
        elif deets_ok.lower() == 'n':
            # Printing the choosing menu
            faulty_entry = menu(flags := list(val_flags.keys()) + ['Ticket file path'],
                                msg='Enter index of incorrect entry: ') - 1

            # User wants to change ticket file path
            if faulty_entry >= len(flags) - 1:
                tkt_fp = ensure_fp()
                continue

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


def upload_to_drive(drive: Any, tkt_fp: str) -> Any:
    mime_type = 'application/pdf'
    return drive.files().create(body={
        'mimeType': mime_type,
        'name': os.path.basename(tkt_fp),
    }, media_body=MediaFileUpload(tkt_fp, mimetype=mime_type, resumable=True), fields='id,name,webViewLink,mimeType').execute()


def create_event(calendar: Any, title: str, departure: datetime, arrival: datetime, color: int, location: str | None = None, attachments: list[Any] = []) -> Any:
    rq_body = {
        'summary': title,
        'start': {
            'dateTime': departure.isoformat()
        },
        'end': {
            'dateTime': arrival.isoformat()
        },
        'colorId': str(color),
        'reminders': {
            'useDefault': False,
            'overrides': [
                {
                    'method': 'popup',
                    'minutes': 30
                },
                {
                    'method': 'popup',
                    'minutes': 120
                },
                {
                    'method': 'popup',
                    'minutes': 10080  # 1 week
                }
            ]
        }
    }
    if location:
        rq_body['location'] = location

    if len(attachments) > 0:
        rq_body['attachments'] = []
    for file in attachments:
        rq_body['attachments'].append(
            {
                'fileId': file['id'],
                'title': file['name'],
                'mimeType': file['mimeType'],
                'fileUrl': file['webViewLink']
            }
        )

    return calendar.events().insert(calendarId='primary', body=rq_body,
                                    supportsAttachments=bool(len(attachments))).execute()


def check_existing_trip(calendar: Any, departure: datetime, arrival: datetime):
    events = calendar.events().list(calendarId="primary",
                                    timeMin=(
                                        departure - timedelta(seconds=1)).isoformat(),
                                    timeMax=(
                                        arrival + timedelta(seconds=1)).isoformat(),
                                    maxResults=10, singleEvents=True, orderBy='startTime').execute()['items']
    for ev in events:
        if (dep := ev['start'].get('dateTime')) and (arr := ev['end'].get('dateTime')) and datetime.fromisoformat(dep) == departure and datetime.fromisoformat(arr) == arrival:
            return ev
    return None


def get_confirmation(msg: str, yes_default: bool) -> bool:
    while True:
        resp = input(f'{msg} [{'Y/n' if yes_default else 'y/N'}]: ')
        if resp == '':
            return yes_default
        resp = resp.lower()
        if resp == 'y':
            return True
        if resp == 'n':
            return False
        print("Didn't get you. Try again.")


def main():
    # List of all options that take a value
    val_flags: dict[str, ValueFlag] = {
        'departure': ValueFlag(
            name='departure',
            val_err_msg=ARRIVAL_DEP_VAL_ERR_MSG.format(
                'departure'),
            missing_msg=ARRIVAL_DEP_MISSING_MSG.format(
                'departure'),
            with_data=lambda data: datetime.fromisoformat(data).astimezone(),
            ask=lambda: ask_datetime('departure'),
            as_str=lambda this: f'Departure time: {
                this.val.strftime(PRETTY_DATETIME_FMT)}'
        ),
        'arrival': ValueFlag(
            name='arrival',
            val_err_msg=ARRIVAL_DEP_VAL_ERR_MSG.format(
                'arrival'),
            missing_msg=ARRIVAL_DEP_MISSING_MSG.format(
                'arrival'),
            with_data=lambda data: datetime.fromisoformat(data).astimezone(),
            ask=lambda: ask_datetime('arrival'),
            as_str=lambda this: f'Arrival time: {
                this.val.strftime(PRETTY_DATETIME_FMT)}'
        ),
        'duration': ValueFlag(
            name='duration',
            val_err_msg=DURATION_VAL_ERR_MSG,
            missing_msg=DURATION_MISSING_MSG,
            with_data=lambda data: timedelta(
                hours=int(data[:2]), minutes=int(data[3:])),
            ask=ask_duration,
            as_str=lambda this: f'Duration of journey: {this.val}'
        ),
        'color': ValueFlag(
            name='color',
            val_err_msg=COLOR_VAL_ERR_MSG,
            missing_msg=COLOR_MISSING_MSG,
            with_data=lambda data: COLORS.index(data.capitalize()) + 1,
            ask=lambda: menu(COLORS, 'Enter the index of your chosen color: '),
            as_str=lambda this: f'Color for event: {COLORS[this.val - 1]}',
            initial_val=COLORS.index('Banana') + 1
        ),
        'type': ValueFlag(
            name='type',
            missing_msg=TYPE_MISSING_MSG,
            ask=lambda: input('Enter the type of travel this is: '),
            as_str=lambda this: this.val,
            initial_val='Trip',
        ),
        'from': ValueFlag(
            name='from',
            missing_msg=FROM_MISSING_MSG,
            ask=lambda: input('Enter your boarding location: '),
            as_str=lambda this: f'Boarding location: {this.val or 'Unknown'}',
        ),
        'to': ValueFlag(
            name='to',
            missing_msg=TO_MISSING_MSG,
            ask=lambda: input('Enter your destination: '),
            as_str=lambda this: f'Going to: {this.val or 'Unknown'}'
        )
    }

    bool_flags = {
        'no-confirm': BoolFlag('no-confirm'),
        'no-ask': BoolFlag('no-ask')
    }

    # All 3 function modify val_flags in place
    tkt_fp = parse_args(sys.argv[1:], val_flags, bool_flags)
    # Having any 2 out of departure, arrival or duration can used to calculate the third. This line does that
    departure_arrival_duration_calc(val_flags, not bool_flags['no-ask'].val)
    tkt_fp = summary_and_confirm(val_flags, tkt_fp, not (
        bool_flags['no-confirm'].val or bool_flags['no-ask'].val))

    exit_by_default = False
    while not exit_by_default:
        exit_by_default = True
        try:
            calendar, drive, to_upload_tkt = init_service()

            if to_upload_tkt and tkt_fp:
                file = upload_to_drive(drive, tkt_fp)
                print(
                    f'Ticket uploaded to your drive at {file['webViewLink']}')

            if not bool_flags['no-ask'].val and (ev := check_existing_trip(calendar, val_flags['departure'].val, val_flags['arrival'].val)) and get_confirmation('Do you want to update this event itself? ', True):
                if to_upload_tkt and tkt_fp:
                    if ev.get('attachments') == None:
                        ev['attachments'] = []
                    ev['attachments'].append({
                        'fileId': file['id'],
                        'title': file['name'],
                        'mimeType': file['mimeType'],
                        'fileUrl': file['webViewLink']
                    })

                response = calendar.events().update(
                    calendarId='primary', eventId=ev['id'], body=ev, supportsAttachments=True).execute()
            else:
                response = create_event(calendar,
                                        title=f'{val_flags['type'].val} to {val_flags['to'].val or 'somewhere'}', departure=val_flags['departure'].val,
                                        arrival=val_flags['arrival'].val,
                                        color=val_flags['color'].val,
                                        location=val_flags['from'].val,
                                        attachments=[
                                            file] if to_upload_tkt and tkt_fp else []
                                        )

            print(f"Added event at {response['htmlLink']}")

        except HttpError as error:
            print(f'An error occurred: {error}')
        except RefreshError as e:
            print(
                f'Seems like your token.json file has expired. Deleting it and trying again.')
            os.remove('token.json')
            exit_by_default = False
        except:
            print(f"Some error occured. Could not create the event")


if __name__ == '__main__':
    main()
