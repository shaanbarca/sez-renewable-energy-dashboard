import boto3

from config.settings import Config

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            's3',
            aws_access_key_id=Config.S3_ACCESS_KEY,
            aws_secret_access_key=Config.S3_SECRET_ACCESS_KEY,
            region_name='eu-north-1',
            endpoint_url='https://s3.eu-north-1.amazonaws.com',
        )
    return _s3_client


def list_bucket_content(bucket=None, folder_loc=None):
    s3 = _get_s3()
    objects = s3.list_objects_v2(Bucket=bucket, Prefix=folder_loc)
    content = []
    
    for obj in objects['Contents']:
        item = obj['Key'].split(f"{folder_loc}/")[-1]
        if len(item)>0:
            content.append(item)

    return content


def list_folders_in_bucket(bucket=None, folder_loc=None):
    """
    List all "folders" (keys with a common prefix) in an S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket.

    Returns:
        list: A list of folder names.
    """

    try:
        s3 = _get_s3()
        objects = s3.list_objects_v2(Bucket=bucket, Prefix=folder_loc)
        content = []

        for obj in objects['Contents']:
            item = obj['Key'].split(f"{bucket}/{folder_loc}/")[-1]
            if len(item) > 0:
                content.append(item)

        return [f.split("/")[0] for f in content]
    except Exception as e:
        print(f"Error listing folders in bucket: {e}")
        return []


def generate_presigned_s3_url(bucket_name, key, expiration=3600):
    """
    Generate a pre-signed URL for an S3 object.

    Parameters:
    - bucket_name: The name of the S3 bucket.
    - key: The key of the S3 object.
    - expiration: Time in seconds for the URL to expire.

    Returns:
    - str: The pre-signed URL of the S3 object.
    """
    try:
        s3 = _get_s3()
        response = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': key},
                                             ExpiresIn=expiration)
        return response
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None