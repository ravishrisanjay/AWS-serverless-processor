import boto3
import json
import os

s3 = boto3.client('s3')

# --- CONFIGURATION ---
IN_BUCKET = 'ssking-in'   
OUT_BUCKET = 'ssking-out' 

def lambda_handler(event, context):
    try:
        # 1. Parse Input
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename')
        # Ensure size is a string for metadata
        target_size = str(body.get('size', '800')) 
        
        # --- FIX: Get file type from frontend or default to binary ---
        file_type = body.get('fileType', 'application/octet-stream')

        if not filename: 
            return {'statusCode': 400, 'body': json.dumps({'error': 'No filename provided'})}

        # 2. Predict Output Name
        name, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if ext in ['.pdf', '.docx', '.doc', '.txt']:
            download_filename = name + '.zip'
        else:
            download_filename = filename

        # 3. Generate Upload Link
        # We MUST include the ContentType here so S3 expects it during the upload
        up_link = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': IN_BUCKET, 
                'Key': filename,
                'Metadata': {'resize': target_size},
                'ContentType': file_type  # <--- The Critical Fix
            },
            ExpiresIn=300
        )

        # 4. Generate Download Link
        down_link = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': OUT_BUCKET, 'Key': download_filename},
            ExpiresIn=3600
        )

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'up': up_link,
                'down': down_link
            })
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }