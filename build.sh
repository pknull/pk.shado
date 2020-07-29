set -ex

# SET THE FOLLOWING VARIABLES
# docker hub username
USERNAME=pknull
# image name
IMAGE=rpgbot

docker build -t $USERNAME/$IMAGE:latest .
