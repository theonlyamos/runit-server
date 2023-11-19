const fileInput = document.getElementById('profile-image');
let previewImage = document.getElementById('image-preview');
let imagePlaceholder = document.getElementById('image-placeholder');

fileInput.addEventListener('change', (event) => {
  const file = event.target.files[0];
  if (file.type.match(/image.*/)) {
    const reader = new FileReader();
    reader.addEventListener('load', (event) => {
      previewImage.src = event.target.result;
      previewImage.classList.remove('d-none');
      imagePlaceholder.classList.add('d-none')
    });
    reader.readAsDataURL(file);
    uploadImage(file)
  } else {
    alert('Please select an image file.');
  }
});

const uploadImage = (file)=>{

    if (!file) {
        alert('Please select a file to upload.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/account/image');
    xhr.upload.addEventListener('progress', (event) => {
        const progress = event.loaded / event.total * 100;
        console.log(`Upload progress: ${progress}%`);
    });

    xhr.onload = () => {
        if (xhr.status === 200) {
        alert('File uploaded successfully.');
        } else {
        alert('Error uploading file.');
        }
    };

    xhr.on

    xhr.send(formData);
}