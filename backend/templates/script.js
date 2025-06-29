const video = document.getElementById("video");
const canvas = document.getElementById("canvas");

// Start webcam
navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    video.srcObject = stream;
  })
  .catch(err => {
    alert("Webcam not accessible: " + err.message);
  });

function captureImage() {
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
}

function analyzeSymptom() {
  const symptom = document.getElementById("symptom").value;
  const imageBase64 = canvas.toDataURL("image/jpeg");

  fetch("/analyze-symptom", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      symptom,
      image: imageBase64
    })
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("symptomResult").textContent = data.result || data.error;
  });
}
