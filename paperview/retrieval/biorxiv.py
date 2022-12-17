import requests
from attrs import define, field

@define
class Message:
    status: str = field()
    interval: str = field()
    cursor: str = field()
    count: int = field()
    count_new_papers: int = field()
    total: int = field()

def split_authors(authors: str) -> list:
    """Split a string of authors into a list of individual author names."""
    return authors.split('; ')

@define
class ManuscriptMetadata:
    doi: str = field()
    title: str = field()
    authors: list = field(converter=split_authors)
    author_corresponding: str = field()
    author_corresponding_institution: str = field()
    date: str = field()
    version: str = field()
    type: str = field()
    license: str = field()
    category: str = field()
    jatsxml: str = field()
    abstract: str = field()
    published: str = field()
    server: str = field()
    

class BioRxivAPI:
    def __init__(self, server, interval=None, cursor=0, format="json"):
        self.base_url = "https://api.biorxiv.org/details/"
        self.server = server
        self.interval = interval
        self.cursor = cursor
        self.format = format
       
    def query(self):
        if self.interval is not None:
            # Construct the URL for a range of dates or most recent N posts or N days
            url = f"{self.base_url}{self.server}/{self.interval}/{self.cursor}/{self.format}"
        else:
            # Construct the URL for a single manuscript using a DOI
            url = f"{self.base_url}{self.server}/na/{self.format}"
        
        # Make the request
        response = requests.get(url)
        
        # Return the response
        return response
    
    def get_metadata(self):
        # Get the response
        response = self.query()
        
        # Parse the messages output
        messages = response.json()['messages']
        parsed_messages = [Message(**message) for message in messages]
        
        # Parse the collections output
        collections = response.json()['collection']
        parsed_collections = [ManuscriptMetadata(**collection) for collection in collections]
        
        # Return the parsed messages and collections
        return parsed_messages, parsed_collections