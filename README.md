***Script is still a work in progress***

A script that you can use to add your travel ticket as an event to your google calendar

To use the script you need to have `credentials.json` file in the same folder as the script.
This file can be obtained by following the steps mentioned [here](https://developers.google.com/calendar/api/quickstart/python) under `Set up your environment`

**DO NOT SHARE YOUR `credentials.json` and the `token.json` file that is generated after running the script for the first time and logging in with anyone**

# Usage

* `python main.py --departure='2025-01-14 13:50' --arrival='2025-01-14 20:05'`
* One can also specify the duration of the journey instead of either arrival or departure date and time by using `--duration='HH:MM'`
* All flags that take a value with them can get their value in two ways: `--flag=value` or `--flag value`. So `--departure='2025-01-14 13:50'` is equivalent to `--departure '2025-01-14 13:50'`
* If all 3 of `--duration`, `--departure` and `--arival` are specified then only values in `--departure` and `--arrival` are considered
* Use `python main.py --help` for more help message