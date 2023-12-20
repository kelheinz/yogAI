from flask import Flask, render_template
from flask_sock import Sock
import os
import json
import pickle
import numpy as np
from xgboost import XGBClassifier
from sklearn.ensemble import ExtraTreesClassifier
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

app = Flask(__name__, static_folder='./static', static_url_path='/')
sock = Sock(app)
models = {}
model_files = {
    'pose1': 'pose_1_model.pkl',
    'pose2': 'pose_2_model.pkl',
    'pose3': 'pose_3_model.pkl',
    'pose4': 'pose_4_model.pkl',
    'pose5': 'pose_5_model.pkl',
    'pose6': 'pose_6_model.pkl',
    'pose7': 'ExtraTreesClassifier_model_7.pkl',
    'pose8': 'pose_8_model.pkl'   
}
std_models = ['pose2', 'pose4', 'pose5', 'pose6', 'pose8']
top_edge = [103, 67, 109, 10, 338, 297, 332]
bottom_edge = [58, 172, 136, 150, 149, 176, 148, 152,
               377, 400, 378, 379, 365, 397, 288]
top_l_lid = [247, 30, 29, 27, 28, 56, 190]
top_r_lid = [414, 286, 258, 257, 259, 260, 467]
l_brow = [107, 66, 105, 63, 70, 55, 65, 52, 53, 46]
r_brow = [336, 296, 334, 293, 300, 285, 295, 282, 283, 276]

@app.route('/')
def home():
    return render_template('index.html')


@sock.route('/process')
def process(sock):
    while True:
        # Receive data from client
        data = sock.receive()
        data = json.loads(data)

        # If no face detected, send -1
        if len(data['faceLandmarks']) == 0:
            sock.send(-1)
            continue

        # Parse Data
        poseId = data['poseId']
        category_data = data['faceBlendshapes'][0]['categories']
        score_values = [d['score'] for d in category_data]
        landmark_data = data['faceLandmarks'][0]

        if poseId in std_models:
            standardized_scores = std_scaler.transform(np.array([score_values]))
            results = models[poseId].predict(standardized_scores)
            print(poseId, results)

        elif poseId == 'pose3':
            landmark_data = data['faceLandmarks'][0]
            top_edge_values = [landmark_data[i]['z'] for i in top_edge]
            bottom_edge_values = [landmark_data[i]['z'] for i in bottom_edge]
            z_diff = np.mean(top_edge_values) - np.mean(bottom_edge_values)
            standardized_scores = p3_scaler.transform(np.array(
                [score_values + [z_diff]]
                ))
            results = models[poseId].predict(standardized_scores)
            print(poseId, results)

        elif poseId == 'pose1':
            landmark_data = data['faceLandmarks'][0]

            # top edge mean
            top_edge_values = [landmark_data[i]['y'] for i in top_edge]
            top_mean = np.mean(top_edge_values)

            # lid mean
            l_lid_values = [landmark_data[i]['y'] for i in top_l_lid]
            r_lid_values = [landmark_data[i]['y'] for i in top_r_lid]
            lid_mean = (np.mean(l_lid_values) + np.mean(r_lid_values)) / 2

            # brow mean
            l_brow_values = [landmark_data[i]['y'] for i in l_brow]
            r_brow_values = [landmark_data[i]['y'] for i in r_brow]
            brow_mean = (np.mean(l_brow_values) + np.mean(r_brow_values)) / 2

            # Get features
            brow_height_dev = (np.std(l_lid_values) + np.std(r_lid_values)) / 2
            brow_ratio = (lid_mean - brow_mean) / (brow_mean - top_mean)
            forehead_ratio = (brow_mean - top_mean)/(lid_mean - top_mean)

            # Predict
            standardized_scores = p1_scaler.transform(np.array(
                [score_values + [brow_ratio, brow_height_dev, forehead_ratio]]
                ))
            results = models[poseId].predict(standardized_scores)
            print(poseId, results)

        else:
            results = models[poseId].predict(np.array([score_values]))
            print(poseId, results)

        sock.send(results[0])


if __name__ == "__main__":
    std_scaler = pickle.load(open('models/scaler.pkl', 'rb'))
    p3_scaler = pickle.load(open('models/p3_scaler.pkl', 'rb'))
    p1_scaler = pickle.load(open('models/p1_scaler.pkl', 'rb'))
    for poseId in model_files.keys():
        filename = 'models/'+model_files[poseId]
        print("Loading model from file: ", filename)
        with open(filename, 'rb') as f:
            models[poseId] = pickle.load(f)
    port = int(os.environ.get('PORT', 3000))
    app.run(debug=True, host='0.0.0.0', port=port)
