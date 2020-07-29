#!/bin/bash

# SET THE FOLLOWING VARIABLES
TOKEN="NzM3ODkyNjk5OTc3NDE2ODQ1.XyD-IQ.tTK5PFCRhPtiOqAYLjZKcTkjql8"

sudo docker build . -t dice --build-arg TOKEN=$TOKEN
