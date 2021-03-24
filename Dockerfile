FROM python:3.9-buster

# Set the working directory to the project directory
WORKDIR /var/spautomod

# Clear apt's cache
RUN  apt-get clean
RUN  rm -rf /var/lib/apt/lists/*

# Setup a user for the app
RUN groupadd -g 1000 spautomod
RUN useradd -u 1000 -ms /bin/bash -g spautomod spuser

# Copy code from the project directory and set www as the owner
COPY --chown=spuser:spautomod . /var/spautomod

# Set spuser as the current user
USER spuser

# Install project dependencies
RUN ./setup.sh
