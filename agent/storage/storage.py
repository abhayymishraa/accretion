"""Private object storage. Provider SDKs own authentication, checksums and retries."""
import os
import asyncio

from ..sandbox.archive import MAX_ARCHIVE


class StorageError(Exception):
    pass


_transfers = asyncio.Semaphore(2)


async def storage_call(method, *args):
    # Cancel the caller promptly, but retain the slot until the SDK thread actually exits.
    await _transfers.acquire()
    def operation():
        try:
            return getattr(ObjectStore(), method)(*args)
        except StorageError:
            raise
        except Exception:
            raise StorageError('Private storage configuration or operation failed') from None
    task = asyncio.create_task(asyncio.to_thread(operation))
    def release(done):
        _transfers.release()
        if not done.cancelled():
            done.exception()  # Retrieve failures even when the HTTP/run caller was cancelled.
    task.add_done_callback(release)
    return await asyncio.shield(task)


class ObjectStore:
    def __init__(self):
        self.provider = os.getenv('STORAGE_PROVIDER', 'minio')
        self.bucket = os.environ['STORAGE_BUCKET']
        if self.provider == 'gcs':
            from google.cloud import storage
            self.client = storage.Client()
        elif self.provider == 'minio':
            import boto3
            from botocore.config import Config
            self.client = boto3.client('s3', endpoint_url=os.environ['MINIO_ENDPOINT'],
                aws_access_key_id=os.environ['MINIO_ACCESS_KEY'],
                aws_secret_access_key=os.environ['MINIO_SECRET_KEY'], region_name='us-east-1',
                config=Config(connect_timeout=5, read_timeout=20, retries={'max_attempts': 2},
                              s3={'addressing_style': 'path'}))
        else:
            raise StorageError('Use gcs or minio for STORAGE_PROVIDER')

    def read(self, key, limit=MAX_ARCHIVE):
        try:
            if self.provider == 'gcs':
                # Inclusive range bounds response memory even for unexpectedly large objects.
                data = self.client.bucket(self.bucket).blob(key).download_as_bytes(end=limit, timeout=20)
            else:
                response = self.client.get_object(Bucket=self.bucket, Key=key, Range=f'bytes=0-{limit}')
                with response['Body'] as body:
                    data = body.read(limit + 1)
            if len(data) > limit:
                raise StorageError('Stored object exceeds its size limit')
            return data
        except Exception as exc:
            if isinstance(exc, StorageError):
                raise
            raise StorageError('Private storage read failed') from None

    def put(self, key, data, content_type='application/zip'):
        if len(data) > MAX_ARCHIVE:
            raise StorageError('Stored object exceeds its size limit')
        try:
            if self.provider == 'gcs':
                from google.api_core.exceptions import PreconditionFailed
                try:
                    self.client.bucket(self.bucket).blob(key).upload_from_string(data,
                        content_type=content_type, if_generation_match=0, checksum='crc32c', timeout=20)
                except PreconditionFailed:
                    if self.read(key) != data:
                        raise StorageError('Immutable object checksum conflict')
            else:
                from botocore.exceptions import ClientError
                try:
                    self.client.put_object(Bucket=self.bucket, Key=key, Body=data,
                        ContentType=content_type, IfNoneMatch='*', ChecksumAlgorithm='SHA256')
                except ClientError as exc:
                    if exc.response['ResponseMetadata']['HTTPStatusCode'] != 412:
                        raise
                    if self.read(key) != data:
                        raise StorageError('Immutable object checksum conflict')
        except Exception as exc:
            if isinstance(exc, StorageError):
                raise
            raise StorageError('Private storage upload failed; previous checkpoint is preserved') from None

    def delete(self, key):
        try:
            if self.provider == 'gcs':
                from google.api_core.exceptions import NotFound
                # Delete every generation, including noncurrent versions. Exact-name
                # filtering is essential: a prefix may also match another object.
                for blob in self.client.list_blobs(self.bucket, prefix=key, versions=True, timeout=20):
                    if blob.name != key:
                        continue
                    try:
                        blob.delete(if_generation_match=blob.generation, timeout=20)
                    except NotFound:
                        pass
            else:
                pages = self.client.get_paginator('list_object_versions').paginate(Bucket=self.bucket, Prefix=key)
                for page in pages:
                    for version in page.get('Versions', []) + page.get('DeleteMarkers', []):
                        if version['Key'] == key:
                            self.client.delete_object(Bucket=self.bucket, Key=key, VersionId=version['VersionId'])
        except Exception:
            raise StorageError('Private storage delete failed') from None
