# google-calendar-implement
Implement calendar event api in python

# Update with etag checking
```
request = service.events().update(
    calendarId=CALENDAR_ID, eventId=calendar_invite_id, body=event, sendUpdates='all' if need_notify else 'none'
)
request.headers["If-Match"] = event['etag']
request.execute()
```
