# Watchtower: Your literature chatbot

### Download the Project

Download the project from Github and extract the `watchtower` folder.

```bash
git clone /path/to/app
```


## Software requirements:
1. Grobid: for research paper pdf parsing
2. Qdrant: for vector search
3. sqlite: for storing parsed content and chat history

## Install external services:
1. Install Grobid  
    Following command runs Grobid in a docker container and exposes api on port 8080.  
    ```bash
    sudo docker run -d --rm  --init --ulimit core=0 -p 8080:8070 grobid/grobid:0.8.0 
    ```

2. Install Qdrant  
    Following command runs Qdrant in a docker container and exposes api on port 6333.  
    ```bash
    sudo docker run -d -p 6333:6333 qdrant/qdrant:latest
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
We support several LLM providers. To use one of them, you need to set the `LLM_TYPE` environment variable. For example:

The following sub-sections define the configuration requirements of each supported LLM.
### OpenAI

To use OpenAI LLM, you will need to provide the OpenAI key via `OPENAI_API_KEY` environment variable:

```sh
export LLM_TYPE=openai
export OPENAI_API_KEY=...
```

You can get your OpenAI key from the [OpenAI dashboard](https://platform.openai.com/account/api-keys).

### Azure OpenAI

If you want to use Azure LLM, you will need to set the following environment variables:

```sh
export LLM_TYPE=azure
export OPENAI_VERSION=... # e.g. 2023-05-15
export OPENAI_BASE_URL=...
export OPENAI_API_KEY=...
export OPENAI_ENGINE=... # deployment name in Azure
```

### Bedrock LLM

To use Bedrock LLM you need to set the following environment variables in order to authenticate to AWS.

```sh
export LLM_TYPE=bedrock
export AWS_ACCESS_KEY=...
export AWS_SECRET_KEY=...
export AWS_REGION=... # e.g. us-east-1
export AWS_MODEL_ID=... # Default is anthropic.claude-v2
```

#### AWS Config

Optionally, you can connect to AWS via the config file in `~/.aws/config` described here:
https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials

```
[default]
aws_access_key_id=...
aws_secret_access_key=...
region=...
```

### Vertex AI

To use Vertex AI you need to set the following environment variables. More information [here](https://python.langchain.com/docs/integrations/llms/google_vertex_ai_palm).

```sh
export LLM_TYPE=vertex
export VERTEX_PROJECT_ID=<gcp-project-id>
export VERTEX_REGION=<gcp-region> # Default is us-central1
export GOOGLE_APPLICATION_CREDENTIALS=<path-json-service-account>
```

### Mistral AI

To use Mistral AI you need to set the following environment variables. The app has been tested with Mistral Large Model deployed through Microsoft Azure. More information [here](https://learn.microsoft.com/en-us/azure/ai-studio/how-to/deploy-models-mistral).

```
export LLM_TYPE=mistral
export MISTRAL_API_KEY=...
export MISTRAL_API_ENDPOINT=...  # should be of the form https://<endpoint>.<region>.inference.ai.azure.com
export MISTRAL_MODEL=...  # optional
```

### Cohere

To use Cohere you need to set the following environment variables:

```
export LLM_TYPE=cohere
export COHERE_API_KEY=...
export COHERE_MODEL=...  # optional
```


### Locally (for development)

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
pip install -r api/requirements.txt

# Install Node dependencies
cd frontend && yarn && cd ..
```

#### Ingest data

##### Indexing your own data
```sh
cd api
python3 -u manage.py index-data-from-directory /path/to/pdf/files
```
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