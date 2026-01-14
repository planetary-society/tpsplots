from .google_sheets_source import GoogleSheetsSource


# Example implementation
class NewNASAAwards(GoogleSheetsSource):
    """
    Tracks new grants and contracts made by NASA for each month in a fiscal year
    """

    URL = "https://docs.google.com/spreadsheets/d/1VZZ4WAM2pVvMtUWFN9LTh0sGr0L9aO6O2eHXny28x7g/export?format=csv"
