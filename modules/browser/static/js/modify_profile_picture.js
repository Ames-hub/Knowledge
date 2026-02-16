// Profile picture functionality
function changeProfilePicture(cfid) {
  const modal = document.getElementById('profile-picture-modal');
  modal.style.display = 'flex';
}

function closeProfilePictureModal() {
  const modal = document.getElementById('profile-picture-modal');
  modal.style.display = 'none';
  document.getElementById('profile-picture-input').value = '';
}

// Handle profile picture form submission
document.getElementById('profile-picture-form').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const fileInput = document.getElementById('profile-picture-input');
  const cfid = document.getElementById('profile-cfid').value;
  
  if (!fileInput.files[0]) {
    alert('Please select a file');
    return;
  }

  try {
    const file = fileInput.files[0];
    
    // Better approach: use FileReader for base64 conversion
    const base64String = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        // Remove the data:image/...;base64, prefix
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    const requestData = {
      cfid: parseInt(cfid),
      img_bytes: base64String
    };

    console.log('Uploading profile picture for CFID:', cfid);

    const response = await fetch('/api/files/upload_profile_picture', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData)
    });

    const data = await response.json();
    
    if (response.ok && data.success) {
      // Update ALL profile pictures on the page with cache busting
      const profileImages = document.querySelectorAll('.profile-image-small, .profile-image-large');
      const timestamp = new Date().getTime();
      
      profileImages.forEach(img => {
        if (img) {
          img.src = `/api/files/${cfid}/profile_icon?t=${timestamp}`;
        }
      });
      
      closeProfilePictureModal();
      alert('Profile picture updated successfully!');
    } else {
      alert('Failed to upload profile picture: ' + (data.error || 'Unknown error'));
    }
  } catch (error) {
    console.error('Error uploading profile picture:', error);
    alert('Error uploading profile picture: ' + error.message);
  }
});

// Close modal when clicking outside
document.getElementById('profile-picture-modal').addEventListener('click', function(e) {
  if (e.target === this) {
    closeProfilePictureModal();
  }
});