# Copyright 2020-2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#    http://aws.amazon.com/asl/
#
# or in the "license" file accompanying this file.
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied.
# See the License for the specific language governing permissions and limitations under the License.
FROM public.ecr.aws/ubuntu/ubuntu:22.04 AS core

ARG DEBIAN_FRONTEND="noninteractive"

# Install git, SSH, and other utilities
RUN set -ex \
    && echo 'Acquire::CompressionTypes::Order:: "gz";' > /etc/apt/apt.conf.d/99use-gzip-compression \
    && apt-get update \
    && apt install -y -qq apt-transport-https gnupg ca-certificates \
    && apt-get install software-properties-common -y -qq --no-install-recommends \
    && apt-get install -y -qq --no-install-recommends openssh-client \
    && mkdir ~/.ssh \
    && mkdir -p /codebuild/image/config \
    && touch ~/.ssh/known_hosts \
    && ssh-keyscan -t rsa,dsa,ed25519,ecdsa -H github.com >> ~/.ssh/known_hosts \
    && ssh-keyscan -t rsa,dsa,ed25519,ecdsa -H bitbucket.org >> ~/.ssh/known_hosts \
    && chmod 600 ~/.ssh/known_hosts \
    && apt-get install -y -qq --no-install-recommends \
          apt-utils asciidoc autoconf automake build-essential bzip2 \
          bzr curl dirmngr docbook-xml docbook-xsl dpkg-dev \
          e2fsprogs expect fakeroot file g++ gcc gettext gettext-base \
          groff gzip iptables jq less libapr1 libaprutil1 \
          libargon2-0-dev libbz2-dev libc6-dev libcurl4-openssl-dev \
          libdb-dev libdbd-sqlite3-perl libdbi-perl libdpkg-perl \
          libedit-dev liberror-perl libevent-dev libffi-dev libgeoip-dev \
          libglib2.0-dev libhttp-date-perl libio-pty-perl libjpeg-dev \
          libkrb5-dev liblzma-dev libmagickcore-dev libmagickwand-dev \
          libmysqlclient-dev libncurses5-dev libncursesw5-dev libonig-dev \
          libpq-dev libreadline-dev libserf-1-1 libsodium-dev libsqlite3-dev libssl-dev \
          libsvn1 libsvn-perl libtcl8.6 libtidy-dev libtimedate-perl \
          libtool libwebp-dev libxml2-dev libxml2-utils libxslt1-dev \
          libyaml-dev libyaml-perl llvm locales make mlocate \
          netbase openssl patch pkg-config procps python3-configobj \
          python3-openssl rsync sgml-base sgml-data \
          tar tcl tcl8.6 tk tk-dev unzip wget xfsprogs xml-core xmlto xsltproc \
          libzip-dev vim xvfb xz-utils zip zlib1g-dev git-lfs \
    && rm -rf /var/lib/apt/lists/*

ENV LC_CTYPE="C.UTF-8"

RUN useradd codebuild-user

#=======================End of layer: core  =================


FROM core AS tools

# Install Git
RUN set -ex \
   && GIT_VERSION=2.42.1 \
   && GIT_TAR_FILE=git-$GIT_VERSION.tar.gz \
   && GIT_SRC=https://github.com/git/git/archive/v${GIT_VERSION}.tar.gz  \
   && curl -L -o $GIT_TAR_FILE $GIT_SRC \
   && tar zxf $GIT_TAR_FILE \
   && cd git-$GIT_VERSION \
   && make -j4 \
   && make install prefix=/usr \
   && cd .. && rm -rf git-$GIT_VERSION \
   && rm -rf $GIT_TAR_FILE /tmp/*

# Install AWS SAM CLI
RUN wget -nv https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip -O /tmp/samcli.zip \
    && unzip -q /tmp/samcli.zip -d /opt \
    && /opt/install --update -i /usr/local/sam-cli -b /usr/local/bin \
    && rm /tmp/samcli.zip /opt/install \
    && rm -rf /opt/aws-sam-cli-src \
    && sam --version

# Install stunnel
RUN set -ex \
   && STUNNEL_VERSION=5.71 \
   && STUNNEL_TAR=stunnel-$STUNNEL_VERSION.tar.gz \
   && STUNNEL_SHA256="f023aae837c2d32deb920831a5ee1081e11c78a5d57340f8e6f0829f031017f5" \
   && curl -o $STUNNEL_TAR https://www.stunnel.org/archive/5.x/$STUNNEL_TAR && echo "$STUNNEL_SHA256 $STUNNEL_TAR" | sha256sum --check && tar xfz $STUNNEL_TAR \
   && cd stunnel-$STUNNEL_VERSION \
   && ./configure \
   && make -j4 \
   && make install \
   && openssl genrsa -out key.pem 2048 \
   && openssl req -new -x509 -key key.pem -out cert.pem -days 1095 -subj "/C=US/ST=Washington/L=Seattle/O=Amazon/OU=Codebuild/CN=codebuild.amazon.com" \
   && cat key.pem cert.pem >> /usr/local/etc/stunnel/stunnel.pem \
   && cd .. && rm -rf stunnel-${STUNNEL_VERSION}*

# AWS Tools
# https://docs.aws.amazon.com/eks/latest/userguide/install-aws-iam-authenticator.html https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_CLI_installation.html
RUN curl -sS -o /usr/local/bin/aws-iam-authenticator https://s3.us-west-2.amazonaws.com/amazon-eks/1.25.6/2023-01-30/bin/linux/amd64/aws-iam-authenticator \
    && curl -sS -o /usr/local/bin/kubectl https://s3.us-west-2.amazonaws.com/amazon-eks/1.25.6/2023-01-30/bin/linux/amd64/kubectl \
    && curl -sS -o /usr/local/bin/ecs-cli https://s3.amazonaws.com/amazon-ecs-cli/ecs-cli-linux-amd64-latest \
    && curl -sS -L https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_Linux_amd64.tar.gz | tar xz -C /usr/local/bin \
    && chmod +x /usr/local/bin/kubectl /usr/local/bin/aws-iam-authenticator /usr/local/bin/ecs-cli /usr/local/bin/eksctl

# Configure SSM
RUN set -ex \
    && mkdir /tmp/ssm \
    && cd /tmp/ssm \
    && wget -q https://s3.amazonaws.com/amazon-ssm-us-east-1/latest/debian_amd64/amazon-ssm-agent.deb \
    && dpkg -i amazon-ssm-agent.deb

# Install AWS CLI v2
# https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-linux.html
RUN curl https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /opt \
    && /opt/aws/install --update -i /usr/local/aws-cli -b /usr/local/bin \
    && rm /tmp/awscliv2.zip \
    && rm -rf /opt/aws \
    && aws --version

# Install env tools for runtimes
#nodejs
ARG SRC_DIR="/usr/src"
ARG N_SRC_DIR="$SRC_DIR/n"
RUN git clone https://github.com/tj/n $N_SRC_DIR \
     && cd $N_SRC_DIR && make install

#python
RUN curl -s -S -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | bash
ENV PATH="/root/.pyenv/shims:/root/.pyenv/bin:$PATH"

#go
RUN git clone https://github.com/syndbg/goenv.git $HOME/.goenv
ENV PATH="/root/.goenv/shims:/root/.goenv/bin:/go/bin:$PATH"
ENV GOENV_DISABLE_GOPATH=1
ENV GOPATH="/go"

#=======================End of layer: tools  =================
FROM tools AS runtimes

#****************      NODEJS     ****************************************************

ENV NODE_18_VERSION="18.18.2"
ENV NODE_20_VERSION="20.9.0"

RUN  n $NODE_18_VERSION && npm install --save-dev -g -f grunt \
     && npm install --save-dev -g -f grunt-cli \
     && npm install --save-dev -g -f webpack \
     && npm install --save-dev -g -f yarn \
     && n $NODE_20_VERSION && npm install --save-dev -g -f grunt \
     && npm install --save-dev -g -f grunt-cli \
     && npm install --save-dev -g -f webpack \
     && npm install --save-dev -g -f yarn \
     && cd / && rm -rf $N_SRC_DIR && rm -rf /tmp/*

#****************      END NODEJS     ****************************************************

#**************** PYTHON *****************************************************
ENV PYTHON_311_VERSION="3.11.6"
ENV PYTHON_312_VERSION="3.12.0"

ARG PYTHON_PIP_VERSION=23.3.1
ENV PYYAML_VERSION=5.4.1

COPY tools/runtime_configs/python/$PYTHON_312_VERSION /root/.pyenv/plugins/python-build/share/python-build/$PYTHON_312_VERSION
RUN env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install $PYTHON_312_VERSION && rm -rf /tmp/*
RUN set -ex \
    && pyenv global  $PYTHON_312_VERSION \
    && pip3 install --no-cache-dir --upgrade --force-reinstall "pip==$PYTHON_PIP_VERSION" \
    && pip3 install wheel \
    && pip3 install --no-cache-dir --upgrade 'setuptools==67.7.2' boto3 pipenv virtualenv \
    && pip3 install --no-build-isolation "Cython<3" "PyYAML==$PYYAML_VERSION" \
    && pip3 uninstall cython --yes

COPY tools/runtime_configs/python/$PYTHON_311_VERSION /root/.pyenv/plugins/python-build/share/python-build/$PYTHON_311_VERSION
RUN env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install $PYTHON_311_VERSION && rm -rf /tmp/*
RUN set -ex \
    && pyenv global  $PYTHON_311_VERSION \
    && pip3 install --no-cache-dir --upgrade --force-reinstall "pip==$PYTHON_PIP_VERSION" \
    && pip3 install wheel \
    && pip3 install --no-build-isolation "Cython<3" "PyYAML==$PYYAML_VERSION" \
    && pip3 install --no-cache-dir --upgrade 'setuptools==67.7.2' boto3 pipenv virtualenv \
    && pip3 uninstall cython --yes

#**************** END PYTHON *****************************************************

#****************     GOLANG     ****************************************************
ENV GOLANG_20_VERSION="1.20.11"
ENV GOLANG_21_VERSION="1.21.4"

RUN goenv install $GOLANG_20_VERSION && rm -rf /tmp/* && \
    goenv install $GOLANG_21_VERSION && rm -rf /tmp/* && \
    goenv global  $GOLANG_20_VERSION && \
    go env -w GO111MODULE=auto

#****************      END GOLANG     *******************************

#=======================End of layer: runtimes  =================


#****************        DOCKER    *********************************************
ARG DOCKER_BUCKET="download.docker.com"
ARG DOCKER_CHANNEL="stable"
ARG DIND_COMMIT="3b5fac462d21ca164b3778647420016315289034"
ARG DOCKER_COMPOSE_VERSION="2.23.1"
ARG DOCKER_BUILDX_VERSION="0.11.0"
ARG SRC_DIR="/usr/src"

ARG DOCKER_SHA256="544262F4A3621222AFB79960BFAD4D486935DAB80893478B5CC9CF8EBAF409AE"
ARG DOCKER_VERSION="23.0.6"

# Install Docker
RUN set -ex \
    && curl -fSL "https://${DOCKER_BUCKET}/linux/static/${DOCKER_CHANNEL}/x86_64/docker-${DOCKER_VERSION}.tgz" -o docker.tgz \
    && echo "${DOCKER_SHA256} *docker.tgz" | sha256sum -c - \
    && tar --extract --file docker.tgz --strip-components 1  --directory /usr/local/bin/ \
    && rm docker.tgz \
    && docker -v \
    # replace runc package to resolve CVE-2024-21626
    && apt-get update && apt-get -y install runc \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && rm -f /usr/local/bin/runc \
    && ln -s /usr/sbin/runc /usr/local/bin/runc \
    && runc -v \
    # set up subuid/subgid so that "--userns-remap=default" works out-of-the-box
    && addgroup dockremap \
    && useradd -g dockremap dockremap \
    && echo 'dockremap:165536:65536' >> /etc/subuid \
    && echo 'dockremap:165536:65536' >> /etc/subgid \
    && wget -q "https://raw.githubusercontent.com/docker/docker/${DIND_COMMIT}/hack/dind" -O /usr/local/bin/dind \
    # Install docker compose as docker plugin and maintain docker-compose usage
    && mkdir -p /usr/local/lib/docker/cli-plugins \
    && curl -L https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-Linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose \
    && chmod +x /usr/local/bin/dind /usr/local/lib/docker/cli-plugins/docker-compose \
    && ln -s /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose \
    # Ensure docker-compose and docker compose work
    && docker-compose version \
    && docker compose version \
    # Add docker buildx tool
    && curl -L https://github.com/docker/buildx/releases/download/v${DOCKER_BUILDX_VERSION}/buildx-v${DOCKER_BUILDX_VERSION}.linux-amd64 -o /usr/local/lib/docker/cli-plugins/docker-buildx \
    && chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx \
    && ln -s /usr/local/lib/docker/cli-plugins/docker-buildx /usr/local/bin/docker-buildx \
    # Ensure docker-buildx works
    && docker-buildx version

VOLUME /var/lib/docker
#*********************** END  DOCKER  ****************************

# Activate runtime versions specific to image version.
RUN n $NODE_18_VERSION
RUN pyenv global $PYTHON_311_VERSION
RUN goenv global $GOLANG_20_VERSION
#********************** install SO packages ******************
ENV DEBIAN_FRONTEND=noninteractive
RUN set -ex \
    && apt-get update \
    && apt-get install figlet jq tree xvfb libfontconfig wkhtmltopdf graphviz gawk golint -y -qq \
    &&  rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*
#********************** Python libraries *********************
ARG PYTHON_PYMSTEAMS_VERSION=0.2.2
ARG PYTHON_PDFKIT_VERSION=1.0.0
ARG PYTHON_JSON2HTML_VERSION=1.3.0
ARG PYTHON_ZIPP_VERSION=3.8.0
ARG PYTHON_TERRAFORM_COMPLIANCE_VERSION=1.3.47
ARG PYTHON_XMLTODICT_VERSION=0.13.0
ARG PYTHON_JUNIT2HTML_VERSION=30.1.3
ARG PYTHON_SIMPLEJSON_VERSION=3.18.1
ARG PYTHON_ARGCOMPLETE_VERSION=2.0.0
ARG GIT_REMOTE_VERSION=1.17
ARG PRE_COMMIT_VERSION=3.6.0

RUN set -ex \
    && pip3 install --no-cache-dir --upgrade "pymsteams==$PYTHON_PYMSTEAMS_VERSION" \
    && pip3 install --no-cache-dir --upgrade "pdfkit==$PYTHON_PDFKIT_VERSION" \
    && pip3 install --no-cache-dir --upgrade "json2html==$PYTHON_JSON2HTML_VERSION" \
    && pip3 install --no-cache-dir --upgrade "zipp==$PYTHON_ZIPP_VERSION" \
    && pip3 install --no-cache-dir --upgrade "terraform-compliance==$PYTHON_TERRAFORM_COMPLIANCE_VERSION" \
    && pip3 install --no-cache-dir --upgrade "xmltodict==$PYTHON_XMLTODICT_VERSION" \
    && pip3 install --no-cache-dir --upgrade "junit2html==$PYTHON_JUNIT2HTML_VERSION" \
    && pip3 install --no-cache-dir --upgrade "simplejson==$PYTHON_SIMPLEJSON_VERSION" \
    && pip3 install --no-cache-dir --upgrade "argcomplete==$PYTHON_ARGCOMPLETE_VERSION" \
    && pip3 install --no-cache-dir --upgrade "git-remote-codecommit==$GIT_REMOTE_VERSION" \
    && pip3 install --no-cache-dir --upgrade "pre-commit==$PRE_COMMIT_VERSION" \
    && pip3 install --no-cache-dir --upgrade pyfiglet \
    && pip3 install --no-cache-dir --upgrade checkov \
    && pip3 install --no-cache-dir --upgrade azure-devops

#************************** Terraform *************************************
ARG TERRAFORM_VERSION=1.7.5
RUN set -ex \
    && curl -O https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    && unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip  -d /usr/local/bin/ \
    && mkdir -p "$HOME"/.terraform.d/plugin-cache && echo 'plugin_cache_dir   = "$HOME/.terraform.d/plugin-cache"' > ~/.terraformrc

#************************* Terragrunt *************************************
ARG TERRAGRUNT_VERSION=0.55.16
RUN set -ex \
     && wget https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_amd64 -q \
     && mv terragrunt_linux_amd64 /usr/local/bin/terragrunt \
     && chmod +x /usr/local/bin/terragrunt

#*********************** Terramate ****************************************
ARG TERRAMATE_VERSION=0.5.3
RUN set -ex \
     && wget https://github.com/mineiros-io/terramate/releases/download/v${TERRAMATE_VERSION}/terramate_${TERRAMATE_VERSION}_linux_x86_64.tar.gz \
      && tar -xzf terramate_${TERRAMATE_VERSION}_linux_x86_64.tar.gz \
      && mv terramate /usr/local/bin/terramate \
      && chmod +x /usr/local/bin/terramate

#*********************** tfsec ********************************************
ARG TFSEC_VERSION=1.28.5
RUN set -ex \
      && wget https://github.com/aquasecurity/tfsec/releases/download/v${TFSEC_VERSION}/tfsec-linux-amd64 \
      && mv tfsec-linux-amd64 /usr/local/bin/tfsec \
      && chmod +x /usr/local/bin/tfsec \
      && terragrunt --version
#************************************TFswitch******************************************
RUN set -ex \
    && curl -L https://raw.githubusercontent.com/warrensbox/terraform-switcher/release/install.sh | bash \
    && tfswitch --version

#**********************Terraform docs ************************************
ARG TERRRAFORM_DOCS_VERSION=0.16.0
RUN set -ex \
    && curl -sSLo ./terraform-docs.tar.gz https://terraform-docs.io/dl/v${TERRRAFORM_DOCS_VERSION}/terraform-docs-v${TERRRAFORM_DOCS_VERSION}-$(uname)-amd64.tar.gz \
    && tar -xzf terraform-docs.tar.gz \
    && chmod +x terraform-docs \
    && mv terraform-docs /usr/local/bin/terraform-docs

#********************* ShellCheck *****************************************
ARG SHELLCHECK_VERSION="stable"
RUN set -ex \
      && wget -qO- "https://github.com/koalaman/shellcheck/releases/download/${SHELLCHECK_VERSION?}/shellcheck-${SHELLCHECK_VERSION?}.linux.x86_64.tar.xz"  | tar -xJv \
      && cp "shellcheck-${SHELLCHECK_VERSION}/shellcheck" /usr/bin/ \
      && shellcheck --version


# Configure SSH
COPY ssh_config /root/.ssh/config
COPY runtimes.yml /codebuild/image/config/runtimes.yml
COPY dockerd-entrypoint.sh /usr/local/bin/dockerd-entrypoint.sh
COPY legal/bill_of_material.txt /usr/share/doc/bill_of_material.txt
COPY amazon-ssm-agent.json /etc/amazon/ssm/amazon-ssm-agent.json



ENTRYPOINT ["/usr/local/bin/dockerd-entrypoint.sh"]

#=======================END of STD:7.0  =================
