from datetime import timedelta,datetime
# Helper function to format the time
def format_received_time(received_at: datetime) -> str:
    now = datetime.utcnow()
    today = now.date()
    yesterday = today - timedelta(days=1)

    # Check if the message was received today
    if received_at.date() == today:
        return received_at.strftime("%I:%M %p")  # E.g., "10:00 AM"
    # Check if the message was received yesterday
    elif received_at.date() == yesterday:
        return "yesterday"
    # Otherwise, return the full date
    else:
        return received_at.strftime("%B %d, %Y")  # E.g., "October 16, 2024"