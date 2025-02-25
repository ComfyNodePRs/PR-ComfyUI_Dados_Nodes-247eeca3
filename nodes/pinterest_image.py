import random
import torch
import numpy as np
import requests
import json
from py3pin.Pinterest import Pinterest
from PIL import Image
from io import BytesIO
from server import PromptServer
from aiohttp import web
import time
import contextlib
import io

from ComfyUI_Dados_Nodes import dirs

def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

class PinterestImageNode:
    board_name = {}

    @classmethod
    def update_board_name(cls, board_name, node_id):
        cls.board_name[node_id] = board_name

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "username": ("STRING", {"default": "", "multiline": False}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("IMAGE","STRING")

    FUNCTION = "get_random_pinterest_image"
    CATEGORY = "pinterest"


    def get_random_pinterest_image(self, username, unique_id):
        print(f"unique_id: {unique_id}")

        cred_root = dirs.BASE_DIR + "/.cred_root"
        print("cred_root folder: ", cred_root)

        print(f"All board names: {PinterestImageNode.board_name}")
    
        board_name = PinterestImageNode.board_name[int(unique_id)]

        """ start_time = time.time() * 1000  # Convert to milliseconds
        for _ in range(100):
            if PinterestImageNode.board_name is not None:
                board_name = PinterestImageNode.board_name
                PinterestImageNode.board_name = None
                break
            time.sleep(0.01)  # Short sleep to prevent excessive CPU usage

        end_time = time.time() * 1000  # Convert to milliseconds
        elapsed_time = round(end_time - start_time)

        print(f"Board name retrieval took {elapsed_time} milliseconds") """

        print(f"Getting random Pinterest image from board '{board_name}' for user '{username}'")

        if not username:
            raise ValueError(f"No username provided")

        self.pinterest = Pinterest(username=username, cred_root=cred_root)

        pins = []
        boards = self.pinterest.boards(username=username)
        if board_name == "all":
            for board in boards:
                pins.extend([pin for pin in self.pinterest.board_feed(board_id=board['id']) if 'images' in pin and '474x' in pin['images']])
        else:
            target_board = next((board for board in boards if board['name'].lower() == board_name.lower()), None)
            if not target_board:
                raise ValueError(f"Board '{board_name}' not found for user '{username}'")
            pins = [pin for pin in self.pinterest.board_feed(board_id=target_board['id']) if 'images' in pin and '474x' in pin['images']]

        if not pins:
            raise ValueError(f"No pins found for the selected board(s) board_name: {board_name}")

        random_pin = random.choice(pins)
        image_url = random_pin['images']['474x']['url']

        if image_url:
            response = requests.get(image_url)
            img = Image.open(BytesIO(response.content))
            img_tensor = pil2tensor(img)

            metadata = json.dumps(random_pin, indent=2)

            """ return (img_tensor, board_name, metadata) """
            return (img_tensor,metadata)
        else:
            raise ValueError("No suitable image URL found in the pin data")

    @classmethod
    def IS_CHANGED(cls, username):
        return random.randint(1, 1000000)



@PromptServer.instance.routes.post('/dadoNodes/pinterestNode')
async def api_pinterest_router(request):
    try:
        data = await request.json()
        operation = data.get('op')
        username = data.get('username')
        
        if operation == 'get_pinterest_board_names':
            print("Getting Boards from Pinterest username:", username)
            pinterestApi = Pinterest(username=username)
            boards = pinterestApi.boards(username=username)
            board_names = ["all"] + [board['name'] for board in boards]
            return web.json_response({"board_names": board_names})
        elif operation == 'update_selected_board_name':
            board_name = data.get('board_name')
            node_id = data.get('node_id')
            print(f"Updating board for {username}: {board_name} (Node ID: {node_id})")
            PinterestImageNode.update_board_name(board_name, node_id)
            return web.json_response({"status": "success", "board_name": board_name})
        else:
            return web.json_response({"error": "Unknown operation"}, status=400)
    except Exception as e:
        print("Error processing request:", e)
        return web.json_response({"error": str(e)}, status=500)

""" 
! TODO

* - preview image right on the node UI - last widget
-- issue is that widgets are being added also by the javascript file
-- which means if adding preview image widget here on the python file, the javascript widgets will be added after the preview image widget
-- unless there is a way to add widgets in the javascript file before the preview image widget

* - targeting a specific board not working
-- issue is that FUNCTION and RETURN_TYPES need to be in the python file as it currently stands
-- if finding a way making these work in the javascript file would basically resolve this issue
-- javascript file needs the image either way in order to display the image in the node UI

* - de-bloat code, clean up, centralize functionalities

"""