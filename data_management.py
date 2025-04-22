import boto3
import os
import logging
from dotenv import load_dotenv
from botocore.exceptions import NoCredentialsError, ClientError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    if load_dotenv():
        logger.info("Loaded environment variables from .env file.")
    else:
        logger.info("No .env file found or python-dotenv not installed. Relying on existing environment variables.")
except ImportError:
    logger.warning("python-dotenv not installed. Cannot load .env file. Relying on existing environment variables.")


DEFAULT_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME", "learnmate-data-resources")

_s3_client = None
_s3_resource = None

def get_s3_client():
    """Gets a Boto3 S3 client, ensuring credentials are loaded."""
    global _s3_client
    if _s3_client is None:
        try:
            _s3_client = boto3.client('s3')
            _s3_client.list_buckets()
            logger.info("Successfully initialized and verified Boto3 S3 client.")
        except NoCredentialsError:
            logger.error("AWS credentials not found by boto3. Configure environment variables (AWS_ACCESS_KEY_ID, etc.), ~/.aws/credentials, or IAM role.")
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'InvalidAccessKeyId' or error_code == 'SignatureDoesNotMatch':
                 logger.error(f"AWS credentials error: {error_code}. Please check your keys.")
            elif error_code == 'ExpiredToken':
                 logger.error("AWS security token has expired.")
            else:
                 logger.warning(f"Could not verify credentials via list_buckets (may lack permission): {e}. Proceeding, but further errors may occur.")
                 _s3_client = boto3.client('s3')

        except Exception as e:
            logger.error(f"Unexpected error initializing Boto3 S3 client: {e}")
            raise
    return _s3_client


def get_s3_resource():
    """Gets a Boto3 S3 resource."""
    global _s3_resource
    if _s3_resource is None:
        _s3_resource = boto3.resource('s3')
        logger.info("Initialized Boto3 S3 resource.")
    return _s3_resource


def list_files(bucket_name=DEFAULT_BUCKET_NAME, prefix=""):
    """
    Lists all object keys within a specific prefix in the S3 bucket.

    Args:
        bucket_name (str): The name of the S3 bucket. Defaults to DEFAULT_BUCKET_NAME.
        prefix (str): The prefix (folder path) to filter by. Defaults to "".

    Returns:
        list[str]: A list of object keys found under the prefix. Returns empty list on error.
    """
    if not bucket_name or "your-bucket-name-fallback" in bucket_name:
        logger.error("S3 list_files failed: Bucket name is not configured correctly.")
        return []

    logger.info(f"Listing files in s3://{bucket_name}/{prefix}")
    found_files = []
    try:
        s3_client = get_s3_client()
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    object_key = obj['Key']

                    # Exclude keys representing folders
                    if not object_key.endswith('/'):
                        found_files.append(object_key)

        logger.info(f"Found {len(found_files)} files under prefix '{prefix}'.")
        return found_files

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'NoSuchBucket':
            logger.error(f"Bucket not found: {bucket_name}")
        else:
            logger.error(f"AWS ClientError listing files with prefix '{prefix}': {e}")
        return []
    except Exception as e:
        logger.error(f"Error listing files with prefix '{prefix}': {e}")
        return []


def upload_file(local_path, s3_key, bucket_name=DEFAULT_BUCKET_NAME):
    """
    Uploads a single file to S3.

    Args:
        local_path (str): The path to the local file to upload.
        s3_key (str): The desired object key (path) in the S3 bucket.
        bucket_name (str): The name of the S3 bucket. Defaults to DEFAULT_BUCKET_NAME.

    Returns:
        bool: True if upload was successful, False otherwise.
    """
    if not bucket_name or "your-bucket-name-fallback" in bucket_name:
        logger.error(f"S3 upload_file failed for '{local_path}': Bucket name not configured.")
        return False
    if not os.path.exists(local_path):
        logger.error(f"S3 upload_file failed: Local file not found at '{local_path}'")
        return False
    if not os.path.isfile(local_path):
         logger.error(f"S3 upload_file failed: '{local_path}' is not a file.")
         return False

    logger.info(f"Uploading '{local_path}' to s3://{bucket_name}/{s3_key}...")
    try:
        s3_resource = get_s3_resource()
        s3_resource.Bucket(bucket_name).upload_file(local_path, s3_key)
        logger.info(f"Successfully uploaded to s3://{bucket_name}/{s3_key}")
        return True
    except ClientError as e:
        logger.error(f"AWS ClientError uploading file '{local_path}' to '{s3_key}': {e}")
        return False
    except Exception as e:
        logger.error(f"Error uploading file '{local_path}' to '{s3_key}': {e}")
        return False


def upload_folder(local_folder_path, s3_prefix, bucket_name=DEFAULT_BUCKET_NAME):
    """
    Uploads the contents of a local folder recursively to an S3 prefix.

    Args:
        local_folder_path (str): The path to the local folder to upload.
        s3_prefix (str): The desired prefix (folder path) in S3. Should usually end with '/'.
        bucket_name (str): The name of the S3 bucket. Defaults to DEFAULT_BUCKET_NAME.

    Returns:
        bool: True if all uploads were attempted successfully (individual files might still fail),
              False if a major error occurred (e.g., folder not found).
    """
    if not bucket_name or "your-bucket-name-fallback" in bucket_name:
        logger.error(f"S3 upload_folder failed for '{local_folder_path}': Bucket name not configured.")
        return False
    if not os.path.exists(local_folder_path):
        logger.error(f"S3 upload_folder failed: Local folder not found at '{local_folder_path}'")
        return False
    if not os.path.isdir(local_folder_path):
         logger.error(f"S3 upload_folder failed: '{local_folder_path}' is not a directory.")
         return False

    if s3_prefix and not s3_prefix.endswith('/'):
        s3_prefix += '/'

    logger.info(f"Uploading folder '{local_folder_path}' to s3://{bucket_name}/{s3_prefix}...")
    success_count = 0
    fail_count = 0

    for root, _, files in os.walk(local_folder_path):
        for filename in files:
            local_path = os.path.join(root, filename)
            relative_path = os.path.relpath(local_path, local_folder_path)
            s3_key = s3_prefix + relative_path.replace(os.sep, '/')

            if upload_file(local_path, s3_key, bucket_name):
                success_count += 1
            else:
                fail_count += 1

    logger.info(f"Folder upload complete. Succeeded: {success_count}, Failed: {fail_count}")
    return True


def delete_s3_object(s3_key, bucket_name=DEFAULT_BUCKET_NAME):
    """
    Deletes a single object from the S3 bucket.

    Args:
        s3_key (str): The exact object key (path) to delete in S3.
        bucket_name (str): The name of the S3 bucket. Defaults to DEFAULT_BUCKET_NAME from env.

    Returns:
        bool: True if deletion API call was successful, False otherwise.
              Note: S3 delete doesn't error if the object doesn't exist.
    """
    if not bucket_name or "your-bucket-name-fallback" in bucket_name:
        logger.error(f"S3 delete_s3_object failed for '{s3_key}': Bucket name not configured.")
        return False
    if not s3_key:
        logger.error("S3 delete_s3_object failed: s3_key argument cannot be empty.")
        return False
    if s3_key.endswith('/'):
         logger.error(f"S3 delete_s3_object failed: Cannot delete folder marker '{s3_key}'. Delete objects within it.")
         return False

    logger.info(f"Attempting to delete s3://{bucket_name}/{s3_key}...")
    try:
        s3_resource = get_s3_resource()
        s3_resource.Object(bucket_name, s3_key).delete()
        logger.info(f"Successfully issued delete command for s3://{bucket_name}/{s3_key}")
        return True

    except ClientError as e:
        logger.error(f"AWS ClientError deleting object '{s3_key}': {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting object '{s3_key}': {e}")
        return False


def download_s3_object(s3_key, target_local_path, bucket_name=DEFAULT_BUCKET_NAME):
    """
    Downloads a single S3 object if it doesn't exist locally.
    Creates necessary local directories.

    Args:
        s3_key (str): The object key (path) in the S3 bucket.
        target_local_path (str): The desired local path to save the file.
        bucket_name (str): The name of the S3 bucket. Defaults to DEFAULT_BUCKET_NAME.

    Returns:
        bool: True if download was successful or file already exists, False otherwise.
    """
    if not bucket_name or "your-bucket-name-fallback" in bucket_name:
        logger.error(f"S3 download_s3_object failed for '{s3_key}': Bucket name not configured.")
        return False

    # Ignore if file exists locally
    if os.path.exists(target_local_path):
        logger.info(f"Skipping download, file already exists: {target_local_path}")
        return True

    target_dir = os.path.dirname(target_local_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    logger.info(f"Downloading s3://{bucket_name}/{s3_key} to {target_local_path}...")
    try:
        s3_resource = get_s3_resource()
        s3_resource.Bucket(bucket_name).download_file(s3_key, target_local_path)
        logger.info(f"Successfully downloaded {target_local_path}")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404' or error_code == 'NoSuchKey':
             logger.error(f"File not found in S3: s3://{bucket_name}/{s3_key}")
        else:
             logger.error(f"AWS ClientError downloading s3://{bucket_name}/{s3_key}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error downloading s3://{bucket_name}/{s3_key}: {e}")
        return False


def sync_data_from_s3(prefixes_to_sync, bucket_name=DEFAULT_BUCKET_NAME):
    """
    Downloads all files under specified S3 prefixes if they don't exist locally.

    Args:
        prefixes_to_sync (list[str]): List of S3 prefixes (folders) to sync.
        bucket_name (str): The name of the S3 bucket. Defaults to DEFAULT_BUCKET_NAME.
    """
    if not bucket_name or "your-bucket-name-fallback" in bucket_name:
        logger.error("S3 sync_data_from_s3 failed: Bucket name not configured.")
        return

    logger.info(f"Starting data sync from S3 bucket: {bucket_name}")
    total_downloaded = 0
    total_skipped = 0
    total_failed = 0
    total_listed = 0

    for prefix in prefixes_to_sync:
        files_in_prefix = list_files(bucket_name=bucket_name, prefix=prefix)
        total_listed += len(files_in_prefix)
        if not files_in_prefix:
             logger.warning(f"No files found to download under prefix: {prefix}")
             continue

        # Download each object in the folder
        for s3_key in files_in_prefix:
            local_path = s3_key
            if os.path.exists(local_path):
                 logger.info(f"Skipping, file already exists: {local_path}")
                 total_skipped += 1
                 continue

            if download_s3_object(s3_key, local_path, bucket_name):
                total_downloaded += 1
            else:
                total_failed += 1

    logger.info("--- Data Sync Summary ---")
    logger.info(f"Total objects listed across specified prefixes: {total_listed}")
    logger.info(f"Successfully downloaded new files: {total_downloaded}")
    logging.info(f"Skipped (already exist locally): {total_skipped}")
    logging.info(f"Failed downloads: {total_failed}")
    logging.info("-------------------------")
    logging.info("Data sync process finished.")


# Example usage to download all data from S3 for use in local repo
# if __name__ == "__main__":
#     prefixes = ["data/"]
#     sync_data_from_s3(prefixes, bucket_name=DEFAULT_BUCKET_NAME)
