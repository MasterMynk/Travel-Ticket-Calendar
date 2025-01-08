A script that you can use to add your travel ticket as an event to your google calendar.

`python main.py ticket.pdf` - Most common use case
If the ticket is a IRCTC or a MakeMyTrip Flight ticket then the script will automatically read any available information useful in creating the event.
This information includes:
1. Departure date and time
2. Arrival date and time
3. Boarding location
4. Destination

If any of these are unavailable or the ticket is unable to be read the script will ask for required details in an interactive mode while optional details will be given default values. The script will then upload the ticket to user's google drive and attach it to the calendar event.

# Set up
1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. Create a new project by clicking on `Select a project` or `<name of the previous project>` in the top left corner.
3. In the search bar search for `calendar api`, click on the [first option](https://console.cloud.google.com/flows/enableapi?apiid=calendar-json.googleapis.com) and enable the api.
4. Go back and search for `google drive api`, click on the [first option](https://console.cloud.google.com/flows/enableapi?apiid=drive.googleapis.com) and enable it.
5. Go back and search for `OAuth consent screen` and on the [first option](https://console.cloud.google.com/apis/credentials/consent)
    1. Select `User Type` as External and click `Create`
    2. Fill in the rquired details and click `SAVE AND CONTINUE`
    3. Click on `ADD OR REMOVE SCOPES`, search for `https://www.googleapis.com/auth/calendar`, click checkbox next to it and click `UPDATE`
    4. Repeat the above step this time searching for `https://www.googleapis.com/auth/drive.file`
    5. Click `SAVE AND CONTINUE`
    6. Click `ADD USERS` and enter your email
    7. Click `ADD` then `SAVE AND CONTINUE`
    8. Click `BACK TO DASHBOARD`
6. Click on `Credentials` on the left side
    1. Click `CREATE CREDENTIALS +` then `OAuth Client ID`
    2. Select `Application Type` as `Desktop App`
    3. Give it some name and click `CREATE`
    4. In the pop-up window click `DOWNLOAD JSON` and save the downloaded file alongside the script as `credentials.json`


**DO NOT SHARE YOUR `credentials.json` or `token.json` file that is generated after running the script for the first time and logging in with anyone**

# Usage

Script to create an event on google calendar regarding your travel bookings.
```bash
main.py [location/to/ticket.pdf] [--departure='YYYY-MM-DD HH:MM:SS'] [--arrival 'YYYY-MM-DD HH:MM:SS'] ...
```

If ticket.pdf is provided then it will be uploaded to google drive and attached to the calendar event

If **[REQUIRED]** options are not specified or are specified incorrectly, they will be asked from you in an interactive mode unless `--no-ask` is specified.
For all options that take a value the value can be specified in 2 ways:
--opt='value' or --opt 'value'

Here's a list of all options:
* `--help:` Prints this help message and exits the program

* Any 2 of the 3 below are required. If all 3 are specified. Only `--departure` and `--arrival` values are considered
* `--departure='YYYY-MM-DD HH:MM:SS'` or `--departure='YYYY-MM-DD HH:MM:SS+HH:MM'`: **[REQUIRED]** Specifies the beginning date and time of your journey along with utc offset if necessary.
* `--arrival='YYYY-MM-DD'` HH:MM:SS' or `--arrival='YYYY-MM-DD` HH:MM:SS+HH:MM': **[REQUIRED]** Specifies the ending date and time of your journey along with utc offset if necessary.
* `--duration='HH:MM'` Specifies the duration of the journey

* `--color='color` name' Available options are: {COLORS}. Default is Banana.

* `--type='type` of travel' This will appear in the title of the event as 'TYPE to DESTINATION'
Eg: `--type=Flight` then title could be 'Flight to New Delhi'

* `--from='boarding` location' This will appear in the location section of the google event
* `--to='destination'` This will appear in the title of the event as 'TYPE to DESTINATION'

* `--no-confirm` Will not ask for confirmation after printing summary and will create event with given or default data.
* `--no-ask` Nothing will be asked interactively. If there is insufficient data program will exit without creating event.