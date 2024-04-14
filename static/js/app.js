const element = document.getElementById('dicomViewer');
cornerstone.enable(element);

function loadAndDisplayImage(imageId) {
    cornerstone.loadImage(imageId).then(function(image) {
        const viewport = cornerstone.getDefaultViewportForImage(element, image);
        cornerstone.displayImage(element, image, viewport);
    }, function(err) {
        console.error('Error loading DICOM image:', err);
    });
}

function loadSeries(filePaths) {
    let imageIds = filePaths.map(fp => `wadouri:http://localhost:5000/dicom/${fp}`);
    // Load first image
    loadAndDisplayImage(imageIds[0]);
}

function nextImage() {
    // Functionality to navigate to next image in series
}

function previousImage() {
    // Functionality to navigate to previous image in series
}
