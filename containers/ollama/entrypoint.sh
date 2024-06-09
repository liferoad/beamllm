#!/bin/bash

# Start the ollama process
nohup ollama serve &
sleep 10

# Start the Beam process
/opt/apache/beam/boot "$@"