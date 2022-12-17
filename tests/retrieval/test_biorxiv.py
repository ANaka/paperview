import pytest
import requests
from paperview.retrieval.biorxiv import BioRxivAPI, ManuscriptMetadata

@pytest.fixture
def api():
    return BioRxivAPI()

def test_query(api):
    # Test a query for a single manuscript using a DOI
    api.server = "10.1101/2020.12.31.422412"
    response = api.query()
    assert response.status_code == 200
    
    # Test a query for a range of dates
    api.server = "biorxiv"
    api.interval = "2021/01/01/2021/01/31"
    response = api.query()
    assert response.status_code == 200

def test_get_metadata(api):
    # Test a query for a single manuscript using a DOI
    api.server = "10.1101/2020.12.31.422412"
    messages, collections = api.get_metadata()
    assert len(collections) == 1
    assert isinstance(collections[0], ManuscriptMetadata)
    
    # Test a query for a range of dates
    api.server = "biorxiv"
    api.interval = "2021/01/01/2021/01/31"
    messages, collections = api.get_metadata()
    assert len(collections) >= 1
    assert isinstance(collections[0], ManuscriptMetadata)

def test_query_many_records(api):
    # Test a query for many records
    api.server = "biorxiv"
    api.interval = "2021/01/01/2021/01/31"
    collections = api.query_many_records(1000)
    assert len(collections) == 1000
    assert isinstance(collections[0], ManuscriptMetadata)
