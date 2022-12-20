import os
import xml.etree.ElementTree as ET
import zipfile

import boto3


class Bucket:
    def __init__(
        self,
        bucket_name: str,
        access_key=None,
        secret_key=None,
        requester_pays='True',
        prefix='',
    ):
        # Create an S3 client using the given access and secret keys
        self.s3_client = boto3.client(
            's3', aws_access_key_id=access_key, aws_secret_access_key=secret_key
        )

        self.bucket_name = bucket_name
        self.requester_pays = requester_pays
        self.prefix = prefix

    def list_objects(self):
        # List the objects in the bucket, with the given prefix and requester pays flag
        paginator = self.s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=self.bucket_name, Prefix=self.prefix, RequestPayer='requester'
        )
        for page in page_iterator:
            for object in page['Contents']:
                yield object

    def download_object(self, object_key, filename):
        # DOESNT WORK
        # Download the given object from the bucket and save it to the given filename
        self.s3_client.download_file(
            Bucket=self.bucket_name,
            Key=object_key,
            Filename=filename,
            ExtraArgs={'RequestPayer': self.requester_pays},
        )

        # Return the manuscript title and the files

    def parse_manifest(self, zip_filename):
        # Extract the zip file and parse the manifest.xml file
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall()
        tree = ET.parse('manifest.xml')
        root = tree.getroot()

        # Return the manuscript title and the files in the content folder
        title = root.find('./title')
        files = []
        for file in root.findall('./file'):
            name = file.find('name').text
            size = file.find('size').text
            files.append((name, size))
        return title.text, files

    def cleanup(self, zip_filename):
        # Clean up the extracted files
        zip_ref.close()
        os.remove(zip_filename)
        os.remove('manifest.xml')


# Example usage


# Set the bucket name and the requester pays flag
bucket_name = 'biorxiv-src-monthly'
requester_pays = True

# Set the prefix to filter the objects by
prefix = ''

# Create a Bucket instance
bucket = Bucket(bucket_name=bucket_name)

objects = bucket.list_objects()
