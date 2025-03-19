# google-calendar-implement
Implement calendar event api in python

# Update calendar event with etag checking
```
event = service.events().get(calendarId=CALENDAR_ID, eventId=calendar_invite_id).execute()
# update event here
request = service.events().update(
    calendarId=CALENDAR_ID, eventId=calendar_invite_id, body=event, sendUpdates='all' if need_notify else 'none'
)
request.headers["If-Match"] = event['etag']
request.execute()
```
