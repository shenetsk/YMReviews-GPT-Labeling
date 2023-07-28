# YMReviews-GPT-Labeling
 Streamlit app for labeling Yandex.Market product reviews with GPT using various prompt approaches:
 - Zero-shot
 - Chain of Thoughts
 - Self-Reflection
 Binary label defines whether each review contains information about a considered product property and can be used to make assumptions about the property.  

## Installation
 - Create your OpenAI API key at: https://platform.openai.com/account/api-keys  
 - Place your OpenAI API key in the `~/.openai/key.txt` file or save it to an environment variable named `OPENAI_API_KEY` in a .env file
 - Default GPT model is `gpt-3.5-turbo`. To choose another model assign it to the `MODEL` variable in `labels.py`
 - Create and activate virtual envrironment:  
    ```
    virtualenv venv
    venv\Scripts\activate
    ```
 - Install required libraries: `pip install -r requirements.txt`

## Usage
 Execute `streamlit run ymreviews-gpt-labeling/app.py`