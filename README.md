# telegram_AI_Processor

## Project Overview
This project contains two main Python scripts: `tg_data_downloader.py` and `reply_only_llama3.2.py`, which jointly complete the task of downloading data from Telegram and processing conversations.

## Project Structure
### tg_data_downloader.py
This script is mainly responsible for downloading data from Telegram. The specific functions are as follows:
1. **Initialize the Telegram client**: Use the `Telethon` library to initialize a Telegram client. You need to provide `API_ID` and `API_HASH`.
2. **Get unread messages**: Obtain all conversations in Telegram, filter out unread messages, including group chats and private messages.
3. **Filter relevant messages**: Check whether the message contains the target keyword (set through the environment variable TARGET_KEYWORD), and filter out relevant messages within the last 24 hours.
4. **Merge messages**: Merge the unread messages of each conversation with the last 20 historical messages, and remove duplicate messages.
5. **Export data**: Export the last 20 messages of each conversation to the telegram_data.json file.
6. **Call the local data processor**: Call the reply_only_llama3.2.py script to process the exported data.

### reply_only_llama3.2.py
This script is mainly responsible for processing the conversation data downloaded from Telegram. The specific functions are as follows:
1. **Initialize the language model**: Use the llama_cpp library to initialize a language model. You need to provide configuration information such as the model path.
2. **Verify and process conversation data**: Verify the format of the conversation data, and preprocess the messages, including cleaning the message content, sorting, etc.
3. **Generate replies**: Build prompts based on the preprocessed messages, call the language model to generate replies, and post - process the replies, including basic cleaning, filtering out invalid content, etc.
4. **Output results**: Print and output the processed results.

## Web Application
The project now includes a web application with a FastAPI backend and a Next.js frontend for easier management of Telegram dialogs.

### Backend
The backend is built with FastAPI and provides endpoints for:
- Telegram authentication via QR code
- Dialog listing and selection
- Message retrieval and processing

### Frontend
The frontend is built with Next.js and provides a user interface for:
- Logging in with Telegram
- Viewing and selecting dialogs for processing
- Managing processing settings

## Development Tools

### Hybrid Testing Environment

To facilitate development without requiring a real Telegram connection, the project includes a hybrid testing environment. This allows you to:

1. Use mock authentication and dialog data
2. Interact with the real database for dialog selection
3. Test database interactions without a Telegram account

#### Setting Up Hybrid Testing

Run the following script to set up the hybrid testing environment:

```bash
cd backend
source ../.venv/bin/activate
./app/dev_utils/start_hybrid_testing.sh
```

This will:
- Start the FastAPI server in development mode
- Inject a mock session into the app
- Generate mock dialog data
- Print example API requests

For more information, see the [Hybrid Testing README](backend/app/dev_utils/README.md).

## Environment Configuration
### Environment Variables
Create a `.env` file in the root directory of the project with the following content:

```
API_ID=your_api_id
API_HASH=your_api_hash
TARGET_KEYWORD=your_target_keyword
DATA_DIR=your_data_directory
PROCESSOR_SCRIPT_NAME=reply_only_llama3.2.py
PYTHON_PATH=python3

```

For the web application, additional environment variables include:

```
FRONTEND_URL=http://localhost:3000
DATABASE_URL=postgresql://username:password@localhost:5432/telegram_dialog_processor
APP_ENV=development  # Set to 'production' in production
```
