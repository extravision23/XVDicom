from flask import Flask, request, send_from_directory
from werkzeug.utils import secure_filename
import os
import SimpleITK as sitk
from monai.transforms import Compose, LoadImaged, AddChanneld, Resized, ScaleIntensityd, ToTensord
from monai.networks.nets import UNet
from monai.inferers import sliding_window_inference
import vtk
from vtk.util.numpy_support import numpy_to_vtk
import trimesh
from pygltflib import GLTF2, Scene, Node, Mesh, Primitive, Buffer, BufferView, Accessor, BufferTarget, ComponentType, Type

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads/'
PROCESSED_FOLDER = 'processed/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        process_and_save(file_path)
        return "Processing done. File saved."

def process_and_save(file_path):
    # Load DICOM images
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(file_path)
    reader.SetFileNames(dicom_names)
    image = reader.Execute()

    # Apply MONAI transforms for preprocessing
    transforms = Compose([
        AddChanneld(keys=["image"]),
        Resized(keys=["image"], spatial_size=[128, 128, 128]),
        ScaleIntensityd(keys=["image"]),
        ToTensord(keys=["image"])
    ])

    # Load or define a U-Net model
    model = UNet(
        dimensions=3,
        in_channels=1,
        out_channels=2,
        channels=(16, 32, 64, 128, 256),
        strides=(2, 2, 2, 2)
    )

    # Assume model is trained and in evaluation mode
    model.eval()

    with torch.no_grad():
        output = sliding_window_inference(image, (1, 64, 64, 64), 4, model)
        # Assume the bone segmentation is channel 1
        bone_segmentation = output[0][1].detach().cpu().numpy()

    # Convert segmentation to 3D model and save as GLTF
    vtk_image = numpy_to_vtk(bone_segmentation.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
    image_vtk = vtk.vtkImageData()
    image_vtk.SetDimensions(image.GetSize())
    image_vtk.GetPointData().SetScalars(vtk_image)

    # Convert to mesh using VTK
    surf = vtk.vtkDiscreteMarchingCubes()
    surf.SetInputData(image_vtk)
    surf.SetValue(0, 1)  # Assuming the bone label is 1
    surf.Update()

    # Convert VTK mesh to trimesh and save as GLTF
    mesh = trimesh.Trimesh(vtk_to_numpy(surf.GetOutput().GetPoints().GetData()),
                           faces=vtk_to_numpy(surf.GetOutput().GetPolys().GetData()))
    processed_path = os.path.join(PROCESSED_FOLDER, 'model.gltf')
    mesh.export(processed_path)

@app.route('/download')
def download_file():
    return send_from_directory(directory=PROCESSED_FOLDER, filename='model.gltf')

if __name__ == '__main__':
    app.run(debug=True)
