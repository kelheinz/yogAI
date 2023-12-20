import pandas as pd
import pytube
import imageio
import os
from moviepy.editor import VideoFileClip
from pydrive.auth import GoogleAuth
from pydrive.auth import ServiceAccountCredentials
from pydrive.drive import GoogleDrive


def download_video(url):
    yt = pytube.YouTube(url)
    yt.streams.filter(progressive=False, file_extension='mp4').order_by('resolution').desc().first().download(filename='video.mp4')
    clip = VideoFileClip('video.mp4')
    return clip


def make_directory(drive, name, parent_id):
    folder = drive.CreateFile({'title': name,
                               'mimeType':'application/vnd.google-apps.folder',
                               'parents': [{'id': parent_id}]})
    folder.Upload()
    return folder['id']


def upload_img(drive, name, parent_id):
    file = drive.CreateFile({'title': name, 'parents': [{'id': parent_id}]})
    file.SetContentFile(name)
    file.Upload()
    return file['id']

def authenticate_google(credentials_file):
    gauth = GoogleAuth()
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, ['https://www.googleapis.com/auth/drive'])
    drive = GoogleDrive(gauth)
    return drive

def get_frames(drive, url, df, clip, pose_dict):
    df1 = df[df['URL'] == url]
    url_dict = {}
    # Loop through df1 and get start and end time
    try:
        for i in range(len(df1)):
            start = df1.iloc[i]['Start_Second']
            extraction_rate = clip.fps/10
            start_frame = extraction_rate * start
            end = df1.iloc[i]['End_Second']
            end_frame = extraction_rate * end
            pose = int(df1.iloc[i]['Pose_Num'])
            creator = df1.iloc[i]['Username']
            dict_key = f'{pose}_{creator}'
            if dict_key in url_dict:
                creator_folder_id = url_dict[dict_key]
            else:
                pose_folder_id = pose_dict[pose]
                creator_folder_id = make_directory(drive, creator, pose_folder_id)
                url_dict[dict_key] = creator_folder_id
            print("Starting to get frames")
            for i in range(int(start_frame), int(end_frame)):
                frame = clip.get_frame(i/extraction_rate)
                imageio.imwrite(f'Pose_{pose}_{creator}_{i}.jpg', frame)
                upload_img(drive, f'Pose_{pose}_{creator}_{i}.jpg', creator_folder_id)
                with open('filenames.csv', 'a') as file:
                    file.write(f'Pose_{pose}_{creator}_{i}.jpg\n')
                os.remove(f'Pose_{pose}_{creator}_{i}.jpg')
        print("Finished getting frames")
        with open('completed_urls.csv', 'a') as file:
            file.write(f'{url}\n')
        with open('url_dict.csv', 'a') as file:
            for key, value in url_dict.items():
                file.write(f'{url}, {key}, {value}\n')
    except:
        with open('failed_urls.csv', 'a') as file:
            file.write(f'{url}\n')


def make_pose_folders(drive, parent_id):
    pose_dict = {}
    for i in range(1, 10):
        pose_folder_id = make_directory(drive, f'Pose_{i}', parent_id)
        # Store pose folder id in dictionary
        pose_dict[i] = pose_folder_id
        print(f'Made Pose {i} folder')
    return pose_dict


def main():
    credentials_file = 'service_account_credentials.json'
    drive = authenticate_google(credentials_file)
    print('Authenticated')

    # Import urls file
    df = pd.read_csv('data.csv')
    completed_urls = pd.read_csv('completed_urls.csv')
    df = df[~df['URL'].isin(completed_urls['URL'])]
    print('Imported CSV')

    # Get unique urls
    url_unique = list(df['URL'].unique())

    # Make Parent directory
    parent_id = make_directory(drive, 'Pose_Data', '1Cpxm2Oyitu9gpDfAySX-3ZwW3MPV1faV')
    print('Made Parent Directory')
    pose_dict = make_pose_folders(drive, parent_id)

    # Make csv file to store completed urls
    if not os.path.exists('completed_urls.csv'):
        with open('completed_urls.csv', 'w') as file:
            file.write('URL\n')

    with open('failed_urls.csv', 'w') as file:
        file.write('URL\n')

    if not os.path.exists('filenames.csv'):
        with open('filenames.csv', 'a') as file:
            file.write('Filename\n')

    if not os.path.exists('url_dict.csv'):
        with open('url_dict.csv', 'a') as file:
            file.write('URL, Pose_Creator, Folder_ID\n')

    # Go through URLs
    for (i, url) in enumerate(url_unique):
        if i % 10 == 0:
            drive = authenticate_google(credentials_file)
        print("Looping through URLs")
        try:
            clip = download_video(url)
            print(f'Downloaded {url}')
            get_frames(drive, url, df, clip, pose_dict)
            print(f'Finished {i} of {len(url_unique)}')
        except:
            with open('failed_urls.csv', 'a') as file:
                file.write(f'{url}\n')
            print(f'Failed {i} of {len(url_unique)}')


if __name__ == '__main__':
    main()
