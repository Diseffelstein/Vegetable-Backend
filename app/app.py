from flask import Flask, request, jsonify
import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import logging

app = Flask(__name__)

logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('botocore').setLevel(logging.DEBUG)
logging.getLogger('s3transfer').setLevel(logging.DEBUG)

region_name = 'eu-west-2'
bucket_name = 'vegetables-recognition'

# Load your ONNX model
ort_session = ort.InferenceSession('model.onnx')

def transform_image(image_bytes):
    # Convert the image to the format your model expects
    image = Image.open(io.BytesIO(image_bytes))
    image = image.resize((299, 299))  # Example resize, adjust to your model's input
    image = np.array(image).astype('float32')
    image = np.transpose(image, (2, 0, 1))  # Change to CxHxW
    image = np.expand_dims(image, axis=0)  # Add batch dimension
    return image

def get_prediction(image_bytes):
    # Transform the image for your model
    image = transform_image(image_bytes)
    # Run inference
    inputs = {ort_session.get_inputs()[0].name: image}
    ort_outs = ort_session.run(None, inputs)
    pred = np.argmax(ort_outs[0], axis=1)
    # Convert your model's prediction to a readable format
    dominant_color = "#4239ba"
    return {
        "class": int(pred[0].item()),
        "dominant_color": dominant_color
    }

# Load a user image of a vegetable and receive output of its markup
# by type (obtained through the inference session) and color
# (calculated through the algorithm implementation).
@app.route('/image', methods=['POST'])
def recognize_image():
    if 'image' not in request.files:
        return jsonify({'response': 'Image is required.'}), 400
    image_file = request.files['image']
    img_bytes = image_file.read()
    prediction = get_prediction(img_bytes)
    return jsonify({'response': prediction})

# Send a query with a combination of parameters "quantity + type + color"
# and receive output of images of vegetables matching the provided
# combination of parameters. Provide adequate visualization of the lack
# of suitable images in the database.
@app.route('/query', methods=["GET"])
def query_images():
    quantity = request.args.get('quantity', type=int)
    veg_type = request.args.get('type', default="")
    color = request.args.get('color', default="")

    # Ensure all parameters are provided
    if quantity is None or veg_type == "" or color == "":
        return jsonify({'response': 'All parameters (quantity, type, color) are required.'}), 400

    # Connect to S3 and retrieve files
    s3_client = boto3.client('s3', region_name=region_name)
    try:
        # Generate prefix based on vegetable type to filter results
        prefix = f"{veg_type}/"
        print(prefix)
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        # Filter files by color and limit by quantity
        matching_files = []
        for obj in response.get('Contents', []):
            print(obj)
            matching_files.append(f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{obj['Key']}")
            if len(matching_files) >= quantity:
                break
            # file_color = obj['Key'].split('/')[-1].split('_')[1]  # Assumes file name format "type_color.jpg"
            # if file_color.lower() == color.lower():

        if not matching_files:
            return jsonify({'response': 'No suitable images found.'}), 404

        return jsonify(matching_files)

    except (NoCredentialsError, PartialCredentialsError) as e:
        return jsonify({'response': 'AWS credentials are not configured properly.'}), 500
    except Exception as e:
        print(e)
        return jsonify({'response': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

# What does the class IDs map to?
# 1 => potato?
# 2 => ???




