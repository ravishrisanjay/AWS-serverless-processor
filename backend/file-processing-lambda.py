import boto3
import urllib.parse
import json
import os
import io
import zipfile
from PIL import Image

s3 = boto3.client('s3')
OUT_BUCKET = 'ssking-out' # Ensure this matches your actual bucket name

def lambda_handler(event, context):
    print("Starting processing...")
    
    for record in event['Records']:
        # 1. Parse the SQS Message
        payload = record['body']
        s3_event = json.loads(payload)
        
        # Safety check: Ignore test events
        if 'Records' not in s3_event: 
            print("Not a valid S3 event. Skipping.")
            continue

        s3_record = s3_event['Records'][0]
        in_bucket = s3_record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(s3_record['s3']['object']['key'])
        
        print(f"--- Processing File: {key} ---")

        # 2. Get the File and Metadata from S3
        try:
            response = s3.get_object(Bucket=in_bucket, Key=key)
            file_content = response['Body'].read()
            
            # READ METADATA: We look for 'resize'. 
            # Note: S3 makes all metadata keys lowercase.
            # Default to 800px if you didn't send the header in Postman.
            target_size = int(response['Metadata'].get('resize', 800))
            print(f"Target Size (Width) from Metadata: {target_size}px")
            
        except Exception as e:
            print(f"Error reading file from S3: {e}")
            continue

        # 3. Check File Extension
        name, ext = os.path.splitext(key)
        ext = ext.lower()

        # 4. Route to correct logic
        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
            process_image(key, file_content, target_size)
            
        elif ext in ['.pdf', '.docx', '.doc', '.txt']:
            zip_name = name + '.zip'
            process_zip(key, zip_name, file_content)
        
        else:
            print(f"File type {ext} not supported. Skipping.")

    return "Job Done"

# --- LOGIC 1: IMAGE COMPRESSION & RESIZING ---
def process_image(key, content, target_width):
    try:
        # Load image from memory
        with Image.open(io.BytesIO(content)) as img:
            
            # Calculate new height to keep aspect ratio
            # (Original Height / Original Width) * Target Width
            aspect_ratio = img.height / img.width
            new_height = int(target_width * aspect_ratio)
            
            print(f"Resizing from {img.width}x{img.height} to {target_width}x{new_height}")

            # Resize using high-quality resampling
            img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
            
            # Handle Transparency: If PNG/RGBA, convert to RGB for JPEG saving
            if img.mode in ("RGBA", "P"): 
                img = img.convert("RGB")
            
            # Save to buffer (Compression happens here!)
            out_buffer = io.BytesIO()
            # optimize=True and quality=85 drastically reduces file size
            img.save(out_buffer, format='JPEG', optimize=True, quality=85)
            out_buffer.seek(0)
            
            # Upload to Output Bucket
            # We save everything as .jpg for consistency
            new_key = os.path.splitext(key)[0] + ".jpg"
            s3.put_object(
                Bucket=OUT_BUCKET, 
                Key=new_key, 
                Body=out_buffer, 
                ContentType='image/jpeg'
            )
            print(f"Success! Saved resized image to: {new_key}")

    except Exception as e:
        print(f"Image Processing Error: {e}")

# --- LOGIC 2: ZIPPING DOCUMENTS ---
def process_zip(original_filename, zip_filename, content):
    try:
        print(f"Zipping {original_filename} into {zip_filename}...")
        
        # Create a Zip file in memory
        zip_buffer = io.BytesIO()
        
        # 'w' mode writes a new zip file. ZIP_DEFLATED compresses it.
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Write the original file content into the zip
            # arcname is the name the file will have INSIDE the zip
            zf.writestr(original_filename, content)
        
        zip_buffer.seek(0)
        
        # Upload Zip to Output Bucket
        s3.put_object(
            Bucket=OUT_BUCKET, 
            Key=zip_filename, 
            Body=zip_buffer, 
            ContentType='application/zip'
        )
        print(f"Success! Saved zip to: {zip_filename}")

    except Exception as e:
        print(f"Zip Processing Error: {e}")