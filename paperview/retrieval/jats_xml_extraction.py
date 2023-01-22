from io import BytesIO
from urllib.error import HTTPError
from urllib.request import urlopen

import pandas as pd
import requests
from lxml import etree
from PIL import Image

from paperview.retrieval.process_xml import xmlstr_to_dict


class JATSXML(object):
    def __init__(self, url: str):
        self.url = url
        self.xml = requests.get(url).text

        self.root = etree.fromstring(self.xml)

        self.xml_dict = xmlstr_to_dict(self.xml)
        self.data = self.parse_xml_dict(self.xml_dict)
        self.full_xml_retrieved = (self.data['all_text']['title'] == 'Results').any()

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

    @property
    def base_xml_url(self):
        return self.url.split('.source.xml')[0]

    def get_image_url(self, slug: str):
        return f'{self.base_xml_url}/{slug}.large.jpg'

    def get_image_from_slug(self, slug: str):
        url = self.get_image_url(slug)
        return self._get_image_from_url(url)

    def _get_image_from_url(self, url: str):
        result = {}
        try:
            with urlopen(url) as response:
                with BytesIO(response.read()) as file:
                    img = Image.open(file)
                    img_data = img.tobytes()  # shenanigans to get it in memory while file is open
                    result['image'] = Image.frombytes(img.mode, img.size, img_data)
                result['status'] = 'image retrieved'
        except HTTPError:
            result['status'] = 'image not found'
            result['image'] = None
        return result

    def get_fig_slug(self, label: str):
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
        df = pd.DataFrame(xml_dict['body_sections'])
        sections = df.query('level == 2').set_index('title')['id'].to_dict()
        texts = []
        figures = []
        tables = []
        for sec_title, sec_id in sections.items():
            subsection_idx = df.id.str.startswith(sec_id)
            subsections = df.loc[subsection_idx]

            for subsec_id, subsection in subsections.set_index('id').iterrows():
                contents = subsection['contents']
                for content in contents:
                    if content.get('tag') == 'p':
                        texts.append(
                            {'section': sec_title, 'id': content['id'], 'text': content['text']}
                        )
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
