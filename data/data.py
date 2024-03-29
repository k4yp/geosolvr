import requests
import json
import random
import wget
import os
import pandas as pd
from PIL import Image

results = pd.read_csv('results.csv')

try:
    df_results = pd.DataFrame(results.iloc[-1:,:].values, index = None)
    index = int(list(df_results[0])[0].split('.')[0])

except:
    index = 0

global_image_num = 0


class Colors:
    BOLD = '\033[1m'
    FAIL = '\033[91m'
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    END = '\033[0m'

class Generate:
    def __init__(self, num_images, output_file, api_key, threads):
        self.num_images = num_images
        self.output_file = output_file
        self.api_key = api_key
        self.threads = threads

        # gets last index of a csv file
        
        global global_image_num

        global index

        epoch = 0

        while epoch < num_images:
            coordinates = self.random_coordinates()
            metadata = self.check_streetview(coordinates[0], coordinates[1])

            if metadata != False:
                lat = metadata['location']['lat']
                lng = metadata['location']['lng']
                pano_id = metadata['pano_id']

                iso_code = self.reverse_geocode(lat, lng)

                print(f'{Colors.SUCCESS} progress [{round(((global_image_num) / (num_images * threads)) * 100, 1)}%]{Colors.END} streetview found in {iso_code}\n{lat},{lng}')
                
                global_image_num += 1

                index += 1

                with open(output_file, 'a') as f:
                    f.write(f'{str(index).zfill(6)}.png,{iso_code},{lat},{lng},{pano_id},{random.randint(0, 359)}\n')
                
                epoch += 1

    # returns random coordinats -> List[float, float]  
    def random_coordinates(self):
        lat = random.uniform(90, -90)
        lng = random.uniform(180, -180)

        return [lat, lng]

    # checks if streetview exists -> Dict or False
    def check_streetview(self, lat, lng):
        metadata = requests.get(f'https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lng}&radius=2048&key={self.api_key}').text
        metadata = json.loads(metadata)

        if metadata['status'] == 'OK' and metadata['copyright'] == '© Google':
            return metadata

        return False
    
    # converts latitude and longitude to iso code -> String
    def reverse_geocode(self, lat, lng):
        iso_code = requests.get(f'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18&addressdetails=1')
        iso_code = iso_code.json()
        
        return iso_code['address']['country_code']

class Download:
    def __init__(self, download_pano, results_file, img_directory, api_key, threads, thread_number):
        self.results_file = results_file
        self.img_directory = img_directory
        self.api_key = api_key
        self.threads = threads
        self.thread_number = thread_number
        self.download_pano = download_pano
 
        # gets last index from the image directory
 
        try:
            file_names = os.listdir(img_directory)
            img_index = int(os.path.splitext(file_names[-1])[0])
        except:
            img_index = 0
 
        df = pd.read_csv(results_file)
 
        rows = df.values.tolist()
        rows.insert(0,0)
 
        for i in range(img_index + 1, len(rows) + 1, threads):
            thread_index = i + thread_number
            try:
                lat = rows[thread_index][2]
                lng = rows[thread_index][3]
                pano_id = rows[thread_index][4]
                heading = rows[thread_index][5]
 
                if download_pano:
                    self.pano(pano_id, thread_index)

                else:
                    self.static(lat, lng, heading, thread_index)
 
            except Exception as e:
                print('thread index out of range: ', e)
 
    def static(self, lat, lng, heading, thread_index):
        wget.download(f'https://maps.googleapis.com/maps/api/streetview?size=640x640&location={lat},{lng}&fov=180&heading={heading}&pitch=0&key={self.api_key}', out=f'{self.img_directory}/{str(thread_index).zfill(6)}.png')
 
    def pano(self, pano_id, thread_index):
        for x in range(7):
            for y in range(3):
                wget.download(f'https://streetviewpixels-pa.googleapis.com/v1/tile?cb_client=apiv3&panoid={pano_id}&x={x}&y={y}&zoom=3', out=f'{self.img_directory}/{str(thread_index).zfill(6)}_{x}_{y}.png')
        
        output_image = Image.new('RGB', (3584, 1536))

        for x in range(7):
            for y in range(3):
                file_name = f'{self.img_directory}/{str(thread_index).zfill(6)}_{x}_{y}.png'
                output_image.paste(Image.open(file_name), (x * 512, y * 512))

                os.remove(file_name)
        
        output_image.save(f'{self.img_directory}/{str(thread_index).zfill(6)}.png')

class Validate:
    def __init__(self, input_file, iso_codes_file):
        self.input_file = input_file
        self.iso_codes_file = iso_codes_file

        iso_codes = self.get_iso_codes(iso_codes_file)

        invalid_indexes = self.get_invalid_indexes(input_file, iso_codes)

    # returns iso codes from provided iso codes file -> List[string, string, string ...]
    def get_iso_codes(self, iso_codes_file):
        iso_codes_list = []
        iso_codes_df = pd.read_csv(iso_codes_file)

        for i in range(len(iso_codes_df.index)):
            iso_codes_list.append(iso_codes_df.iloc[i]['iso_code'])

        return iso_codes_list

    # returns indexes of invalid iso codes -> List[int, int, int ...]    
    def get_invalid_indexes(self, input_file, iso_codes):

        input_df = pd.read_csv(input_file)

        invalid_indexes = []

        for i in range(len(input_df.index)):     
            index_iso_code = input_df.iloc[i]['iso_code']

            if index_iso_code not in iso_codes:
                invalid_indexes.append(i)

        return invalid_indexes
        