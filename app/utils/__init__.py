def hash_file_md5(user_id: str, contents: bytes):
    """
    Generate an MD5 hash for the given file contents.

    Args:
        user_id (str): The ID of the user uploading the file.
        contents (bytes): The contents of the file to hash.

    Returns:
        str: The MD5 hash of the file contents.
    """
    import hashlib

    md5_hash = hashlib.md5()
    md5_hash.update(bytes(user_id, "UTF-8"))
    md5_hash.update(contents)
    return md5_hash.hexdigest()
