#!/bin/bash

# SET THE FOLLOWING VARIABLES
TOKEN="Token"

sudo docker build . -t dice --build-arg TOKEN=$TOKEN
