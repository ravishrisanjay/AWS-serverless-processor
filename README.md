# ⚡ AWS Serverless File Processor

A fully serverless, event-driven file processing application built on AWS. This project demonstrates a decoupled architecture using React, AWS Lambda, S3, and SQS to handle image optimization and document compression at scale.

## 🎥 Project Demo
> *Note: The live AWS backend services for this demo are currently paused to minimize cloud costs. Please view the video above to see the full event-driven workflow in action.*

## 🏗️ Architecture

![Architecture Diagram](./assets/architecture_diagram.png)

### The Event-Driven Workflow:
1.  **Frontend:** A React application hosted on **AWS S3** (Static Website Hosting).
2.  **Auth/API:** The app requests a secure **Presigned URL** from an **AWS Lambda** function (via Function URL).
3.  **Upload:** The browser uploads the file directly to the **S3 Input Bucket** (bypassing the server for efficiency).
4.  **Event Trigger:** S3 detects the new file and sends an event notification to **Amazon SQS** (Simple Queue Service).
5.  **Processing:** The SQS message triggers the **Processing Lambda**, which checks the file type:
    * **Images:** Resized to a target width.
    * **Documents (.pdf, .docx):** Compressed into a `.zip` archive.
6.  **Storage:** The processed file is saved to the **S3 Output Bucket**.
7.  **Retrieval:** The frontend polls the output bucket using a signed URL to allow the user to download the result.

## 🛠️ Tech Stack
* **Frontend:** React.js, Tailwind CSS (via CDN), Axios
* **Compute:** AWS Lambda (Python 3.9)
* **Storage:** Amazon S3 (Input/Output Buckets + Static Hosting)
* **Integration:** Amazon SQS (Event decoupling)
* **SDK:** Boto3 (AWS SDK for Python)

## 💡 Key Challenges & Solutions

### 1. The "Signature Mismatch" Error
**The Problem:**
During the development of the direct-to-S3 upload feature, I consistently received `403 Forbidden` errors, even though my IAM permissions were correct. The error message was `SignatureDoesNotMatch`.

**The Debugging:**
I discovered that Axios automatically attaches a `Content-Type` header (e.g., `image/jpeg`) based on the file input. However, my Python Lambda was generating the signature without specifying a Content-Type. In AWS Signature V4, the headers used to *create* the signature must match the headers sent during the *request* exactly.

**The Solution:**
I refactored the backend to accept the `fileType` from the frontend request and enforce it in the `generate_presigned_url` parameters.
```python
# Backend Fix
up_link = s3.generate_presigned_url(
    'put_object',
    Params={..., 'ContentType': file_type} # Enforcing the type
)
