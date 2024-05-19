import threading
from hikerapi import Client as InstagramClient
from pymongo import MongoClient, UpdateOne
import random
import asyncio
import uuid
import base64
import vertexai
import vertexai.preview.generative_models as generative_models
from vertexai.generative_models import GenerativeModel, Part, SafetySetting, HarmBlockThreshold, HarmCategory
import mimetypes
import urllib.request
import os
import re
import requests
import pyheif
from PIL import Image
import io


class AdmyreInstagramClient:
    client = InstagramClient("5uEjC54ppVtf1UBwz1RStKydDz8VVxYV")
    dbclient = MongoClient('mongodb://localhost:27017/')
    raw_db = dbclient['demo_raw_db']
    insights_db = dbclient['demo_insights_db']
    profiles = raw_db['profiles']
    strategy = raw_db['strategy']
    lists = raw_db['lists']
    media = raw_db['media']
    followers = raw_db['followers']
    followings = raw_db['followings']
    media_likers = raw_db['media_likers']
    media_comments = raw_db['media_comments']
    operations_statuses = {}

    @staticmethod
    def run_async(func, *args, **kwargs):
        operation_id = str(uuid.uuid4())
        AdmyreInstagramClient.operations_statuses[operation_id] = "Running"

        def task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(func(*args, **kwargs))
            AdmyreInstagramClient.operations_statuses[operation_id] = "Completed"
            return result

        thread = threading.Thread(target=task)
        thread.start()
        return operation_id

    @classmethod
    async def create_strategy_async(cls, strategy_name: str, strategy_desc: str):
        strategy_id = random.randint(1000, 9999)
        while cls.strategy.find_one({"strategy_id": strategy_id}):
            strategy_id = random.randint(1000, 9999)

        strategy_data = {
            "strategy_id": strategy_id,
            "name": strategy_name,
            "description": strategy_desc
        }
        cls.strategy.insert_one(strategy_data)
        return strategy_data

    @classmethod
    def create_strategy(cls, strategy_name, strategy_desc):
        print('operation ID:- ', cls.run_async(cls.create_strategy_async, strategy_name, strategy_desc))

    @classmethod
    def show_strategy(cls):
        # Retrieve all strategies from the database
        strategies = list(cls.strategy.find({}))

        # Format and print each strategy
        for strategy in strategies:
            print(f"Strategy ID: {strategy['strategy_id']}, Name: {strategy['name']}, Description: {strategy['description']}")

        if len(strategies) == 0:
            print("No strategies in database. Create One to get started.")



    @classmethod
    async def create_list_async(cls, strategy_id: int, list_name: str):
        '''
        This method takes in a strategy_id and a list name, creates a list related to the strategy, and returns a dictionary containing
        the strategy_id, list_id, cumulative_list_id, and list_name. Each list is uniquely identified by a concatenation of the strategy_id and
        a new 4-digit list_id.
        '''
        list_id = random.randint(1000, 9999)
        cumulative_list_id = f"{strategy_id}_{list_id}"

        while cls.lists.find_one({"cumulative_list_id": cumulative_list_id}):
            list_id = random.randint(1000, 9999)
            cumulative_list_id = f"{strategy_id}_{list_id}"

        list_data = {
            "strategy_id": strategy_id,
            "list_id": list_id,
            "cumulative_list_id": cumulative_list_id,
            "list_name": list_name
        }

        cls.lists.insert_one(list_data)
        return list_data

    @classmethod
    def create_list(cls, strategy_id, list_name):
        print('operation ID:- ', cls.run_async(cls.create_list_async, strategy_id, list_name))

    @classmethod
    def show_list(cls):
        # Retrieve all lists from the database
        lists = list(cls.lists.find({}))

        # Format and print each list
        for lst in lists:
            print(f"List ID: {lst['list_id']}, Name: {lst['list_name']}, Strategy ID: {lst['strategy_id']}, Cumulative ID: {lst['cumulative_list_id']}")

        if len(lists) == 0:
            print("No lists found in the database.")



    @classmethod
    async def load_profile_async(cls, c_list_id: str, username: str):
        '''
        Fetches user data by username, combines it with additional user data fetched by user ID, then stores the combined data in the profiles table in MongoDB.
        A unique Admyre internal profile_id is also generated and stored, and this ID is used to establish a relationship between the profile and the list.
        '''
        user_data = cls.client.user_by_username_v1(username=username)
        if not user_data or 'pk' not in user_data:
            raise ValueError("User data could not be fetched or lacks 'pk'")

        user_about_data = cls.client.user_about_v1(id=user_data['pk'])

        # Combine data, preferring 'user_about_data' in case of overlap
        combined_data = {**user_data, **user_about_data}

        # Generate a unique Admyre profile ID
        admyre_profile_id = f"public_{random.randint(1000, 9999)}"
        while cls.profiles.find_one({"admyre_public_profile_id": admyre_profile_id}):
            admyre_profile_id = f"public_{random.randint(1000, 9999)}"

        combined_data['admyre_public_profile_id'] = admyre_profile_id

        # Store combined data in MongoDB, updating if the user already exists
        cls.profiles.update_one(
            {'admyre_public_profile_id': admyre_profile_id},
            {'$set': combined_data},
            upsert=True
        )

        # Establish a relationship with the list by adding the Admyre profile ID to the list's profile IDs array
        cls.lists.update_one(
            {'cumulative_list_id': c_list_id},
            {'$addToSet': {'profile_ids': admyre_profile_id}},
            upsert=True
        )

        return {'status': 'success', 'data': combined_data}

    @classmethod
    def load_profile(cls, c_list_id, username):
        print('operation ID:- ', cls.run_async(cls.load_profile_async, c_list_id, username))

    @classmethod
    def show_profiles(cls):
        # Retrieve all profiles from the database
        profiles = list(cls.profiles.find({}))

        # Format and print each profile
        for profile in profiles:
            print(f"Profile ID: {profile.get('admyre_public_profile_id', 'N/A')}, Username: {profile.get('username', 'N/A')}, Name: {profile.get('name', 'N/A')}")

        if len(profiles) == 0:
            print("No profiles found in the database.")



    @classmethod
    async def load_media_async(cls, admyre_public_id: str, count: int = 12, is_pinned: bool = False, type: str = 'all'):
        '''
        this method loads the media associated with that profile... there are media chunks associated with each profile...
        argument admyre_public_id is compulsory but is_pinned and type and count are optional, (default values need to be count=12,
        is_pinned = false and type='all'). when admyre public id is given, use it and obtain the pk (the one which instagram provides)
        using that pk, u can do something like this to fetch all types of media posted by that user
        from hikerapi import Client
        cl = Client(<ACCESS_KEY>)
        medias, end_cursor = await cl.user_medias_chunk_v1(
            user_id="123123", end_cursor=None
        )

        the above method fetches 12 media objects at a time... therefore if user specifies anything less than 12 in the count, it will still
        fetch 12 media posts, but if they want 19 posts, then first fetch 12 posts using end_cursor=None, but after that, use the end cursor
        provided by this api above to paginate...

        similarly, if type='reels',
        then use this method:
        videos, end_cursor = await cl.user_videos_chunk_v1(
            user_id="123123", end_cursor=None
        )
        there are only two types available, either 'all' or 'reels'

        and if the user requests pinned media, then is_pinned can be set to true and this would be the function call for that:
        res = await cl.user_medias_pinned_v1(user_id="123123", amount=10)

        (here amount can be specified...)

        all these data has to be stored in media table... and it has to be stored along with the admyre_public_id as well so that there is a more
        apparent relation between the media and the profile...
        '''
        profile = cls.profiles.find_one({'admyre_public_profile_id': admyre_public_id})
        if not profile:
            raise ValueError("Profile not found")
        pk = profile['pk']

        # Initialize variables
        media_items = []
        end_cursor = None
        amount_to_fetch = max(12, count)  # Ensure at least 12 are fetched

        if is_pinned:
            # Fetch pinned media
            media_items = cls.client.user_medias_pinned_v1(user_id=pk, amount=count)
        elif type == 'all':
            # Fetch all types of media
            while len(media_items) < count:
                new_media, end_cursor = cls.client.user_medias_chunk_v1(user_id=pk, end_cursor=end_cursor)
                media_items.extend(new_media)
                if not end_cursor or len(new_media) < 12:
                    break
        elif type == 'reels':
            # Fetch only reels
            while len(media_items) < count:
                new_media, end_cursor = cls.client.user_videos_chunk_v1(user_id=pk, end_cursor=end_cursor)
                media_items.extend(new_media)
                if not end_cursor or len(new_media) < 12:
                    break

        # Store fetched media in the MongoDB media table
        for media in media_items:
            media['admyre_public_id'] = admyre_public_id
            cls.media.update_one({'id': media['id']}, {'$set': media}, upsert=True)

        return {'status': 'success', 'fetched_count': len(media_items)}

    @classmethod
    def load_media(cls, admyre_public_id, count=12, is_pinned=False, type='all'):
        print('operation ID:- ', cls.run_async(cls.load_media_async, admyre_public_id, count, is_pinned, type))

    @classmethod
    def show_media(cls, admyre_public_id):
        # Retrieve all media for a specific Admyre public ID
        media_records = list(cls.media.find({'admyre_public_id': admyre_public_id}))

        # Format and print each media record
        for media in media_records:
            print(f"Media ID: {media.get('id')}, Type: {media.get('type', 'N/A')}, Content: {media.get('content', 'N/A')}")

        if len(media_records) == 0:
            print("No media found for the given Admyre public ID.")



    @classmethod
    async def load_profile_followers_async(cls, admyre_public_id: str, count: int = 100):
        profile = cls.profiles.find_one({'admyre_public_profile_id': admyre_public_id})
        if not profile:
            raise ValueError("Profile not found with given Admyre public ID")
        pk = profile['pk']

        followers = []
        max_id = None
        while len(followers) < count:
            fetched_followers, next_max_id = cls.client.user_followers_chunk_v1(user_id=pk, max_id=max_id)
            valid_followers = [f for f in fetched_followers if 'pk' in f]  # Ensure each follower has a 'pk'
            followers.extend(valid_followers)
            if not next_max_id or len(valid_followers):
                break
            max_id = next_max_id

        operations = [UpdateOne({'id': f['pk']}, {'$set': f, '$addToSet': {'admyre_public_profile_ids': admyre_public_id}}, upsert=True) for f in followers]
        if operations:
            cls.followers.bulk_write(operations)
            return {'status': 'success', 'fetched_count': len(followers)}
        else:
            return {'status': 'failed', 'reason': 'No valid followers to process'}




    @classmethod
    def load_profile_followers(cls, admyre_public_id, count=100):
        print('operation ID:- ', cls.run_async(cls.load_profile_followers_async, admyre_public_id, count))

    @classmethod
    def show_followers(cls, admyre_public_id):
        # Retrieve all followers for a specific Admyre public ID
        followers_records = list(cls.followers.find({'admyre_public_profile_ids': admyre_public_id}))

        # Format and print each follower record
        for follower in followers_records:
            print(f"Follower ID: {follower.get('id')}, Name: {follower.get('name', 'N/A')}, Username: {follower.get('username', 'N/A')}")

        if len(followers_records) == 0:
            print("No followers found for the given Admyre public ID.")


    @classmethod
    async def load_profile_followings_async(cls, admyre_public_id: str, count: int = 100):
        profile = cls.profiles.find_one({'admyre_public_profile_id': admyre_public_id})
        if not profile:
            raise ValueError("Profile not found with the given Admyre Public ID")
        pk = profile['pk']

        followings = []
        max_id = None

        while len(followings) < count:
            fetched_followings, next_max_id = cls.client.user_following_chunk_v1(user_id=pk, max_id=max_id)
            followings.extend(fetched_followings)
            if not next_max_id or len(fetched_followings):
                break
            max_id = next_max_id

            if followings:
                operations = [UpdateOne({'id': follower['id']}, {'$set': follower, '$addToSet': {'admyre_public_profile_ids': admyre_public_id}}, upsert=True) for following in followings]
                cls.followings.bulk_write(operations)

        return  {'status': 'success', 'fetched_count': len(followings)}

    @classmethod
    def load_profile_followings(cls, admyre_public_id, count=100):
        print('operation ID:- ', cls.run_async(cls.load_profile_followings_async, admyre_public_id, count))

    @classmethod
    def show_followings(cls, admyre_public_id):
        # Retrieve all following entries for a specific Admyre public ID
        followings_records = list(cls.followings.find({'admyre_public_profile_ids': admyre_public_id}))

        # Format and print each following record
        for following in followings_records:
            print(f"Following ID: {following.get('id')}, Name: {following.get('name', 'N/A')}, Username: {following.get('username', 'N/A')}")

        if len(followings_records) == 0:
            print("No followings found for the given Admyre public ID.")



    @classmethod
    async def load_media_likers_async(cls, code: str, type: str = 'media_pk'):
        # Determine the media primary key based on the input type
        if type == 'media_code':
            media_pk = cls.client.media_pk_from_code_v1(code=code)
        elif type == 'media_url':
            media_pk = cls.client.media_pk_from_url_v1(url=code)
        else:
            media_pk = code  # Assume code is the PK if type is 'media_pk'

        # Fetch likers using the media primary key
        likers = cls.client.media_likers_v1(id=media_pk)

        # Store likers in MongoDB
        if likers:
            operations = [UpdateOne({'id': liker.get('pk')}, {'$set': liker, '$setOnInsert': {'media_code': code, 'media_pk': media_pk}}, upsert=True) for liker in likers if 'pk' in liker]
            if operations:
                cls.media_likers.bulk_write(operations)
                return {'status': 'success', 'fetched_count': len(likers)}
            else:
                return {'status': 'failed', 'reason': 'No valid likers to process'}

        return {'status': 'failed', 'reason': 'No likers found'}

    @classmethod
    def load_media_likers(cls, code, type='media_pk'):
        print(cls.run_async(cls.load_media_likers_async, code, type))

    @classmethod
    def show_media_likers(cls, identifier, identifier_type='media_pk'):
        # Ensure the identifier_type is one of the expected types
        valid_types = ['media_pk', 'media_code', 'media_url']
        if identifier_type not in valid_types:
            print(f"Invalid identifier type. Must be one of {valid_types}.")
            return

        # Build the query field dynamically based on the identifier_type
        query_field = identifier_type  # This will dynamically set to 'media_pk', 'media_code', or 'media_url'
        likers_records = list(cls.media_likers.find({query_field: identifier}))

        # Format and print each liker record
        for liker in likers_records:
            print(f"Liker ID: {liker.get('id')}, Username: {liker.get('username', 'N/A')}")

        if len(likers_records) == 0:
            print("No likers found for the given media identifier.")


    @classmethod
    async def load_media_comments_async(cls, code: str, type: str = 'media_pk', count: int = 20, fetch_replies: bool = False):
        # Determine the media primary key based on the input type
        if type == 'media_code':
            media_pk = cls.client.media_pk_from_code_v1(code=code)
        elif type == 'media_url':
            media_pk = cls.client.media_pk_from_url_v1(url=code)
        else:
            media_pk = code  # Assume code is the PK if type is 'media_pk'

        comments = []
        max_id = None

        # Fetch comments in chunks until the desired count is reached or no more comments are available
        while len(comments) < count:
            fetched_comments, new_max_id, _ = cls.client.media_comments_chunk_v1(
                id=media_pk, max_id=max_id, can_support_threading=fetch_replies
            )
            comments.extend(fetched_comments)
            print("comments fetched:- " + str(len(comments)) + "and count is: " +str(count))
            if not new_max_id or len(fetched_comments):
                break
            max_id = new_max_id

        # Store comments in the MongoDB media_comments table
        operations = [
            UpdateOne({'id': comment.get('pk')}, {'$set': comment, '$setOnInsert': {'media_code': code, 'media_pk': media_pk}}, upsert=True)
            for comment in comments if 'pk' in comment
        ]
        if operations:
            cls.media_comments.bulk_write(operations)
            return {'status': 'success', 'fetched_count': len(comments)}
        else:
            return {'status': 'failed', 'reason': 'No operations to execute'}



    @classmethod
    def load_media_comments(cls, code, type='media_pk', count=20, fetch_replies=False):
        print(cls.run_async(cls.load_media_comments_async, code, type, count, fetch_replies))

    @classmethod
    def show_media_comments(cls, identifier, identifier_type='media_pk'):
        query_field = f"{identifier_type}"  # This will map to 'media_pk', 'media_code', or 'media_url'
        comments_records = list(cls.media_comments.find({query_field: identifier}))

        # Format and print each comment record
        for comment in comments_records:
            print(f"Comment ID: {comment.get('id')}, Text: {comment.get('text', 'N/A')}")

        if len(comments_records) == 0:
            print("No comments found for the given media.")



    @classmethod
    def check_status(cls, operation_id):
        return cls.operations_statuses.get(operation_id, "No such operation ID")

    @staticmethod
    def init_gemini():
        vertexai.init(project="iconic-parsec-418113", location="us-central1")

    @staticmethod
    def encode_input(file_path):
        """Encode file content to base64."""
        with open(file_path, 'rb') as file:
            return base64.b64encode(file.read()).decode('utf-8')

    # @staticmethod
    # def get_mime_type(file_path):
    #     """Determine MIME type based on file extension."""
    #     if file_path.endswith('.mp4'):
    #         return 'video/mp4'
    #     elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
    #         return 'image/jpeg'
    #     elif file_path.endswith('.png'):
    #         return 'image/png'
    #     else:
    #         raise ValueError("Unsupported file type")

    @staticmethod
    def get_mime_type(file_url):
        """Returns the MIME type based on the file extension."""
        # Extract file extension from the URL using regular expression
        file_extension = re.search(r'\.([a-zA-Z0-9]+)\?', file_url)
        if file_extension:
            file_extension = '.' + file_extension.group(1)
        else:
            raise ValueError("File extension could not be determined from URL")

        # Manually handle common file extensions
        if file_extension.lower() == '.mp4':
            return 'video/mp4'
        elif file_extension.lower() == '.jpeg' or file_extension.lower() == '.jpg':
            return 'image/jpeg'
        elif file_extension.lower() == '.png':
            return 'image/png'
        else:
            # Use mimetypes to guess MIME type
            type, _ = mimetypes.guess_type(file_url)
            if not type:
                raise ValueError("Unsupported file type or MIME type could not be determined")
            return type

    @staticmethod
    def load_media_from_url(url):
        """Load media from a URL and return a Part object with the appropriate MIME type."""
        mime_type = AdmyreInstagramClient.get_mime_type(url)
        with urllib.request.urlopen(url) as response:
            media_data = response.read()
        return Part.from_data(mime_type=mime_type, data=media_data)

    @staticmethod
    def fetch_and_convert_image(url):
        """Fetch image from URL and convert if necessary."""
        # Get MIME type based on URL extension
        mime_type = AdmyreInstagramClient.get_mime_type(url)

        # Fetch the media
        response = requests.get(url)
        response.raise_for_status()
        media_data = response.content

        # If the media is HEIC, convert to JPEG
        if mime_type == 'image/heic':
            heif_file = pyheif.read_heif(media_data)
            image = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                "raw",
                heif_file.mode,
                heif_file.stride
            )
            jpeg_buffer = io.BytesIO()
            image.save(jpeg_buffer, format="JPEG")
            jpeg_buffer.seek(0)
            media_data = jpeg_buffer.getvalue()
            mime_type = 'image/jpeg'

        return media_data, mime_type

    @classmethod
    def generate_insights(cls, media_urls, prompt):
        """Generates insights from given media URLs and a prompt."""
        cls.init_gemini()
        results = []

        for url in media_urls:
            try:
                media_data, mime_type = cls.fetch_and_convert_image(url)
                media_part = Part.from_data(mime_type=mime_type, data=media_data)
                contents = [media_part, prompt]
                model = GenerativeModel("gemini-1.5-pro-preview-0409")
                generation_config = {
                    "max_output_tokens": 8192,
                    "temperature": 1,
                    "top_p": 0.95
                }
                safety_settings = [
                    SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH),
                    SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH),
                    SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH),
                    SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH)
                ]
                responses = model.generate_content(contents, generation_config=generation_config, safety_settings=safety_settings, stream=True)
                for response in responses:
                    results.append(response.text)
            except Exception as e:
                print(f"Error processing media from {url}: {e}")
        return results

    @classmethod
    def generate_media_insights(cls, file_url):
        """Generate insights for a video using the Gemini model, utilizing the generate_insights method."""
        prompt = """
Analyze the provided video content carefully. Based on the spoken content, audio cues, and visual elements observed, classify the video into the following specified categories. You should assign a percentage score for each category reflecting how well the video fits into it, with a limit of categorizing into a maximum of six categories. The categories should be ranked according to their relevance, and if necessary, scores can be distributed across multiple overlapping categories.

Additionally, evaluate the tonality of the video by identifying the most prominent tones from the list provided. Rate each identified tone on a scale from 0 to 100%, reflecting how strongly each tone is presented in the video.

Also assess the production quality of the video. Rate the production on a scale from 0 to 100, where higher scores indicate higher production quality considering factors such as editing, sound, resolution, and visual aesthetics.

Determine the approximate geographical location where the video was either shot or is primarily focused on. Specify this in terms of city and country. If the location cannot be determined, return 'null' for both city and country.

Return the analysis results in the form of a Python dictionary with the categories and their corresponding percentage scores, alongside the identified location, tonal analysis, and production quality score.

Categories to consider:
- Autos & Vehicles
- Animation
- Astrology
- Agriculture & Allied Sectors
- Adult
- Arts & Craft
- Beauty
- Blogs and Travel
- Book
- Comedy
- DIY
- Devotional
- Defence
- Entertainment
- Education
- Events
- Electronics
- Food & Drinks
- Finance
- Fashion & Style
- Family & Parenting
- Films
- Gaming
- Government
- Health & Fitness
- Infotainment
- IT & ITES
- Kids & Animation
- Legal
- Music
- Miscellaneous
- meme
- Motivational
- Movies & Shows
- News & Politics
- Non-profits
- Photography & Editing
- Pets & Animals
- People & Culture
- Religious Content
- Real Estate
- Reviews
- Science & Technology
- Sports
- Supernatural
- Travel & Leisure
- Vlogging

Tonalities to consider:
- Sarcasm
- Inclusivity
- Humor
- Offensiveness
- Caring
- Originality
- Surprise
- Anger
- Sadness
- Frustration
- Inspirational
- Educational
- Excitement
- Calmness
- Nostalgic
- Romantic
- Professional
- Casual
- Urgency
- Relaxation

Required output format:
{
  'results': {
    'Category1': 'XX%',
    'Category2': 'XX%',
    ...,
    'Category6': 'XX%'
  },
  'tonality': {
    'Tone1': 'XX%',
    'Tone2': 'XX%',
    ...
  },
  'production_quality': XX,
  'location': {
    'city': 'City Name or null',
    'country': 'Country Name or null'
  }
}
"""
        # Use the existing generate_insights method to process the video
        results = cls.generate_insights([file_url], prompt)
        for result in results:
            print(result)
        return results


'''
there are few things that are needed as insights:
influencer level:
content categories
basic metrics


audience level:
audience interests (based on commenters)
fake followers
location (city and country)
age distribution
'''

# from sdkdemo.client import AdmyreInstagramClient
# media_url = ["https://scontent-lax3-1.cdninstagram.com/o1/v/t16/f1/m82/F84666FB894AF8B334FD93AA9DEAF383_video_dashinit.mp4?efg=eyJ2ZW5jb2RlX3RhZyI6InZ0c192b2RfdXJsZ2VuLmNsaXBzLmMyLjcyMC5iYXNlbGluZSJ9&_nc_ht=scontent-lax3-1.cdninstagram.com&_nc_cat=102&vs=1279514356288215_1566453304&_nc_vs=HBksFQIYT2lnX3hwdl9yZWVsc19wZXJtYW5lbnRfcHJvZC9GODQ2NjZGQjg5NEFGOEIzMzRGRDkzQUE5REVBRjM4M192aWRlb19kYXNoaW5pdC5tcDQVAALIAQAVAhg6cGFzc3Rocm91Z2hfZXZlcnN0b3JlL0dJM01DaGE2Ry0tNEV1MENBT1B6cDNWc3RBWUVicV9FQUFBRhUCAsgBACgAGAAbABUAACb0trrS8pfvPxUCKAJDMywXQE03bItDlYEYEmRhc2hfYmFzZWxpbmVfMV92MREAdf4HAA%3D%3D&_nc_rid=4f67877b34&ccb=9-4&oh=00_AfCaBtENzvRO-7VBGMywhkrxeKV_LkPQXbwB6ZgpYIjUXg&oe=6634FE73&_nc_sid=b41fef"]
# prompt = "what is this video about? can u describe the tonality of this video?"
# AdmyreInstagramClient.generate_insights(media_url, prompt)

url = "https://scontent-lax3-1.cdninstagram.com/o1/v/t16/f1/m82/F84666FB894AF8B334FD93AA9DEAF383_video_dashinit.mp4?efg=eyJ2ZW5jb2RlX3RhZyI6InZ0c192b2RfdXJsZ2VuLmNsaXBzLmMyLjcyMC5iYXNlbGluZSJ9&_nc_ht=scontent-lax3-1.cdninstagram.com&_nc_cat=102&vs=1279514356288215_1566453304&_nc_vs=HBksFQIYT2lnX3hwdl9yZWVsc19wZXJtYW5lbnRfcHJvZC9GODQ2NjZGQjg5NEFGOEIzMzRGRDkzQUE5REVBRjM4M192aWRlb19kYXNoaW5pdC5tcDQVAALIAQAVAhg6cGFzc3Rocm91Z2hfZXZlcnN0b3JlL0dJM01DaGE2Ry0tNEV1MENBT1B6cDNWc3RBWUVicV9FQUFBRhUCAsgBACgAGAAbABUAACb0trrS8pfvPxUCKAJDMywXQE03bItDlYEYEmRhc2hfYmFzZWxpbmVfMV92MREAdf4HAA%3D%3D&_nc_rid=4f67877b34&ccb=9-4&oh=00_AfCaBtENzvRO-7VBGMywhkrxeKV_LkPQXbwB6ZgpYIjUXg&oe=6634FE73&_nc_sid=b41fef"
