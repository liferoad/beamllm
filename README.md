# Beam LLM

Bring your LLM models to production with `beamllm`.

Note This project uses the [Dataflow ML Starter project](https://github.com/google/dataflow-ml-starter) as the template.

The Beam pipeline to deploy a LLM model using Dataflow is:

```bash
Read messages from Pub/Sub ----> Pre-process messages ----> RunInference with LLMs
----> Post-process messages ----> Write messages to Pub/Sub
```

Each message is associated with a chat session id, which guarantees the receiver only gets the messages for the corresponding session.

## How to run

### Prerequisites

* Tools: conda, git, make, docker, gcloud, python3-venv
* Access to a GCP project

### Modify `.env`

Only `FLAN-T5-small` and `gemma_instruct_2b_en` models are supported.
`INPUT_TOPIC` and `OUTPUT_TOPIC` define two Pub/Sub topics for message ins and outs.

### Steps to run this demo

``` bash
# create venv for this demo
make init
# build customer container
make docker
# deploy a LLM model using Dataflow
make run-cpu
# chat with the model
make run-chat
```

[pipeline.py](https://github.com/liferoad/beamllm/blob/main/beamllm/pipeline.py) defines the Beam pipeline.
[config.py](https://github.com/liferoad/beamllm/blob/main/beamllm/config.py) configures the model information.

[chat.py](https://github.com/liferoad/beamllm/blob/main/beamllm/chat.py) provides a simple chat interface. It basically publishes the user's message to the input Pub/Sub topic by adding one unique session id and keeps listening the response from the output topic. One example output is,

```bash
Listening for messages on projects/apache-beam-testing/subscriptions/llm_output-32555ae3-e8b1-4977-a7db-015f22ee2c51..

Enter message to chat (Ctrl-Break to exit): translate English to Spanish: We are in New York City.
Bot 32555ae3-e8b1-4977-a7db-015f22ee2c51: Estamos en Nueva York City.

Enter message to chat (Ctrl-Break to exit): what is the sky color
Bot 32555ae3-e8b1-4977-a7db-015f22ee2c51: a blue sky

Enter message to chat (Ctrl-Break to exit): ^CExiting...
Subscription deleted: projects/apache-beam-testing/subscriptions/llm_output-32555ae3-e8b1-4977-a7db-015f22ee2c51.
Chat finished.
```

## Known Issues

`FLAN-T5-small` needs `pytorch` while `gemma_instruct_2b_en` requires `Keras 3.0` and `Tensorflow 3.15`.
Make all of these packages coexisting with a GPU container image is challenging.
Right now, running on GPUs using Dataflow is broken. Running `gemma_instruct_2b_en` on CPUs is very slow.

## To Do

* Make GPUs working
* Polish the interface to package everything with a CLI package
* Support more built-in models
* Support custom models
* Polish the chat client

## Links

* <https://cloud.google.com/dataflow/docs/notebooks/run_inference_pytorch>
* <https://github.com/GoogleCloudPlatform/dataflow-cookbook/tree/main/Python/pubsub>
* <https://cloud.google.com/dataflow/docs/notebooks/run_inference_generative_ai>
* <https://cloud.google.com/dataflow/docs/machine-learning/gemma-run-inference>
* <https://www.kaggle.com/models/google/gemma>
* <https://www.tensorflow.org/install/source#gpu>