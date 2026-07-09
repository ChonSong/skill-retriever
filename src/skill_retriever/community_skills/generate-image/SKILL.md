---
name: generate-image
description: generate image with nano banana pro and FAL
license: MIT
compatibility: opencode
metadata:
  audience: image gen
---

generate 1K unless explicitly told otherwise

don't  make a bash script, just execute the curl call as follows

our FAL_KEY should be in .env , if it's not there, ask the user for it

always remember to safely utilize environment variables to prevent exposure 

source .env && curl --request POST \
  --url https://fal.run/fal-ai/nano-banana-pro \
  --header "Authorization: Key $FAL_KEY" \
  --header "Content-Type: application/json" \
  --data '{
     "prompt": "<prompt>"
   }'


IF YOU NEED to edit an image (using reference images along with prompt)

source .env && curl --request POST \
  --url https://fal.run/fal-ai/nano-banana-pro/edit \
  --header "Authorization: Key $FAL_KEY" \
  --header "Content-Type: application/json" \
  --data '{
     "prompt": "make a photo of the man driving the car down the california coastline",
     "image_urls": [
       "https://storage.googleapis.com/falserverless/example_inputs/nano-banana-edit-input.png",
       "https://storage.googleapis.com/falserverless/example_inputs/nano-banana-edit-input-2.png"
     ]
   }'

IF YOU NEED TO UPLOAD AN IMAGE TO GET A PROPER URL FAL.AI can see, it's probably best to run some ad hoc python


```python
import os
import fal_client

# Ensure FAL_KEY is set in your environment
os.environ["FAL_KEY"] = "your_key_here"

# Uploads automatically and returns the CDN URL
url = fal_client.upload_file("path/to/image.jpg")
print(url)
```


Other properties

prompt string
The text prompt to generate an image from.

num_images integer
The number of images to generate. Default value: 1

seed integer
The seed for the random number generator.

aspect_ratio AspectRatioEnum
The aspect ratio of the generated image. Default value: "1:1"

Possible enum values: 21:9, 16:9, 3:2, 4:3, 5:4, 1:1, 4:5, 3:4, 2:3, 9:16

output_format OutputFormatEnum
The format of the generated image. Default value: "png"

Possible enum values: jpeg, png, webp

sync_mode boolean
If True, the media will be returned as a data URI and the output data won't be available in the request history.

resolution ResolutionEnum
The resolution of the image to generate. Default value: "1K"

Possible enum values: 1K, 2K, 4K

limit_generations boolean
Experimental parameter to limit the number of generations from each round of prompting to 1. Set to True to to disregard any instructions in the prompt regarding the number of images to generate.

enable_web_search boolean
Enable web search for the image generation task. This will allow the model to use the latest information from the web to generate the image.


{
  "prompt": "An action shot of a black lab swimming in an inground suburban swimming pool. The camera is placed meticulously on the water line, dividing the image in half, revealing both the dogs head above water holding a tennis ball in it's mouth, and it's paws paddling underwater.",
  "num_images": 1,
  "aspect_ratio": "1:1",
  "output_format": "png",
  "resolution": "1K"
}