import logging
import os
from typing import Optional
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.events']
CALENDAR_ID = 'primary'
EVENT_INFO_DEFAULT = {
    'reminders': {
        'useDefault': False,
        'overrides': [
            {'method': 'email', 'minutes': 24 * 60},
            {'method': 'popup', 'minutes': 10},
        ],
    },
    'guestsCanInviteOthers': False,
    'guestsCanModify': False,
    'guestsCanSeeOtherGuests': False
}

def get_google_calendar_service():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    token_file = 'token.json'
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("refreshing token for google calendar service...")
            creds.refresh(Request())
            logging.info("Token refreshed!")
        else:
            credential_file = 'credentials.json'
            flow = InstalledAppFlow.from_client_secrets_file(credential_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    try:
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)

    except:
        logging.error("unable to connect to google calendar api")
        raise

def create_calendar_event_with_retry(service, body: dict, retry_count: int = 3) -> Optional[str]:
    try:
        event = service.events().insert(calendarId=CALENDAR_ID, body=body, sendNotifications=True).execute()
        return event['id']
    except:
        if retry_count > 0:
            logging.info("unable to create calendar event, retrying...")
            time.sleep(40 - retry_count * 10)
            return create_calendar_event_with_retry(service, body, retry_count - 1)
        else:
            logging.error("unable to create calendar event, failed after 3 retries")
            # Return None for now, will retry to create calendar nexttime, when someone rsvp to the event
            return None
        
def add_user_to_calendar_invite(calendar_invite_id: str, email: str, need_notify: bool = True, retry_count: int = 3):
    if not email or len(email.strip()) == 0: 
        logging.info("email is empty, skip adding user to calendar invite")
        return
    if not is_valid_email_format(email):
        logging.error(f"invalid email format: {email}, skip adding user to calendar invite")
        return
    service = get_google_calendar_service()
    try:
        event = service.events().get(calendarId=CALENDAR_ID, eventId=calendar_invite_id).execute()
        attendees = event.get('attendees', [])
        found = False
        for attendee in attendees:
            if 'email' not in attendee: continue
            if attendee['email'].lower().strip() == email.lower().strip():
                found = True
                break
        if not found:
            attendees.append({'email': email})
            event['attendees'] = attendees
            time.sleep(10)
            request = service.events().update(
                calendarId=CALENDAR_ID, eventId=calendar_invite_id, body=event, sendUpdates='all' if need_notify else 'none'
            )
            request.headers["If-Match"] = event['etag']
            request.execute()
            logging.info(f"add user to calendar invite success")
        else:
            logging.info(f"user already in calendar invite, skip adding")
    except Exception as ex:
        if retry_count > 0:
            logging.info(f"unable to add user to calendar event, retrying... {str(ex)}")
            time.sleep(40 - retry_count * 10)
            add_user_to_calendar_invite(calendar_invite_id, email, need_notify, retry_count - 1)
        else:
            logging.exception(f"unable to add user to calendar invite: {str(ex)}")
    
def remove_user_from_calendar_invite(name: str, calendar_invite_id: str, email: str, need_notify: bool = True, retry_count: int = 3):
    if not email or len(email.strip()) == 0: return
    service = get_google_calendar_service()
    try:
        event = service.events().get(calendarId=CALENDAR_ID, eventId=calendar_invite_id).execute()
        attendees = event.get('attendees', [])
        found_index = None
        for index, attendee in enumerate(attendees):
            if 'email' not in attendee: continue
            if attendee['email'].lower().strip() == email.lower().strip():
                found_index = index
                break
        if found_index is not None:
            attendees.pop(found_index)
            event['attendees'] = attendees
            request = service.events().update(
                calendarId=CALENDAR_ID, eventId=calendar_invite_id, body=event, sendUpdates='all' if need_notify else 'none'
            )
            request.headers["If-Match"] = event['etag']
            request.execute()
            logging.info(f"remove user from {name} calendar invite success")
        else:
            logging.info(f"user not found in {name} calendar invite, skip removing")
    except Exception as ex:
        if retry_count > 0:
            logging.info(f"unable to remove user from {name} calendar event, retrying...")
            time.sleep(40 - retry_count * 10)
            remove_user_from_calendar_invite(name, calendar_invite_id, email, need_notify, retry_count - 1)
        else:
            logging.exception(f"unable to remove user from {name} calendar invite: {str(ex)}")

def update_calendar_invite(calendar_invite_id: str, update_data: dict, send_notifications: bool, retry_count: int = 3):
    service = get_google_calendar_service()
    if not service: return
    try:
        event = service.events().get(calendarId=CALENDAR_ID, eventId=calendar_invite_id).execute()
        for key, value in update_data.items():
            event[key] = value
        request = service.events().update(
            calendarId=CALENDAR_ID, eventId=calendar_invite_id, sendUpdates='all' if send_notifications else 'none', 
            body=event
        )
        request.headers["If-Match"] = event['etag']
        request.execute()
        logging.info(f"calendar invite updated: calendar invite id = {calendar_invite_id} field changed = {update_data.keys()}")
    except Exception as ex:
        if retry_count > 0:
            logging.info("unable to update calendar event, retrying...")
            time.sleep(40 - retry_count * 10)
            update_calendar_invite(calendar_invite_id, update_data, send_notifications, retry_count - 1)
        else:
            logging.exception(f'Unable to update calendar invite {calendar_invite_id}, {str(ex)}')