from utils import generate_key, encrypt_content, decrypt_content
import os, hashlib, cv2, numpy as np, json, struct

# Function to get the hash of a file
def file_hash(file_path: str) -> bytes:
    """This fucntion will get the hash of the file and will return the hash"""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.digest()

# helper function to open image
def open_image(image_path: str) -> np.ndarray:
    """Opens an image from the given file path using OpenCV."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    return image

################################ Steganography Helpers ################################
def embed_lsb(image: np.ndarray, encrypted_data: bytes, header: dict) -> np.ndarray:
    """
    Embed encrypted data and header into an image using LSB steganography.
    Parameters
    ----------
    image : np.ndarray
        Input image (H, W, C) uint8
    encrypted_data : bytes
        Encrypted payload to embed
    header : dict
        Metadata required for decryption
    Returns
    -------
    np.ndarray
        Stego image with embedded payload
    Raises
    ------
    ValueError
        If the image does not have enough capacity
    """
    if image.dtype != np.uint8:
        raise ValueError("Image must be uint8")
    if image.ndim != 3:
        raise ValueError("Image must be H x W x C")
    # --- Serialize header ---
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    header_size = len(header_json)
    # --- Payload format ---
    # [4 bytes header_size][header_json][encrypted_data]
    payload = (
        struct.pack(">I", header_size) +
        header_json +
        encrypted_data
    )
    # --- Convert payload to bitstream ---
    payload_bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    # --- Calculate capacity ---
    h, w, c = image.shape
    capacity_bits = h * w * c  # 1 bit per channel
    if payload_bits.size > capacity_bits:
        raise ValueError(
            f"Payload too large: {payload_bits.size} bits > {capacity_bits} bits"
        )
    # --- Flatten image ---
    flat_image = image.flatten()
    # --- Clear LSB and embed payload ---
    flat_image[:payload_bits.size] &= 0b11111110
    flat_image[:payload_bits.size] |= payload_bits
    # --- Reshape back to image ---
    stego_image = flat_image.reshape(image.shape)
    return stego_image

def decode_lsb(stego_image: np.ndarray) -> tuple[dict, bytes]:
    """
    Decode and extract header and encrypted data from an LSB-stego image.
    Parameters
    ----------
    stego_image : np.ndarray
        Image containing embedded payload (H, W, C) uint8
    Returns
    -------
    tuple[dict, bytes]
        (header, encrypted_data)
    Raises
    ------
    ValueError
        If extraction fails or data is corrupted
    """
    if stego_image.dtype != np.uint8:
        raise ValueError("Image must be uint8")
    if stego_image.ndim != 3:
        raise ValueError("Image must be H x W x C")
    flat_image = stego_image.flatten()
    # --- Extract LSBs ---
    lsb_bits = flat_image & 1
    # --- Convert bits to bytes ---
    all_bytes = np.packbits(lsb_bits).tobytes()
    # --- Read header size (first 4 bytes) ---
    if len(all_bytes) < 4:
        raise ValueError("Corrupted data: insufficient length")
    header_size = struct.unpack(">I", all_bytes[:4])[0]
    # --- Read header ---
    header_start = 4
    header_end = header_start + header_size
    if len(all_bytes) < header_end:
        raise ValueError("Corrupted data: incomplete header")
    header_json = all_bytes[header_start:header_end]
    try:
        header = json.loads(header_json.decode("utf-8"))
    except Exception:
        raise ValueError("Failed to decode header JSON")
    # --- Read encrypted payload ---
    payload_start = header_end
    payload_size = header.get("binary_size")
    if payload_size is None:
        raise ValueError("Header missing 'binary_size'")
    payload_end = payload_start + payload_size
    if len(all_bytes) < payload_end:
        raise ValueError("Corrupted data: incomplete payload")
    encrypted_data = all_bytes[payload_start:payload_end]
    return header, encrypted_data

################################ Main Function Handlers ################################
def encrypt_file(file_path: str, master_password: str, image_path: str) -> tuple[bool, str]:
    """This function will read the file and will encrypt the file and convert the data into an image or video"""
    # generate key form the master pass
    key, salt = generate_key(master_password)
    # get the hash of the file
    file_hash_value = file_hash(file_path)
    # open imnage
    image = open_image(image_path)
    # read the file content
    with open(file_path, 'rb') as file:
        content = file.read()
    # encrypt the content
    encrypted_data, iv = encrypt_content(content, key)
    # create a header with salt and iv and hash of the file
    header = {
        'file_name': os.path.basename(file_path),
        'file_hash': file_hash_value.hex(),
        'salt': salt.hex(),
        'iv': iv.hex(),
        'binary_size': len(encrypted_data)
    }
    # embed the encrypted data into the image using LSB
    embedded_image = embed_lsb(image, encrypted_data, header)
    # save the stego image
    output_path = f'{os.path.basename(image_path).split(".")[0]}.png'
    cv2.imwrite(output_path, embedded_image)
    # return success message
    return True, output_path

def decrypt_file(stego_image_path: str, master_password: str, output_path: str) -> tuple[bool, str]:
    """This function will decrypt the stego image and will extract the original file"""
    # open stego image
    stego_image = open_image(stego_image_path)
    # decode the lsb to get header and encrypted data
    header, encrypted_data = decode_lsb(stego_image)
    # retrieve salt and iv from header
    salt = bytes.fromhex(header['salt'])
    iv = bytes.fromhex(header['iv'])
    # generate key from master password and salt
    key, _ = generate_key(master_password, salt)
    # decrypt the content
    decrypted_data = decrypt_content(encrypted_data, key, iv)
    # verify file hash
    file_hash_value = hashlib.sha256(decrypted_data).hexdigest()
    if file_hash_value != header['file_hash']:
        raise ValueError("File hash mismatch! Decryption failed or data corrupted.")
    # write the decrypted data to output file
    output_path = os.path.join(os.path.dirname(output_path), header['file_name'])
    with open(output_path, 'wb') as output_file:
        output_file.write(decrypted_data)
    return True, "File decrypted successfully."

if __name__ == "__main__":
    success, _ = encrypt_file('input/1.docx', 'my_master_password', 'board.png')
    if success:
        output_path = _
        success, message = decrypt_file(output_path, 'my_master_password', 'output_dir/')
        if success:
            print(message)
        else:
            print(message)
    else:
        print(_)
