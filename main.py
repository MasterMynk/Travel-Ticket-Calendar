# TODO: Add a flag to dyanmically set location of token.json file
# TODO: Remove the need for credentials.json file. Store the data in this python script itself

import os.path
import sys
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar']


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


def get_date_time_interactive(verb):
    # TODO: Add error checking
    year = int(input(f'Enter year of {verb}: '))
    month = int(
        input(f'Enter the number of the month of {verb} [1 for January and so on]: '))
    date = int(input(f'Enter the date: '))
    hour = int(input(f'Enter the hour of {verb} in 24-hour format: '))
    minute = int(input(f'Enter the minute of {verb}: '))

    # TODO: Do more error checking while creating datetime object
    return datetime(year, month, date, hour, minute).astimezone()


def parse_args(args):
    departure = None
    arrival = None

    for i, arg in enumerate(args):
        # TODO: Add option to interpret --flag value
        # TODO: Do some checks to see data is correct
        # TODO: See if you can move common functionality between arrival and departure into a function
        # TODO: If the travel mode is specified then 'Enter your arrival/departure' date and time should be replaced by respective transport vehicle
        # TODO: Instead of specifying departure date time, give user the option to specify journey duration

        if arg.startswith('--departure='):
            try:
                departure = datetime.fromisoformat(arg[12:]).astimezone()
            except ValueError:
                print(
                    f'''--departure value specified incorrectly.
Correct format is YYYY-MM-DD HH:MM:SS and optionally YYYY-MM-DD HH:MM:SS+HH:MM to specify timezone.
Enter your departure date and time:'''
                )
                departure = get_date_time_interactive(verb='departure')
        elif arg.startswith('--arrival='):
            try:
                arrival = datetime.fromisoformat(arg[10:]).astimezone()
            except ValueError:
                print(
                    f'''--arrival value specified incorrectly.
Correct format is YYYY-MM-DD HH:MM:SS and optionally YYYY-MM-DD HH:MM:SS+HH:MM to specify timezone.
Enter your arrival date and time:'''
                )
                arrival = get_date_time_interactive(verb='arrival')

    if not departure:
        departure = get_date_time_interactive('departure')
    if not arrival:
        arrival = get_date_time_interactive('arrival')

    return departure, arrival


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
