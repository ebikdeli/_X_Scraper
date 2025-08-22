from datetime import datetime


def current_timestamp() -> str:
    """Return current timestamp as standard string format to insert or update database"""
    current_time = datetime.now()
    # ISO format (recommended)
    # iso_time = current_time.isoformat()
    # String format
    return current_time.strftime('%Y-%m-%d %H:%M:%S')
