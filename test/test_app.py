import pytest
from app.main import app  # adjust this import according to your application structure

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_recognize_image_no_file(client):
    """ Test recognize_image endpoint without an image file. """
    response = client.post('/image')
    assert response.status_code == 400
    assert 'Image is required.' in response.json['response']

def test_recognize_image_with_file(client, mocker):
    """ Test recognize_image endpoint with a mock image file. """
    class MockFile:
        def read(self):
            return b'mock data'  # assuming this is how your image data looks like

    mocker.patch('PIL.Image.open')  # Mock PIL Image.open to not actually open a file
    response = client.post('/image', data={'image': MockFile()})
    assert response.status_code == 200
    assert 'dominant_color' in response.json['response']

def test_query_images_missing_params(client):
    """ Test query_images endpoint with missing parameters. """
    response = client.get('/query')
    assert response.status_code == 400
    assert 'All parameters (quantity, type, color) are required.' in response.json['response']

def test_query_images(client, mocker):
    """ Test query_images with mocked S3 responses. """
    mocker.patch('boto3.client')  # Mock boto3 S3 client

    class MockS3Client:
        def list_objects_v2(self, Bucket, Prefix):
            return {
                'Contents': [
                    {'Key': 'Tomato/#ff0000_1.jpg'},
                    {'Key': 'Tomato/#ff0000_2.jpg'}
                ]
            }

    mocker.patch('app.main.boto3.client', return_value=MockS3Client())
    response = client.get('/query?quantity=1&type=Tomato&color=#ff0000')
    assert response.status_code == 200
    assert 'https://vegetables.s3.me-central-1.amazonaws.com/Tomato/#ff0000_1.jpg' in response.json['images']
    assert len(response.json['images']) == 1  # Ensure only one image is returned as per 'quantity'