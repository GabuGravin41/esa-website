import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.db import models
from datetime import datetime
from .models import Event

@require_GET
def events_api(request):
    """API endpoint to get events for the calendar"""
    # Get query parameters
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    # Base query - include all active events
    events_query = Event.objects.filter(is_active=True)
    
    # Apply year and month filters if provided
    if year and month:
        try:
            year = int(year)
            month = int(month)
            
            # Debug the filter
            print(f"Filtering by year={year}, month={month}")
            
            # Include events that occur during the month or span the month
            events_query = events_query.filter(
                (models.Q(start_date__year=year, start_date__month=month)) |  # Events starting in this month
                (models.Q(end_date__year=year, end_date__month=month))        # Events ending in this month
            )
        except (ValueError, TypeError) as e:
            # Invalid parameters, ignore filtering
            print(f"Error in date filtering: {e}")
    
    # Debug information
    print(f"API called with year={year}, month={month}")
    print(f"Found {events_query.count()} events")
    
    # Select needed fields
    events = events_query.values(
        'id', 'title', 'description', 'start_date', 'end_date', 'location',
        'category', 'image', 'is_online', 'online_link', 'event_type'
    )[:100]  # Limit to 100 events for performance
    
    # Format the response
    formatted_events = []
    for event in events:
        # Handle image URL
        image_url = None
        if event['image']:
            image_url = f"/media/{event['image']}"
        
        # Determine color based on category or event_type
        event_type = event.get('category') or event.get('event_type') or 'other'
        
        formatted_events.append({
            'id': event['id'],
            'title': event['title'],
            'description': event['description'][:100] + '...' if len(event['description']) > 100 else event['description'],
            'start': event['start_date'].isoformat(),
            'end': event['end_date'].isoformat() if event['end_date'] else event['start_date'].isoformat(),
            'location': event['location'],
            'backgroundColor': get_event_color(event_type),
            'borderColor': get_event_color(event_type),
            'textColor': '#ffffff',
            'url': f"/events/{event['id']}/",
            'extendedProps': {
                'is_online': event['is_online'],
                'online_link': event['online_link'],
                'image_url': image_url
            }
        })
    
    return JsonResponse(formatted_events, safe=False)

def get_event_color(event_type):
    """Return a color based on event type"""
    colors = {
        'workshop': '#4285F4',  # Blue
        'seminar': '#0F9D58',   # Green
        'conference': '#DB4437', # Red
        'networking': '#F4B400', # Yellow
        'competition': '#9C27B0', # Purple
        'social': '#00ACC1',    # Cyan
        'project': '#FF5722',   # Orange
    }
    
    return colors.get(event_type, '#607D8B')  # Default gray
