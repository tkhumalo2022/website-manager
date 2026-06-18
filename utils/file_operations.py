import os
from typing import Optional, Union

def read_file_content(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """
    Reads the entire content of a text file.

    Args:
        file_path: The path to the file to read.
        encoding: The encoding to use when reading the file (default: 'utf-8').

    Returns:
        The content of the file as a string, or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return None
    except IOError as e:
        print(f"Error reading file '{file_path}': {e}")
        return None
    except UnicodeDecodeError:
        print(f"Error: Could not decode file '{file_path}' with encoding '{encoding}'. "
              "Try a different encoding.")
        return None

def get_file_name(file_path: str, include_extension: bool = True) -> str:
    """
    Extracts the file name from a given path.

    Args:
        file_path: The full path to the file.
        include_extension: If True, includes the file extension; otherwise, removes it.

    Returns:
        The file name (with or without extension).
    """
    base_name = os.path.basename(file_path)
    if not include_extension:
        return os.path.splitext(base_name)[0]
    return base_name

def get_file_extension(file_path: str) -> str:
    """
    Extracts the file extension from a given path.

    Args:
        file_path: The full path to the file.

    Returns:
        The file extension, including the dot (e.g., ".txt"), or an empty string if no extension.
    """
    return os.path.splitext(file_path)[1]

def get_directory_path(file_path: str) -> str:
    """
    Extracts the directory path from a given file path.

    Args:
        file_path: The full path to the file.

    Returns:
        The directory path.
    """
    return os.path.dirname(file_path)

def join_paths(*paths: str) -> str:
    """
    Joins multiple path components intelligently.

    Args:
        *paths: Variable number of path components to join.

    Returns:
        The combined path.
    """
    return os.path.join(*paths)

def file_exists(file_path: str) -> bool:
    """
    Checks if a file exists at the given path.

    Args:
        file_path: The path to the file.

    Returns:
        True if the file exists and is a regular file, False otherwise.
    """
    return os.path.isfile(file_path)

def get_file_size(file_path: str) -> Optional[int]:
    """
    Returns the size of a file in bytes.

    Args:
        file_path: The path to the file.

    Returns:
        The size of the file in bytes, or None if the file does not exist or
        its size cannot be determined.
    """
    try:
        return os.path.getsize(file_path)
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return None
    except OSError as e:
        print(f"Error getting size of file '{file_path}': {e}")
        return None

if __name__ == "__main__":
    # Create a dummy file for testing
    test_dir = "temp_test_files"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    test_file_path = os.path.join(test_dir, "example_content.txt")
    binary_test_file_path = os.path.join(test_dir, "binary_data.bin")
    
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("This is a test file.\n")
        f.write("It contains some example content for file operations.")
    
    with open(binary_test_file_path, "wb") as f:
        f.write(b'\x01\x02\x03\x04\x05')

    print("--- Testing file_operations.py ---")

    # Test read_file_content
    print("\n1. Testing read_file_content:")
    content = read_file_content(test_file_path)
    if content:
        print(f"Content of '{test_file_path}':\n{content}")
    
    non_existent_file = os.path.join(test_dir, "non_existent.txt")
    read_file_content(non_existent_file) # Should print error

    # Test get_file_name
    print("\n2. Testing get_file_name:")
    path1 = "/home/user/docs/report.pdf"
    path2 = "my_image.jpg"
    print(f"File name (with ext) of '{path1}': {get_file_name(path1)}")
    print(f"File name (no ext) of '{path1}': {get_file_name(path1, False)}")
    print(f"File name (with ext) of '{path2}': {get_file_name(path2)}")
    print(f"File name (no ext) of '{path2}': {get_file_name(path2, False)}")

    # Test get_file_extension
    print("\n3. Testing get_file_extension:")
    print(f"Extension of '{path1}': {get_file_extension(path1)}")
    print(f"Extension of '{path2}': {get_file_extension(path2)}")
    print(f"Extension of 'archive.tar.gz': {get_file_extension('archive.tar.gz')}")
    print(f"Extension of 'noextensionfile': {get_file_extension('noextensionfile')}")

    # Test get_directory_path
    print("\n4. Testing get_directory_path:")
    print(f"Directory of '{path1}': {get_directory_path(path1)}")
    print(f"Directory of '{test_file_path}': {get_directory_path(test_file_path)}")
    print(f"Directory of 'simple_file.txt': {get_directory_path('simple_file.txt')}")

    # Test join_paths
    print("\n5. Testing join_paths:")
    joined = join_paths("/usr", "local", "bin", "my_app")
    print(f"Joined paths '/usr', 'local', 'bin', 'my_app': {joined}")
    joined_relative = join_paths(test_dir, "subdir", "another.txt")
    print(f"Joined paths '{test_dir}', 'subdir', 'another.txt': {joined_relative}")

    # Test file_exists
    print("\n6. Testing file_exists:")
    print(f"Does '{test_file_path}' exist? {file_exists(test_file_path)}")
    print(f"Does '{non_existent_file}' exist? {file_exists(non_existent_file)}")
    print(f"Does '{test_dir}' exist as a file? {file_exists(test_dir)}") # Should be False for a directory

    # Test get_file_size
    print("\n7. Testing get_file_size:")
    size = get_file_size(test_file_path)
    if size is not None:
        print(f"Size of '{test_file_path}': {size} bytes")
    size_binary = get_file_size(binary_test_file_path)
    if size_binary is not None:
        print(f"Size of '{binary_test_file_path}': {size_binary} bytes")
    get_file_size(non_existent_file) # Should print error

    # Cleanup dummy files
    os.remove(test_file_path)
    os.remove(binary_test_file_path)
    os.rmdir(test_dir)
    print(f"\nCleaned up '{test_dir}' directory and test files.")
    print("--- End of tests ---")