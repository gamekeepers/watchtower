# Watchtower: Your literature chatbot

### Download the Project

Download the project from Github and extract the `watchtower` folder.

```bash
git clone git@github.com:gamekeepers/watchtower.git
```


## Software requirements:
1. Grobid: for research paper pdf parsing
2. Qdrant: for vector search
3. sqlite: for storing pdf parsed content and chat history

## Install external services:
1. Install Grobid  
    Following command runs Grobid in a docker container and exposes api on port 8080.  
    ```bash
    sudo docker run -d --rm  --init --ulimit core=0 -p 8080:8070 grobid/grobid:0.8.0 
    ```
2. Install Qdrant  
    Following command runs Qdrant in a docker container and exposes api on port 6333.  
    ```bash
   # create persistent qdrant storage directory
   mkdir -p ~/.watchtower/qdrant_storage
    sudo docker run -d -p 6333:6333 qdrant/qdrant:latest
   sudo docker run -d -p 6333:6333 \
    -v ~/.watchtower/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
    ```
    Qdrant dashboard can be accessed at http://localhost:6333/dashboard

3. Install sqlite
    ```bash
    sudo apt-get install sqlite3
    ```
4. Install python dependencies
    ```bash
    pip install -r requirements.txt
    ```




## Connecting to LLM
We support several LLM providers.  
OpenAI, Azure OpenAI, Bedrock LLM, AWS Config, Vertex AI, Mistral AI, Cohere
To use one of them, you need to set the `LLM_TYPE` environment variable. For example:

The following sub-sections define the configuration requirements of OpenAI.
### OpenAI

To use OpenAI LLM, you will need to provide the OpenAI key via `OPENAI_API_KEY` environment variable:

```sh
export LLM_TYPE=openai
export OPENAI_API_KEY=...
```

You can get your OpenAI key from the [OpenAI dashboard](https://platform.openai.com/account/api-keys).


### Run Locally (for development)

With the environment variables set, you can run the following commands to start the server and frontend.

#### Pre-requisites

- Python 3.8+
- Node 14+

#### Install the dependencies

For Python we recommend using a virtual environment.

_ℹ️ Here's a good [primer](https://realpython.com/python-virtual-environments-a-primer) on virtual environments from Real Python._

```sh
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
cd frontend && yarn && cd ..
```
#### Setup environment variables
Copy env.sample  .env file  
```sh
cp env.sample .env
```
Populate `.env` file   

#### Ingest data
##### Set up data stores
```sh
cd api && python3 -u manage.py set-data-stores && cd ..
```
This will create a sqlite database and a qdrant collection for use by app
##### Indexing your own data
```sh
cd api && python3 -u manage.py index-data-from-directory /path/to/pdf/files && cd ..
```
Ensure both Grobid and Qdrant services are up.
This will store parsed content in sqlite database and index the vectors in Qdrant.
By default, this will index the data into the `literature-docs` index. You can change this by setting the `QDRANT_COLLECTION` environment variable.



#### Run API and frontend

```sh
# Launch API app
flask run

# In a separate terminal launch frontend app
cd frontend && yarn start
```

You can now access the frontend at http://localhost:3000. Changes are automatically reloaded.


# References:
1. [Elasticsearch chatbot example app.](https://github.com/elastic/elasticsearch-labs/tree/main/example-apps/chatbot-rag-app)
