from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen

import pandas as pd
import requests
from lxml import etree
from PIL import Image

from paperview.retrieval.process_xml import xmlstr_to_dict


class JATSXML(object):
    """
    This class is responsible for parsing and extracting data from JATS XML files.

    Args:
      url (str): The URL of the JATS XML file.

    Attributes:
      url (str): The URL of the JATS XML file.
      xml (str): The raw XML file.
      root (lxml.etree._Element): The root element of the XML file.
      xml_dict (dict): The XML file converted to a dictionary.
      data (dict): The extracted data from the XML file.
      full_xml_retrieved (bool): A boolean indicating whether the full XML file was retrieved.
    """

    def __init__(self, url: str):
        self.url = url

        # check url valid
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL")

        # check reachable url
        r = requests.head(url)
        if not r.ok:
            raise ValueError("URL not reachable")

        self.xml = requests.get(url).text

        self.root = etree.fromstring(self.xml)

        self.xml_dict = xmlstr_to_dict(self.xml)
        self.data = self.parse_xml_dict(self.xml_dict)
        self.full_xml_retrieved = self.check_if_is_fulltext_xml(self.data)

        if self.full_xml_retrieved:
            self.data['figure_captions']['slug'] = self.data['figure_captions']['label'].apply(
                lambda x: self.get_fig_slug(x)
            )
            self.data['figure_captions']['slug_backup'] = [
                f'F{ii+1}' for ii in self.data['figure_captions'].index
            ]

            images = []
            for ii, row in self.data['figure_captions'].iterrows():
                image_data = row.to_dict()

                result = self.get_image_from_slug(row['slug'])
                if result['status'] == 'image not found':
                    result = self.get_image_from_slug(row['slug_backup'])

                image_data.update(result)
                images.append(image_data)
            self.data['images'] = images

    @staticmethod
    def check_if_is_fulltext_xml(parsed_xml_data: dict):
        """
        It checks if the parsed xml data is a full text xml file.

        Args:
          parsed_xml_data (dict): the parsed xml data

        Returns:
          A boolean value.
        """
        return (parsed_xml_data['all_text']['title'] == 'Results').any()

    @property
    def base_xml_url(self):
        return self.url.split('.source.xml')[0]

    def get_image_url(self, slug: str):
        """
        It takes a slug and returns a URL

        Args:
          slug (str): The slug is the unique identifier for each image.

        Returns:
          The image url for the given slug.
        """
        return f'{self.base_xml_url}/{slug}.large.jpg'

    def get_image_from_slug(self, slug: str):
        """
        It takes a slug, gets the image url from the slug, and then gets the image from the url

        Args:
          slug (str): The slug of the image you want to get.

        Returns:
          The image is being returned.
        """
        url = self.get_image_url(slug)
        return self._get_image_from_url(url)

    def _get_image_from_url(self, url: str):
        """
        It takes a URL as an argument, checks that the URL is valid, tries to get the image from the
        URL, and returns the image if it was successful, or None if it wasn't

        Args:
          url (str): The url of the image to be retrieved

        Returns:
          A dictionary with the image and a status message.
        """
        # Parse the url
        parsed_url = urlparse(url)
        # Check that the url is valid
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL")
        # Try to get the image
        try:

            # Get the image data
            with urlopen(url) as response:
                with BytesIO(response.read()) as file:
                    img = Image.open(file)
                    img_data = img.tobytes()  # shenanigans to get it in memory while file is open
            # Return the image
            result = {
                'image': Image.frombytes(img.mode, img.size, img_data),
                'status': 'image retrieved',
            }
        except HTTPError as e:
            # Return None if there was an error
            result = {'status': 'image not found', 'image': None}
        return result

    def get_fig_slug(self, label: str):
        """
        It takes a label as an argument, searches the XML for that label, and returns the slug of the
        figure that the label is associated with

        Args:
          label (str): the label of the figure

        Returns:
          A list of all the slugs in the document.
        """
        try:
            element = self.root.xpath(f"//*[local-name()='label' and text()='{label}']/..")[0]
            #  search children for hwp:sub-type = slug and get text
            for child in element.getchildren():
                if 'slug' in child.attrib.values():
                    slug = child.text
            return slug
        except IndexError:
            return None

    @staticmethod
    def parse_xml_dict(xml_dict: dict):
        """
        > The function takes a dictionary of the XML file and returns a dictionary of dataframes

        Args:
          xml_dict (dict): the dictionary of the xml file

        Returns:
          A dictionary with three keys: xml_text, figure_captions, and table_captions.
        """
        # create dataframe from the xml dictionary
        df = pd.DataFrame(xml_dict['body_sections'])
        # get sections with level 2
        sections = df.query('level == 2').set_index('title')['id'].to_dict()
        texts = []
        figures = []
        tables = []
        # iterate over sections
        for sec_title, sec_id in sections.items():
            # get subsections for each section
            subsection_idx = df.id.str.startswith(sec_id)
            subsections = df.loc[subsection_idx]

            for subsec_id, subsection in subsections.set_index('id').iterrows():
                contents = subsection['contents']
                for content in contents:
                    # get texts
                    if content.get('tag') == 'p':
                        texts.append(
                            {'section': sec_title, 'id': content['id'], 'text': content['text']}
                        )
                    # get figures
                    elif content.get('tag') == 'fig':
                        figures.append(
                            {
                                'section': sec_title,
                                'id': content['id'],
                                'caption': content['caption'],
                                'label': content['label'],
                                'xref_id': content.get('xref_id'),
                            }
                        )
                    # get tables
                    elif content.get('tag') == 'table':
                        tables.append(
                            {
                                'section': sec_title,
                                'id': content['id'],
                                'caption': content['caption'],
                                'label': content['label'],
                                'xref_id': content.get('xref_id'),
                            }
                        )

        texts = pd.DataFrame(texts)
        figures = pd.DataFrame(figures)
        tables = pd.DataFrame(tables)
        return {
            'xml_text': texts,
            'figure_captions': figures,
            'table_captions': tables,
            'all_text': df,
        }
