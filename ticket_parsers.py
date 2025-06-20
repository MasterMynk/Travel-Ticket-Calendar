from datetime import datetime, timedelta
import re
from functools import reduce

from pypdf import PdfReader
import pypdf.errors

import sys

def read_irctc_tkt(tkt_txt: str) -> tuple[datetime | None, datetime | None, timedelta | None, str | None, str | None]:
    '''
    Reads a standard IRCTC ticket and returns departure and arrival date and time if available along with boarding location and destination
    '''

    IRCTC_TIME_SPECIFIER = '%H:%M'
    IRCTC_DATE_SPECIFIER = '%d-%b-%Y'
    IRCTC_DATETIME_SPECIFIER = f'{IRCTC_TIME_SPECIFIER} {IRCTC_DATE_SPECIFIER}'

    departure, arrival = None, None

    # An IRCTC ticket has the Start Date, Departure date and time and Arrival Date and time all specified in one line
    line = re.search(
        r'Start Date\* (?P<start>.*?)\s+Departure\* (?P<departure>.*?)\s+Arrival\* (?P<arrival>.*?)\s*\n', tkt_txt)
    if line:
        # First checking if departure date and time is available. If it is then checking start date won't be necessary
        try:
            if line.group('departure') != 'N.A.':
                departure = datetime.strptime(
                    line.group('departure'), IRCTC_DATETIME_SPECIFIER).astimezone()
            else:
                print('Could not read departure date and time from ticket!')
        except ValueError:
            print('Could not read departure date and time from ticket!')

        try:
            if line.group('arrival') != 'N.A.':
                arrival = datetime.strptime(
                    line.group('arrival'), IRCTC_DATETIME_SPECIFIER).astimezone()
            else:
                print('Could not read arrival date and time from ticket!')
        except ValueError:
            print('Could not read arrival date and time from ticket!')
    else:
        print('Could not read any date and time data for arrival or departure from ticket!')

    boarding, destination = None, None
    location_info = re.search(
        r'Booked\sFrom\s*To\s*(.*?)\s\(.*?\)\s*.*?\)\s*(.*?)\s\(.*?\)', tkt_txt, flags=re.DOTALL)

    if location_info:
        boarding, destination = location_info.group(1), location_info.group(2)
    else:
        print("Could not read boarding location or destination from ticket!")

    return departure, arrival, arrival - departure if departure and arrival else None, boarding, destination


def read_mmt_tkt(tkt_txt: str) -> tuple[datetime, datetime, timedelta, str, str]:
    departure_match = re.search(
        r'\w{3} (?P<departure_time>\d{2}:\d{2}) hrs\n(?P<departure_date>.*)\n(?P<boarding1>.*)\n(?P<boarding2>.*)', tkt_txt)
    dur_match = re.search(
        r'(?P<year>\d{4}).*(?P<hours>\d{1,2})h (?P<minutes>\d{1,2})m duration', tkt_txt)

    departure = datetime.strptime(departure_match.group(
        'departure_time') + departure_match.group('departure_date') + dur_match.group('year'), '%H:%M%a, %d %b%Y')
    boarding = f'{departure_match.group('boarding1')} {
        departure_match.group('boarding2')}'

    duration = timedelta(hours=int(dur_match.group(
        'hours')), minutes=int(dur_match.group('minutes')))

    dest_match = re.search(
        r'\d{2}:\d{2} hrs \w{3}\n.*\n(?P<destination1>.*)\n(?P<destination2>.*)', tkt_txt)
    destination = f'{dest_match.group('destination1')} {
        dest_match.group('destination2')}'

    return departure.astimezone(), (departure + duration).astimezone(), duration, boarding, destination


def read_akasa_boarding_pass(tkt_txt: str) -> tuple[datetime, None, None, str, str]:
    locations = re.search(
        r'From\s*:\s*(?P<departure>.*)\nTo\s*:\s*(?P<destination>.*)', tkt_txt)
    departure = re.search(
        r'Date\s:\s(?P<date>.*)\sDeparture\s:\s(?P<time>.*)', tkt_txt)
    return datetime.strptime(departure.group('date') + departure.group('time'), '%d %b %Y%H:%M').astimezone(), None, None, locations.group('departure'), locations.group('destination')


def read_akasa_tkt(tkt_txt: str) -> tuple[datetime, datetime, timedelta, str, str]:
    matches = re.search(
        r"Baggage Allowance:.*\n(?P<boarding>.*\n.*)\n(?P<departure>.*\n.*)\n.*\n.*\n(?P<destination>.*\n.*)\n(?P<arrival>.*\n.*)", tkt_txt)

    departure = datetime.strptime(matches.group(
        "departure").replace('\n', ' '), "%d %b, %Y %H:%M").astimezone()
    arrival = datetime.strptime(
        matches.group("arrival").replace('\n', ' '), "%d %b, %Y %H:%M").astimezone()

    return departure, arrival, arrival - departure, matches.group("boarding").replace('\n', ' '), matches.group("destination").replace('\n', ' ')


def read_tkt(tkt_fp: str) -> tuple[datetime | None, datetime | None, timedelta | None, str | None, str | None, str | None]:
    try:
        with PdfReader(tkt_fp) as tkt:
            tkt_txt = reduce(lambda txt, page: txt +
                             page.extract_text(), tkt.pages, "")
            if tkt_txt.find('Web Boarding Pass') != -1 and tkt_txt.find('Akasa Air') != -1:
                return *read_akasa_boarding_pass(tkt_txt), 'Flight'
            elif tkt_txt.find('IRCTC') != -1:
                return *read_irctc_tkt(tkt_txt), 'Train'
            elif tkt_txt.find('SNV Aviation Private Limited'):
                return *read_akasa_tkt(tkt_txt), 'Flight'
            elif re.search('[Aa]irport', tkt_txt):
                return *read_mmt_tkt(tkt_txt), 'Flight'
            sys.exit(0)
    except pypdf.errors.PyPdfError:
        print("There was a problem opening your ticket! Parsing ticket for journey data won't be possible.")
    except:
        print("Couldn't interpret ticket content. Enter the details manually.")
    return None, None, None, None, None, None
