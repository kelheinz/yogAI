import vision from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0";
const { FaceLandmarker, FilesetResolver, DrawingUtils } = vision;

const socket_url = 'ws://' + location.host + '/process';
const socket = new WebSocket(socket_url);
// const canvas = document.createElement('canvas');

let webcam_running = false;
let model_loaded = false;
let socket_open = false;

let video = null;
let mediaDevices = null;

let lastVideoTime = -1;
let results = undefined;
let lastPositiveTime = -1;
let poseTimeout = 50;

let faceLandmarker = null;
let poseId = 'pose1';

let currentlyPosing = false;
let currentlyCountingDown = false;
let remainingTime = null;

function playCorrectSound() {
    var audio = new Audio('audio/correct-156911.mp3');
    audio.play();
}
export const setPoseId = (pose) => {
    if (pose != poseId) {
        poseId = pose;
        remainingTime = null;
        currentlyCountingDown = false;
        document.getElementById("timer").innerHTML = "Get Ready!";
        document.getElementById("video").style.borderColor = "lightgray";
        document.getElementById("resultsDisplay").innerHTML = "Let's get started!";
    }
}

async function loadFaceLandmarker() {
    const filesetResolver = await FilesetResolver.forVisionTasks(
        // path/to/wasm/root
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
    );
    faceLandmarker = await FaceLandmarker.createFromOptions(
        filesetResolver,
        {
            baseOptions: {
                modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            },
            runningMode: "VIDEO",
            outputFaceBlendshapes: true
        }
    );
    model_loaded = true;
}


const getFrame = () => {
    if (!model_loaded || !webcam_running) {
        return;
    }
    let nowInMs = Date.now();
    if (lastVideoTime !== video.currentTime) {
        lastVideoTime = video.currentTime;
        results = faceLandmarker.detectForVideo(video, nowInMs);
    }
    return results;
}

const processResults = (results) => {
    if (!webcam_running || results === undefined || currentlyCountingDown == false) {
        return;
    }
    if (results == -1){
        document.getElementById("resultsDisplay").innerHTML = "No face detected!"; 
        document.getElementById("video").style.borderColor = "black"; 
        currentlyPosing = false;
    }
    if (results == 0){
        if (lastPositiveTime == -1 || (Date.now() - lastPositiveTime > poseTimeout)){
            document.getElementById("resultsDisplay").innerHTML = "Adjust your pose, try again!"; 
            document.getElementById("video").style.borderColor = "crimson"; 
            currentlyPosing = false;
            

        }
    }
    if (results == 1){
        lastPositiveTime = Date.now();
        document.getElementById("resultsDisplay").innerHTML = "Great job!";
        document.getElementById("video").style.borderColor = "greenyellow"; 
        currentlyPosing = true;
        
    }
}

const receivePacket = (event) => {
    // console.log('Message from server ', event.data);
    processResults(event.data);
};

socket.onopen = () => {
    console.log(`Connected to ${socket_url}`);
    socket.addEventListener('message', receivePacket);
    socket_open = true;
}

const videoPlayHandler = () => {
    video.play();
    console.log("Vid on");
    model_loaded = false;
    loadFaceLandmarker();
    webcam_running = true;
    console.log("Model loaded");
}

const activateWebcam = () => {
    mediaDevices
    .getUserMedia({
        video: { facingMode: "user" },
        audio: false,
    })
    .then((stream) => {
        // Changing the source of video to current stream.
        video.srcObject = stream;
        video = document.getElementById("video");
        video.addEventListener("loadedmetadata", videoPlayHandler);
    })
    .catch(alert);
    console.log("Webcam on");
}; 

const deactivateWebcam = () => {
    document.getElementById("resultsDisplay").innerHTML = "Let's get started!";
    document.getElementById("video").style.borderColor = "lightgray"; 
    video.pause();
    const stream = video.srcObject;
    if (stream) {
        const tracks = stream.getTracks();
        tracks.forEach(track => track.stop());
        video.srcObject = null;
    }
    video.removeEventListener("loadedmetadata", videoPlayHandler);
    console.log("Webcam off");
  };

document.addEventListener("DOMContentLoaded", () => {
    video = document.getElementById("video");
    video.muted = true;

    mediaDevices = navigator.mediaDevices;

    document.getElementById("buttonStart").addEventListener("click", () => {
        // Accessing the user camera and video.
        activateWebcam();
        document.getElementById("timer").innerHTML = "Get Ready!";
        remainingTime=5000;
        currentlyCountingDown=true;
    });

    document.getElementById("buttonStop").addEventListener("click", () => {
        // Deactivating the user camera and video.
        webcam_running = false;
        deactivateWebcam();
        document.getElementById("timer").innerHTML = "Timer Stopped";
        remainingTime=null;
        currentlyCountingDown=false;
    });

    const FPS = 30;
    setInterval(() => {
        if (socket_open && model_loaded && webcam_running && currentlyCountingDown) {
            var results = getFrame();
            // console.log('poseId: ', poseId)
            results['poseId'] = poseId;
            if (results !== undefined) {
                socket.send(JSON.stringify(results));
            }
            if (currentlyPosing) {
                if (remainingTime > 0) {
                    remainingTime -= 1000 / FPS;
                    document.getElementById("timer").innerHTML = `Time left: ${Math.round(remainingTime / 1000)}s`;
                } else {
                    document.getElementById("timer").innerHTML = "Timer Complete!";
                    remainingTime = null;
                    currentlyCountingDown = false;
                    document.getElementById("resultsDisplay").innerHTML = "Well done!";
                    playCorrectSound();
                    document.getElementById("video").style.borderColor = "turquoise";
                }
            }
        }
    }, 1000 / FPS);
});