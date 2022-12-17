import pytest
import requests

from paperview.retrieval.biorxiv import (
    Message, 
    ArticleDetail,
    query_content_detail_by_doi,
    query_content_detail_by_interval,
    get_all_content_details_by_interval,
    )


@pytest.fixture
def example_article_detail():
    return {'doi': '10.1101/456574',
    'title': 'Complementary subnetworks of cortical somatostatin interneurons',
    'authors': 'Naka, A.; Shababo, B.; Snyder, B.; Egladyous, A.; Sridharan, S.; Paninski, L.; Adesnik, H.',
    'author_corresponding': 'Hillel  Adesnik',
    'author_corresponding_institution': 'UC Berkeley',
    'date': '2018-10-30',
    'version': '1',
    'type': 'new results',
    'license': 'cc_by_nc',
    'category': 'neuroscience',
    'jatsxml': 'https://www.biorxiv.org/content/early/2018/10/30/456574.source.xml',
    'abstract': 'The neocortex is organized into discrete layers of excitatory neurons: layer 4 receives the densest  bottom up projection carrying external sensory data, while layers 2/3 and 5 receive  top down inputs from higher cortical areas that may convey sensory expectations and behavioral goals. A subset of cortical somatostatin (SST) neurons gate top down input and control sensory computation by inhibiting the apical dendrites of pyramidal cells in layers 2/3 and 5. However, it is unknown whether an analogous inhibitory mechanism separately and specifically controls activity in layer 4. We hypothesized that distinct SST circuits might exist to inhibit specific cortical layers. By enforcing layer-specific inhibition, distinct SST subnetworks could mediate pathway-specific gain control, such as regulating the balance between bottom up and top down input. Employing a combination of high precision circuit mapping, in vivo optogenetic perturbations, and single cell transcriptional profiling, we reveal distinct and complementary SST circuits that specifically and reciprocally interconnect with excitatory cells in either layer 4 or layers 2/3 and 5. Our data further define a transcriptionally distinct SST neuronal sub-class that powerfully gates bottom up sensory activity during active sensation by regulating layer 4 activity. This integrated paradigm further represents a potentially generalizable approach to identify and characterize neuronal cell types and reveal their in vivo function.',
    'published': '10.7554/eLife.43696',
    'server': 'biorxiv'}
    
def test_query_content_detail_by_doi_matches_example_article_detail(example_article_detail):
    response = query_content_detail_by_doi(doi=example_article_detail['doi'])
    
    assert response.status_code == 200
    assert response.json()['collection'][0] == example_article_detail
import pytest
from typing import List

def test_query_content_detail_by_interval():
    # Test a valid interval with a cursor value
    interval = "2018-08-21/2018-08-28"
    cursor = 45
    result = query_content_detail_by_interval(interval, cursor=cursor)
    assert isinstance(result, dict)
    assert isinstance(result['messages'], list)
    assert isinstance(result['collections'], list)
    assert len(result['collections']) >= 0
        
    # Test a valid interval without a cursor value
    interval = "2018-08-21/2018-08-28"
    result = query_content_detail_by_interval(interval)
    assert isinstance(result, dict)
    assert isinstance(result['messages'], list)
    assert isinstance(result['collections'], list)
    assert len(result['collections']) >= 0
        
    # Test an invalid interval
    interval = "invalid"
    with pytest.raises(ValueError):
        result = query_content_detail_by_interval(interval)

def test_get_all_content_details_by_interval():
    # Test a valid interval
    interval = "2018-08-21/2018-08-28"
    result = get_all_content_details_by_interval(interval)
    assert isinstance(result, list)
    assert len(result) >= 0