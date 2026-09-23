"""Create the private local development bucket. Never creates a production bucket."""
from urllib.parse import urlparse
from .storage import ObjectStore


def main():
    import os
    if os.getenv('STORAGE_PROVIDER') != 'minio' or urlparse(os.getenv('MINIO_ENDPOINT', '')).hostname not in {'localhost', '127.0.0.1'}:
        raise SystemExit('This command only initializes local MinIO')
    store = ObjectStore()
    from botocore.exceptions import ClientError
    try:
        store.client.create_bucket(Bucket=store.bucket)
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'BucketAlreadyOwnedByYou':
            raise SystemExit('Could not create local bucket; check credentials and container') from None
    # Fresh buckets are private. Refuse to use an existing bucket with a public policy.
    try:
        store.client.get_bucket_policy(Bucket=store.bucket)
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'NoSuchBucketPolicy':
            raise SystemExit('Could not inspect local bucket policy') from None
    else:
        raise SystemExit('Existing bucket has a policy. Review it before using it for private projects.')
    print('Private local project bucket ready')


if __name__ == '__main__':
    main()
