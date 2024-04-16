# app/Dockerfile

FROM python:3.10-slim

WORKDIR /deploy

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list &&\
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17

# Always clone
ADD "https://www.random.org/cgi-bin/randbyte?nbytes=10&format=h" random
RUN rm -rf random
# Do not use a credential manager. Force ai_web user.
RUN git -c credential.helper="" clone -b "feature/newsletter" https://ai_web:xu3wm_hf-5pMMfzXtWaG@gitlab.rc.uab.edu/anes_ai/llm_apps/scopingreview.git .
RUN git config --local credential.helper ""

RUN pip3 install -r requirements.txt
RUN pip3 install --user pip setuptools wheel
RUN pip3 install --user -e .

CMD ["python", "./ScopingReview/main.py", "--output", "/data/results"]


