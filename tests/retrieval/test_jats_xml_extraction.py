from unittest.mock import patch
from urllib.error import HTTPError

import pandas as pd
import pytest
import requests
from lxml import etree
from PIL import Image

from paperview.examples import example_dir
from paperview.retrieval.biorxiv_api import ArticleDetail, get_content_detail_for_page
from paperview.retrieval.jats_xml_extraction import JATSXML


@patch('requests.get')
def test_init_with_invalid_url(mock_get):
    mock_get.side_effect = ConnectionError
    with pytest.raises(ConnectionError):
        jats = JATSXML('http://invalid.url')


def test_base_xml_url():
    jats = JATSXML('http://valid.url.source.xml')
    assert jats.base_xml_url == 'http://valid.url'
    jats = JATSXML('http://valid.url.source')
    assert jats.base_xml_url == 'http://valid.url.source'


def test_get_image_url():
    jats = JATSXML('http://valid.url')
    assert jats.get_image_url('valid_slug') == 'http://valid.url/valid_slug.large.jpg'
