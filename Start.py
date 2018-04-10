from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import tallyfy
import datetime

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Sync Tallyfy to Google Calendar - API'
GOOGLE_CALENDAR_NAME = "Tallyfy Calendar"


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def getCalendarID(service, calendarName=GOOGLE_CALENDAR_NAME):
    ''' Returns the Calendar ID for Tallyfy

    arg:
        service (apiclient.discovery.object)

    Looks for 'Tallyfy Calendar' in the Google user's calenders. If calender
    is not found, it means that it is the first time using the sync script
    and a new calender needs to be created
    '''
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            if calendar_list_entry['summary'] == calendarName:
                print("Tallyfy Google calendar exists...")
                return calendar_list_entry['id']
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break
    calendar = {
        'summary': calendarName
    }

    created_calendar = service.calendars().insert(body=calendar).execute()
    print("Tallyfy Google calendar does not exist. Created new \"Tallyfy Calendar\" for Google.")
    return created_calendar['id']


def deconflictCalendars(tallyfyCal, googleCal):
    '''Compares the Tallyfy calendar list with Google Calendar list to decide on creating event or updating events

    Args:
        tallyfyCal (list)
        googleCal (list)

    Returns dictionary of two lists. "CreateList" and "UpdateList".
    '''
    CreateList = []
    UpdateList = []
    for eventTallyfy in tallyfyCal:
        hasMatch = False
        for eventGoogle in googleCal:
            if eventGoogle['id'] == eventTallyfy['id']:
                hasMatch = True
                UpdateList.append(eventTallyfy)
                break
        if hasMatch is False:
            CreateList.append(eventTallyfy)

    return {'Create': CreateList, 'Update': UpdateList}


def main():
    '''Extracts all tasks to be done by the Tallyfy user
    '''
    listFromTallyfy = []
    tallyfy.extractTasks(tallyfy.url, tallyfy.accessHeader, listFromTallyfy)
    print(listFromTallyfy)

    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    250 events on the user's calendar.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    calendarID = getCalendarID(service)
    # Specify only looking for Tallyfy tasks from 30 days ago and onwards
    dtObject = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    date = dtObject.isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming 250 events by default on Google\'s Tallyfy Calendar.')
    eventsResult = service.events().list(
        calendarId=calendarID, timeMin=date, singleEvents=True,
        orderBy='startTime').execute()

    events = eventsResult.get('items', [])
    if not events:
        print('No upcoming events found on Google Calendar.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'].encode('utf-8'))

    # Deconflict by extracting tasks to be created and tasks to be updated into
    # two seperate lists
    changeDict = deconflictCalendars(listFromTallyfy, events)
    print("\n Printing the changeDict:")
    print(changeDict)

    print("Creating events (If it exists)...")
    for eventBody in changeDict['Create']:
        event = service.events().insert(calendarId=calendarID, body=eventBody).execute()
        print("Event created: %s" % (event.get('htmlLink')))

    print("Updating events (If it exists)...")
    for eventBody in changeDict['Update']:
        updated_event = service.events().update(
            calendarId=calendarID, eventId=eventBody['id'], body=eventBody).execute()
        # Print the updated date.
        print("Event updated: %s" % updated_event['updated'])

    print("Google sync process completed.")


if __name__ == '__main__':

    main()
